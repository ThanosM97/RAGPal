""" This module implements a Flask API for the RAGPal application.

Endpoints:
'/' : Endpoint for home/index page (methods: GET)
'/send_message' : Endpoint for sending a request to the LLM to obtain a
                  response based on user's prompt. (methods: POST,
                  request args: `user-input`)
"""
import time
from typing import Generator

from flask import Flask, Response, render_template, request
from lorem_text import lorem

app = Flask(__name__)
messages = []


def ask_LLM(prompt: str) -> Generator[bytes, None, str]:
    # TODO: Send a request to the selected LLM
    response = lorem.paragraph()

    # Simulate bot response in chunks
    for sentence in response.split(","):
        time.sleep(2)  # Simulate delay
        yield sentence.encode('utf-8')

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
