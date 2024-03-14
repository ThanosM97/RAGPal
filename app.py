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
from typing import Generator, List, Optional

import yaml
from dotenv import load_dotenv
from flask import Flask, Response, render_template, request
from openai import AzureOpenAI
from qdrant_client import QdrantClient, models

# Initialize Flask app
app = Flask(__name__)

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
    collection_name="Knowledge Base",
    vectors_config=models.VectorParams(
        size=config['azure-openai']['embedding']['vector_size'],
        distance=models.Distance.COSINE,
    ),
)

# Global variables
messages = []
uid = 0


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
        collection_name="Knowledge Base",
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


@app.route('/', methods=['GET'])
def home() -> str:
    return render_template(
        "index.html",  messages=messages)


@app.route("/send_message", methods=["POST"])
def send_message() -> Flask.response_class:
    prompt = request.form['user-input']
    rag_enabled = request.form['rag-enabled'] == 'true'
    messages.append(('user', prompt))

    try:
        relevant_documents = retrieval(prompt) if rag_enabled else None
        response = generation(prompt, relevant_documents)

        return Response(response, content_type="text/plain",
                        status=200, direct_passthrough=True)
    except Exception:
        return Response(status=500)


@app.route('/upload', methods=['GET', 'POST'])
def upload() -> str:
    global uid

    alert = None
    alert_type = None
    document = None

    if request.method == "POST":
        try:
            if 'text' in request.form:  # Text field was used
                document = request.form['text']
                alert_type = "success"
                alert = "Text sucessfully uploaded."
            elif 'file' in request.files:  # File was selected
                document = request.files['file'].read().decode('utf-8')
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
                "short_desc": short_desc
            }

            qdrant.upload_points(
                collection_name="Knowledge Base",
                points=[
                    models.PointStruct(
                        id=uid,
                        vector=embd, payload=doc
                    )
                ]
            )

            uid += 1

    return render_template(
        "upload.html",  alert_type=alert_type, alert=alert)


@app.route('/view', methods=['GET', 'POST'])
def view() -> str:
    if request.method == "POST":  # Delete entry request
        doc_id = int(request.form['id'])

        try:
            qdrant.delete(
                collection_name="Knowledge Base",
                points_selector=[doc_id]
            )
            return Response("Successfully deleted.", status=200)
        except Exception:
            return Response(
                "Document is not in the Knowledge Base.", status=404)

    # Default limit
    limit = int(request.args.get('limit')) if 'limit' in request.args else 10

    scroll_results = qdrant.scroll(
        collection_name="Knowledge Base",
        with_vectors=False,
        with_payload=True,
        limit=limit
    )[0]
    documents = [(record.id, record.payload["short_desc"])
                 for record in scroll_results]

    return render_template("view.html", documents=documents)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
