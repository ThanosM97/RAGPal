"""This module implements a Flask API for the RAGPal application.

Endpoints:
'/' : Endpoint for home/index page (methods: GET)
'/upload' : Endpoint for uploading text files or text input to the knowledge
            base of the RAG model. (methods: GET, POST)
'/view' : Endpoint for viewing the contents of the knowledge base, with an
          option to delete entries. (methods: GET, POST)

WebSockets:
'/send_message' : WebSocket for sending a request to the LLM to obtain a
                  response based on user's prompt. Sends the streamed
                  response through the websocket.

Functions:
'generation' : Makes the request to AzureOpenAI API given an input string
               `prompt` and a list of `relevant_documents`. The response is
               a stream, so the function is asynchronous, sending the chunks
               of the response through the `websocket` as they come.
'retrieval' : Retrieves and returns relevant documents to the input string
              argument `prompt`.
"""
import os
import time
import uuid
from typing import List

import uvicorn
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from openai import AzureOpenAI
from qdrant_client import QdrantClient, models

# Initialize FASTAPI app
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load variables from .env file
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")

# Load config variables from config.yaml
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize AzureOpenAI client
azure_client = AzureOpenAI(
    api_key=OPENAI_API_KEY,
    azure_endpoint=OPENAI_API_BASE,
    api_version=config['azure-openai']['client']['api_version'])

# Initialize qdrant client and collection
qdrant = QdrantClient(location=":memory:")

qdrant.recreate_collection(
    collection_name=config['qdrant']['collection_name'],
    vectors_config=models.VectorParams(
        size=config['azure-openai']['embedding']['vector_size'],
        distance=models.Distance.COSINE,
    ),
)

# Global variables
messages = []


def retrieval(prompt: str) -> List[str]:
    """Returns relevant documents to `prompt`.

    This function first makes a request to AzureOpenAI embeddings endpoints to
    generate query embeddings for the input `prompt`. Then, the cosine
    similarity between the query embeddings and the embeddings of each document
    in the `knowledge_base` are computed, keeping only the documents with a
    value greater than 0.8.

    Args:
    - prompt (str): User input/prompt.

    Returns:
        A list of relevant documents.
    """
    # Generate query embeddings
    query_embedding = list(azure_client.embeddings.create(
        input=prompt,
        model=config['azure-openai']['embedding']['model']
    ).data[0].embedding)

    hits = qdrant.search(
        collection_name=config['qdrant']['collection_name'],
        query_vector=query_embedding,
        limit=config['qdrant']['top_k']
    )

    relevant_documents = [hit.payload["content"] for hit in hits]
    return relevant_documents


async def generation(
    websocket: WebSocket,
    prompt: str,
    relevant_documents: List[str] | None = None
) -> None:
    """Sends chunks of AzureOpenAI API's streamed response via a `websocket`.

    This asynchronous function takes as input a user `prompt` and the retrieved
    `relevant_documents`. It makes a request to AzureOpenAI's chat completion
    API using formatting and RAG-specific instructions for the generation
    process, the relevant docuements, and the user prompt. It sends the chunks
    of the API's response to the `websocket` as they come.

    If the `relevant_documents` argument is None, the user has disabled the
    RAG functionality, so a generic request will be made to AzureOpenAI's
    chat completion API using only the `input_prompt` and the formatting
    isntruction.

    Args:
    - websocket (WebSocket): Established WebSocket for messages.
    - prompt (str): User input/prompt.
    - relevant_documents (List | None): A list of relevant documents to
                                        the input prompt, or None.
    """
    # Formatting instruction
    instruction = ("You are a multilingual virtual assistant. " +
                   "Respond using Markdown if formatting is needed. ")

    if relevant_documents is None:  # RAG functionality disabled
        message_text = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": prompt}]
    else:  # with RAG
        rag_instructions = (
            "Do not justify your answers. " +
            "Forget the information you have outside of context." +
            "If the answer to the question is not provided in the context, " +
            "say I don't know the answer to this question in the appropriate" +
            "language. Do not mention that context is provided to the user. " +
            "Based on these instructions, and the relevant context, " +
            "Answer the following question:")

        documents = "[NEW DOCUMENT]: ".join(relevant_documents)
        message_text = [
            {"role": "system", "content": instruction},
            {
                "role": "system",
                "content": f"Relevant context: {documents}"
            },
            {"role": "user", "content": rag_instructions + prompt}]

    chat_completion = azure_client.chat.completions.create(
        messages=message_text,
        model=config['azure-openai']['chat-completion']['model'],
        stream=True,
        temperature=0.7  # Makes the model more focused and deterministic
    )

    await websocket.send_text("[MESSAGE STARTS HERE]")

    response = []
    for chunk in chat_completion:
        if len(chunk.choices) > 0:
            msg = chunk.choices[0].delta.content
            msg = "" if msg is None else msg
            response.append(msg)

            await websocket.send_text(msg)

    response = "".join(response)
    messages.append(('bot', response))

    await websocket.send_text("[MESSAGE ENDS HERE]")

    await websocket.close(reason="End of Message")


