"""This module implements a Flask API for the RAGPal application.

Endpoints:
'/' : Endpoint for home/index page (methods: GET)
'/send_message' : Endpoint for sending a request to the LLM to obtain a
                  response based on user's prompt. Returns the streamed
                  response. (methods: POST, request args: `user-input`)

Functions:
'generation' : Makes the request to AzureOpenAI API given an input string
               `prompt` and a list of `relevant_documents`. The response is
               a stream, so the function is a Generator that yields chunks
               of the response as they come.
'retrieval' : Retrieves and returns relevant documents to the input string
              argument `prompt`.
"""
import os
from typing import Generator, List

from flask import Flask, Response, render_template, request
from openai import AzureOpenAI

app = Flask(__name__)
messages = []

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")


def retrieval(prompt: str) -> List[str]:
    """Returns relevant documents to `prompt`.

    Args:
    - prompt (str): User input/prompt.

    Returns:
        A list of relevant documents.
    """
    # TODO: Add retrieval process or return custom text
    return []


def generation(
    prompt: str,
    relevant_documents: List[str]
) -> Generator[bytes, None, str]:
    """Yields chunks of AzureOpenAI API's streamed response.

    This generator function takes as input a user `prompt` and the retrieved
    `relevant_documents`. It makes a request to AzureOpenAI's API using
    formatting and RAG-specific instructions for the generation process,
    the relevant docuements, and the user prompt. It yields the chunks of
    the API's response as they come.

    Args:
    - prompt (str): User input/prompt.
    - relevant_documents (List): A list of relevant documents to the prompt.

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

    instruction = "Respond using Markdown if formatting is needed. "

    rag_instructions = (
        "Do not justify your answers. " +
        "Forget the information you have outside of context." +
        "If the answer to the question is not provided in the context, say" +
        "I don't know the answer to this question." +
        "Do not mention that context is provided to the user. " +
        "Based on these instructions, and the relevant context, answer this:")

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
    messages.append(('user', prompt))

    relevant_documents = retrieval(prompt)
    response = generation(prompt, relevant_documents)

    return Response(response, content_type="text/plain",
                    status=200, direct_passthrough=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
