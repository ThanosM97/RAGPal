"""This module implements a Flask API for the RAGPal application.

Endpoints:
'/' : Endpoint for home/index page (methods: GET)
'/send_message' : Endpoint for sending a request to the LLM to obtain a
                  response based on user's prompt. Returns the streamed
                  response. (methods: POST, request args: `user-input`)
'/upload' : Endpoint for uploading text files or text input to the knowledge
            base of the RAG model. (methods: GET, POST)
'/view' : Endpoint for viewing the contents of the knowledge base, with an
          option to delete entries. (methods: GET, POST)

Functions:
'generation' : Makes the request to AzureOpenAI API given an input string
               `prompt` and a list of `relevant_documents`. The response is
               a stream, so the function is a Generator that yields chunks
               of the response as they come.
'retrieval' : Retrieves and returns relevant documents to the input string
              argument `prompt`.
"""
import os
import urllib.parse
from typing import Generator, List, Optional

import uvicorn
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
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


def generation(
    prompt: str,
    relevant_documents: Optional[List[str]] = None
) -> Generator[bytes, None, str]:
    """Yields chunks of AzureOpenAI API's streamed response.

    This generator function takes as input a user `prompt` and the retrieved
    `relevant_documents`. It makes a request to AzureOpenAI's chat completion
    API using formatting and RAG-specific instructions for the generation
    process, the relevant docuements, and the user prompt. It yields the chunks
    of the API's response as they come.

    If the `relevant_documents` argument is None, the user has disabled the
    RAG functionality, so a generic request will be made to AzureOpenAI's
    chat completion API using only the `input_prompt` and the formatting
    isntruction.

    Args:
    - prompt (str): User input/prompt.
    - relevant_documents (List | None): A list of relevant documents to
                                        the input prompt, or None.

    Yields:
        Chunks of the response in bytes (utf-8 encoded).

    Returns:
        The generated response as a string.
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

    response = []
    for chunk in chat_completion:
        if len(chunk.choices) > 0:
            msg = chunk.choices[0].delta.content
            msg = "" if msg is None else msg
            response.append(msg)
            yield msg.encode('utf-8')

    response = "".join(response)
    messages.append(('bot', response))

    return response


@app.get('/', response_class=HTMLResponse)
def home(request: Request) -> str:
    return templates.TemplateResponse("index.html",
                                      context={"request": request})


@app.post("/send_message")
async def send_message(request: Request):
    form_data = await request.form()

    user_input = urllib.parse.unquote(form_data.get('user_input'))
    rag_enabled = form_data.get('rag_enabled')

    messages.append(('user', user_input))

    try:
        relevant_documents = retrieval(user_input) if rag_enabled else None
        response = generation(user_input, relevant_documents)

        return StreamingResponse(
            content=response, media_type="text/plain",
            status_code=200, background=None)
    except Exception:
        return Response(status_code=500)


if __name__ == "__main__":
    uvicorn.run('app:app', port=5000, reload=True, host='0.0.0.0')