@app.get('/', response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html",
                                      context={"request": request})


@app.websocket("/send_message")
async def send_message(websocket: WebSocket) -> None:
    await websocket.accept()

    args = await websocket.receive_json()

    user_input = args['prompt']
    rag_enabled = args['ragEnabled']

    messages.append(('user', user_input))

    try:
        relevant_documents = retrieval(
            user_input) if rag_enabled else None

        await generation(websocket, user_input, relevant_documents)

    except Exception:
        await websocket.close(code=1011)


@app.get("/upload", response_class=HTMLResponse)
def upload_get(request: Request):

    return templates.TemplateResponse(
        "upload.html",  context={
            "request": request, "alert_type": None, "alert": None})


@app.post("/upload", response_class=HTMLResponse)
async def upload_post(request: Request):
    alert = None
    alert_type = None
    document = None

    form_data = await request.form()

    try:
        if 'text' in form_data:  # Text field was used
            document = form_data.get('text')
            alert_type = "success"
            alert = "Text sucessfully uploaded."
        elif 'file' in form_data:  # File was selected
            document = await form_data.get('file').read()
            document = document.decode('utf-8')
            alert_type = "success"
            alert = "Files sucessfully uploaded."
    except Exception as e:
        alert_type = "danger"
        alert = "No files were uploaded. " + str(e)

    if document is not None:  # Text or file was uploaded
        short_desc = " ".join(document.split(" ")[:15]) + "..."

        try:
            # Generate document embeddings
            embd = list(azure_client.embeddings.create(
                input=document,
                model=config['azure-openai']['embedding']['model']
            ).data[0].embedding)
        except Exception:
            return Response(status=500)

        # # Add document to knowledge base
        doc = {
            "content": document,
            "short_desc": short_desc,
            "uploaded": time.time()
        }

        qdrant.upload_points(
            collection_name="Knowledge_Base",
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embd, payload=doc
                )
            ]
        )

    return templates.TemplateResponse(
        "upload.html",  context={
            "request": request, "alert_type": alert_type, "alert": alert})


@app.get("/view", response_class=HTMLResponse)
def view_get(request: Request, limit: int = 10):

    scroll_results = qdrant.scroll(
        collection_name="Knowledge_Base",
        with_vectors=False,
        with_payload=True,
        order_by="uploaded",
        limit=limit
    )[0]

    documents = [(record.id, record.payload["short_desc"])
                 for record in scroll_results]

    return templates.TemplateResponse(
        "view.html",  context={
            "request": request, "documents": documents})


@app.delete("/view")
async def view_delete(request: Request) -> Response:
    form_data = await request.form()

    try:
        qdrant.delete(
            collection_name=config['qdrant']['collection_name'],
            points_selector=[form_data.get('id')]
        )
        return Response("Succesfully deleted.", status_code=200)
    except Exception:
        return Response("Document not found.", status_code=404)


if __name__ == "__main__":
    uvicorn.run('app:app', port=5000, reload=True, host='0.0.0.0')
