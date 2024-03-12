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

import numpy as np
from flask import Flask, Response, render_template, request
from openai import AzureOpenAI
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

# Global variables
messages = []
knowledge_base = {}
uid = 0

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")


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
    relevant_documents = []

    client = AzureOpenAI(
        api_key=OPENAI_API_KEY,
        azure_endpoint=OPENAI_API_BASE,
        api_version="2023-07-01-preview"
    )

    # Generate query embeddings
    query_embedding = np.array(client.embeddings.create(
        input=prompt,
        model="embedding-ada"
    ).data[0].embedding)

    # Comput the cosine similarity between query and document embeddings
    for doc_info in knowledge_base.values():
        sim = cosine_similarity(
            query_embedding.reshape(1, -1),
            doc_info['embedding'].reshape(1, -1))

        if sim > 0.8:
            relevant_documents.append(doc_info['content'])

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
    client = AzureOpenAI(
        api_key=OPENAI_API_KEY,
        azure_endpoint=OPENAI_API_BASE,
        api_version="2023-07-01-preview"
    )

    # Formatting instruction
    instruction = "Respond using Markdown if formatting is needed. "

    if relevant_documents is None:  # RAG functionality disabled
        message_text = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": prompt}]
    else:  # with RAG
        rag_instructions = (
            "Do not justify your answers. " +
            "Forget the information you have outside of context." +
            "If the answer to the question is not provided in the context, " +
            "say I don't know the answer to this question." +
            "Do not mention that context is provided to the user. " +
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

    chat_completion = client.chat.completions.create(
        messages=message_text,
        model="gpt-4-turbo",
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

    relevant_documents = retrieval(prompt) if rag_enabled else None
    response = generation(prompt, relevant_documents)

    return Response(response, content_type="text/plain",
                    status=200, direct_passthrough=True)


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
            client = AzureOpenAI(
                api_key=OPENAI_API_KEY,
                azure_endpoint=OPENAI_API_BASE,
                api_version="2023-07-01-preview"
            )

            # Generate document embeddings
            embd = np.array(client.embeddings.create(
                input=document,
                model="embedding-ada"
            ).data[0].embedding)

            # Add document to knowledge base
            knowledge_base[uid] = {
                "content": document,
                "short_desc": short_desc,
                "embedding": embd
            }

            uid += 1

    return render_template(
        "upload.html",  alert_type=alert_type, alert=alert)


@app.route('/view', methods=['GET', 'POST'])
def view() -> str:
    if request.method == "POST":  # Delete entry request
        doc_id = int(request.form['id'])

        if doc_id in knowledge_base:
            del knowledge_base[doc_id]
            return Response("Successfully deleted.", status=200)
        else:
            return Response(
                "Document is not in the Knowledge Base.", status=404)

    documents = [(key, doc['short_desc'])
                 for key, doc in knowledge_base.items()]

    return render_template("view.html", documents=documents)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
