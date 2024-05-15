"""This module implements a CLI Client for RAGPal."""
import argparse
import asyncio

from network import http_request, websocket_request

# ANSI escape codes for colors
COLOR_CYAN = "\033[36m"  # Cyan
COLOR_GREEN = "\033[32m"   # Green
COLOR_RESET = "\033[0m"   # Reset color

# AGENT AND USER TAGS
AGENT_TAG = f"{COLOR_GREEN}Agent:{COLOR_RESET}: "
USER_TAG = f"{COLOR_CYAN}You:{COLOR_RESET}: "


async def chat(
        prompt: str,
        endpoint: str,
        rag_enabled: bool,
        message_history: list[dict]) -> str:
    """Communicates with RAGPal and prints the response.

    This function communicates with RAGPal's REST API asynchronously
    in the case of a streaming response through a websocket, or via an HTTP
    POST request. It sends the user query along with the conversation history
    and prints RAGPal's response.

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
        str: RAGPal's response.
    """
    print(AGENT_TAG, end='', flush=True)

    if endpoint.startswith("ws"):  # Streamed communication through websocket
        response = []
        async for message in websocket_request(
                prompt, endpoint, rag_enabled, message_history):
            print(message, end='', flush=True)
            response.append(message)

        print("\n")  # Add a newline after the complete streamed response
        return "".join(response)

    else:  # Communication through POST request
        response = http_request(prompt, endpoint, rag_enabled, message_history)
        print(response + "\n")
        return response


async def main(
        endpoint: str, rag_enabled: bool = False, history: int = 5) -> None:
    """Implements the CLI client.

    Args:
        endpoint (str): RAGPal's REST API endpoint for chatting.
        rag_enabled (bool): Whether to use RAG functionality. Defaults to
            False.
        history (int, optional): The number of query/response pairs to be
            passed as conversation history to RAGPal. Defaults to 5.
    """
    msg = "RAGPal CLI Client (Type 'exit' to quit)"
    print("\t\t" + "-"*len(msg))
    print(f"\t\t{msg}")
    print("\t\t" + "-"*len(msg) + "\n")
    message_history = []

    print(f"{AGENT_TAG}Hello, how may I assist you?\n")

    response = None
    while True:
        prompt = input(USER_TAG)

        if prompt.lower() == "exit":
            print("Exiting RAGPal CLI Client.")
            break

        response = await chat(
            prompt, endpoint, rag_enabled, message_history[-history*2:])

        if (history > 0 and not response.startswith(
                "Error while communicating with RAGPal")):
            message_history.append({"role": "user", "content": prompt})
            message_history.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='RAGPal CLI Client')
    parser.add_argument(
        '--endpoint',
        required=True,
        help='URL of RAGPal API endpoint')
    parser.add_argument(
        '--rag',
        action='store_true',
        help='Enable RAG functionality.')
    parser.add_argument(
        '--history',
        type=int,
        default=5,
        help='Number of query/response pairs to use as conversation history')
    args = parser.parse_args()

    endpoint = args.endpoint
    history = args.history
    rag_enabled = args.rag

    asyncio.run(main(endpoint, rag_enabled, history))
