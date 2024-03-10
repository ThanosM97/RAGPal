""" This module implements a Flask API for the RAGPal application.

Endpoints:
'/' : Endpoint for home/index page (methods: GET)
'/send_message' : Endpoint for sending a request to the LLM to obtain a
                  response based on user's prompt. (methods: POST,
                  request args: `user-input`)
"""
from flask import Flask, render_template, request, jsonify
from lorem_text import lorem

app = Flask(__name__)
messages = []


def ask_LLM(prompt: str) -> str:
    # TODO: Send a request to the selected LLM
    response = lorem.paragraph()
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
    messages.append(('bot', response))

    return jsonify({'bot_response': response})


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
