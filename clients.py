"""This module implements clients for RAG and Qdrant operations.

- VectorDatabaseClient: It is a wrapper class for Qdrant operations. It
    implements search, scroll, add, and delete methods.
- RAGClient: A class for the functionality of the RAG pattern. It implements
    the create_embedding and generate_completion methods utilizing the
    AzureOpenAI client, and the retrieve_documents method through the
    VectorDatabaseClient.
"""
import os
import uuid
from pathlib import Path

import yaml
from dotenv import load_dotenv
from fastapi import WebSocket
from openai import AzureOpenAI
from qdrant_client import QdrantClient, models


class VectorDatabaseClient:
    """Implements Qdrant operations."""

    def __init__(self, config_path: str | Path) -> None:
        """Initializes the VectorDatabaseClient.

        Args:
            config_path (str | Path): Path to RAGPal's configuration file.
        """
        # Load config variables from config.yaml
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Initialize Qdrant client
        self.qdrant = QdrantClient(location=":memory:")

        # Create the collection
        self.qdrant.recreate_collection(
            collection_name=self.config['qdrant']['collection_name'],
            vectors_config=models.VectorParams(
                size=self.config['azure-openai']['embedding']['vector_size'],
                distance=models.Distance.COSINE,
            ),
        )

    def search(self, query_embedding: list[float]) -> list:
        """Searches for relevant points to `query_embedding`.

        This method calculates the cosine similarity between the input
        `query_embedding` and the embeddings of each document in the
        knowledge base, and retrieves only the top_k most similar documents.

        Args:
            query_embedding (list[float]): Query embedding.

        Returns:
            list[Points]: A list of the top_k relevant points to
                `query embedding`
        """
        hits = self.qdrant.search(
            collection_name=self.config['qdrant']['collection_name'],
            query_vector=query_embedding,
            limit=self.config['qdrant']['top_k']
        )
        return hits

    def scroll(self, limit: int) -> list:
        """Returns the first `limit` points of the Vector Database.

        Args:
            limit (int): Number of points to return.

        Returns:
            list: A list of `limit` points.
        """
        return self.qdrant.scroll(
            collection_name=self.config['qdrant']['collection_name'],
            with_vectors=False,
            with_payload=True,
            order_by="uploaded",
            limit=limit
        )[0]

    def add(self, embedding: list[float], document: dict[str, any]) -> None:
        """Adds a point to the Vector Database.

        Args:
            embedding (list[float]): The embedding of the point.
            document (dict): The payload of the point.
        """
        self.qdrant.upload_points(
            collection_name=self.config['qdrant']['collection_name'],
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding, payload=document
                )
            ]
        )

    def delete(self, point_id: int) -> None:
        """Deletes a point from the Vector Database.

        Args:
            point_id (int): The id of the point to delete.
        """
        self.qdrant.delete(
            collection_name=self.config['qdrant']['collection_name'],
            points_selector=[point_id]
        )


class RAGClient:
    """Implements the functionality of the RAG pattern."""

    def __init__(self, config_path: str | Path) -> None:
        """Initializes the RAGClient.

        Args:
            config_path (str | Path): Path to RAGPal's configuration file.
        """
        # Load config variables from config.yaml
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.__init_azure_client()

    def __init_azure_client(self) -> None:
        """Initializes the AzureOpenAI client with environmental variables."""
        load_dotenv()
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        OPENAI_API_BASE = os.getenv("OPENAI_API_BASE")

        self.azure_client = AzureOpenAI(
            api_key=OPENAI_API_KEY,
            azure_endpoint=OPENAI_API_BASE,
            api_version=self.config['azure-openai']['client']['api_version'])

    def create_embedding(self, text: str) -> list[float]:
        """Creates the embedding of input `text`.

        This method makes a request to AzureOpenAI embeddings endpoint to
        generate embeddings for input `text`.

        Args:
            text (str): The text to embed.

        Returns:
            list[float]: The embeddings of the input `text`.
        """
        return list(self.azure_client.embeddings.create(
            input=text,
            model=self.config['azure-openai']['embedding']['model']
        ).data[0].embedding)

    def retrieve_documents(
            self, prompt: str, vector_db: VectorDatabaseClient) -> list[str]:
        """Returns relevant documents to `prompt`.

        This method first generates embeddings for the input `prompt`. Then,
        the top_k most relevant points to the embeddings of the input `prompt`
        are retrieved from the vector database. Finally, the documents in the
        payload of the retrieved points are returned.

        Args:
        - prompt (str): User input/prompt.
        - vector_db: The VectorDatabaseClient.

        Returns:
            A list of top_k relevant documents.
        """
        # Generate query embeddings
        query_embedding = self.create_embedding(prompt)

        hits = vector_db.search(query_embedding)

        relevant_documents = [hit.payload["content"] for hit in hits]
        return relevant_documents

    async def generate_completion(
        self,
        websocket: WebSocket,
        prompt: str,
        history: list[dict],
        relevant_documents: list[str] | None = None
    ) -> None:
        """Sends chunks of AzureOpenAI API's streamed response via a
        `websocket`.

        This asynchronous method takes as input a user `prompt`, the
        conversation history, and the retrieved `relevant_documents`. It makes
        a request to AzureOpenAI's chat completion API using formatting,
        RAG-specific instructions for the generation process, the relevant
        docuements, and the user prompt. It sends the chunks of the API's
        response through the `websocket` as they arrive.

        If the `relevant_documents` argument is None, the user has disabled the
        RAG functionality, so a generic request will be made to AzureOpenAI's
        chat completion API using only the `input_prompt`, the conversation
        history, and the formatting isntruction.

        Args:
        - websocket (WebSocket): Established WebSocket for messages.
        - prompt (str): User input/prompt.
        - history (List[dict]): The conversation history containing the
            query/response pairs in the OpenAI format:
                [
                    {"role":"user", "content":"user_query"},
                    {"role":"assistant", "content":"assistant_response"}
                ]
        - relevant_documents (list | None): A list of relevant documents to
                                            the input prompt, or None.
        """
        # Formatting instruction
        instruction = ("You are a multilingual virtual assistant. " +
                       "Respond using Markdown if formatting is needed. ")

        if relevant_documents is None:  # RAG functionality disabled
            message_text = history.copy()
            message_text.extend([
                {"role": "system", "content": instruction},
                {"role": "user", "content": prompt}])
        else:  # with RAG
            rag_instructions = """
                Do not justify your answers. Forget the information you have
                outside of context and conversation history. If the answer to
                the question is not provided in the context, say I don't know
                the answer to this question in the appropriate language. Do not
                mention that context is provided to the user. Based on these
                instructions, and the relevant context, answer the following
                question:"""

            documents = "[NEW DOCUMENT]: ".join(relevant_documents)
            message_text = history.copy()
            message_text.extend([
                {"role": "system", "content": instruction},
                {
                    "role": "system",
                    "content": f"Relevant context: {documents}"
                },
                {"role": "user", "content": rag_instructions + prompt}])

        chat_completion = self.azure_client.chat.completions.create(
            messages=message_text,
            model=self.config['azure-openai']['chat-completion']['model'],
            stream=True,
            temperature=0.7  # Makes the model more focused and deterministic
        )

        response = []
        for chunk in chat_completion:
            if len(chunk.choices) > 0:
                msg = chunk.choices[0].delta.content
                msg = "" if msg is None else msg
                response.append(msg)

                await websocket.send_json({"text": msg})

        response = "".join(response)

        await websocket.close(reason="End of Message")
