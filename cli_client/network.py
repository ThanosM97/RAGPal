"""This module implements the communication with RAGPal's API."""
import json
from typing import AsyncGenerator

import requests
import websockets


async def websocket_request(
        prompt: str,
        endpoint: str,
        rag_enabled: bool,
        message_history: list[dict]) -> AsyncGenerator[str, None]:
    """Communicates with RAGPal through a WebSocket.

    Args:
        prompt (str): The user's query.
        endpoint (str): RAGPal's REST API endpoint for chatting.
        rag_enabled (bool): Whether to use RAG functionality.
        message_history (list[dict]): The conversation history containing the
            last `history` query/response pairs, as defined in the `main`
            function. It is a list of dictionaries in the structure required
            by OpenAI:
                [
                    {"role":"user", "content":"user_query"},
                    {"role":"assistant", "content":"assistant_response"}
                ]

    Yields:
        str: A chunk of RAGPal's response.
    """
    try:
        async with websockets.connect(endpoint) as websocket:
            # Serialize the data as JSON before sending
            message = json.dumps(
                {"prompt": prompt,
                 "ragEnabled": rag_enabled,
                 "history": message_history})
            await websocket.send(message)

            async for chunk in websocket:
                yield json.loads(chunk)['text']

    except Exception as e:
        yield f"Error while communicating with RAGPal via WebSocket: {e}"


def http_request(
        prompt: str,
        endpoint: str,
        rag_enabled: bool,
        message_history: list[dict]) -> str:
    """Communicates with RAGPal through an HTTP POST request.

    Args:
        prompt (str): The user's query.
        endpoint (str): RAGPal's REST API endpoint for chatting.
        rag_enabled (bool): Whether to use RAG functionality.
        message_history (list[dict]): The conversation history containing the
            last `history` query/response pairs, as defined in the `main`
            function. It is a list of dictionaries in the structure required
            by OpenAI:
                [
                    {"role":"user", "content":"user_query"},
                    {"role":"assistant", "content":"assistant_response"}
                ]

    Returns:
        str: RAGPal's complete response.
    """
    try:
        response = requests.post(
            endpoint,
            json={
                "prompt": prompt,
                "ragEnabled": rag_enabled,
                "history": message_history})
        response.raise_for_status()
        return response.json()['text']
    except requests.RequestException as e:
        # Handle exceptions if the request fails
        return f"Error while communicating with RAGPal via HTTP: {e}"
