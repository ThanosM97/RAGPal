"""This module implements a Flask API for the RAGPal application.

Endpoints:
'/' : Endpoint for home/index page (methods: GET)
'/send_message' : Endpoint for sending a request to the LLM to obtain a
                  response based on user's prompt. Returns the streamed
                  response. (methods: POST, request args: `user-input`)

Functions:
'ask_LLM' : Makes the request to AzureOpenAI API given an input string
            `prompt`. The response is a stream, so the function is a
            Generator that yields chunks of the response as they come.
"""
import os
from typing import Generator

from flask import Flask, Response, render_template, request
from openai import AzureOpenAI

app = Flask(__name__)
messages = []

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")


def ask_LLM(prompt: str) -> Generator[bytes, None, str]:
    client = AzureOpenAI(
        api_key=OPENAI_API_KEY,
        azure_endpoint=OPENAI_API_BASE,
        api_version="2023-07-01-preview"
    )

    message_text = [{"role": "user", "content": prompt}]

    chat_completion = client.chat.completions.create(
        messages=message_text,
        model="gpt-4-turbo",
        stream=True
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
    form = request.form
    messages.append(('user', form['user-input']))

    response = ask_LLM(form['user-input'])

    return Response(response, content_type="text/plain",
                    status=200, direct_passthrough=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
