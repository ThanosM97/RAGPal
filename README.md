<h1 align="center">RAGPal</h1>


This repository hosts a simplified proof-of-concept implementation of a RAG-based virtual assistant.

## Retrieval Augmented Generation (RAG)
The Retrieval Augmented Generation (RAG) approach combines the power of document retrieval techniques and generative models in natural language processing tasks. It utilizes a **retriever** to extract relevant documents from a large database, which is then fed into a **generative** model along with the input query to produce a response. This approach enhances the generatiion process by providing the model with access to contextual-relevant information, enabling it to generate more accurate responses. 

## Implementation
![RAGPal architecture](https://github.com/ThanosM97/RAGPal/assets/41332813/c9773a55-3105-45b7-8c6e-dc1e352d0be4)

RAGPal is implemented as a web application with a front-end interface for user interaction and a Flask-based back-end for handling requests and business logic. The system utilizes Azure OpenAI API resources for chat completion and embedding generation, and the Qdrant vector database to serve as the knowledge base for storing and retrieving documents. 

### Endpoints
* `/` : Endpoint to get home/index page (method: GET).
* `/send_message` : Endpoint for sending a request to AzureOpenAI API resources to obtain a response based on user's prompt. Returns the streamed response. (method: POST).
* `/upload` : Endpoint for uploading text files or text input to the knowledge base of the RAG model. (methods: GET, POST).
* `/view` : Endpoint for viewing the contents of the knowledge base, with an option to delete entries. (methods: GET, POST).

### Technologies Used
* **Front-end**: HTML is used to define the structure of the application's content, CSS to determine style and layout, and JavaScript enables the Single-Page Application (SPA) functionallity of the web application.
* **Back-end**: Flask API handles the back-end RAG logic, including processing user queries, interacting with Azure OpenAI APIs, and querying the Qdrant vector database.
* **Azure OpenAI APIs**: The chat-completion model is utilized for generating text responses, while the embedding-ada model produces embeddings for input queries (i.e., user messages) and documents in the database.
* **Qdrant Vector Database**: Used as an in-memory knowledge base, storing documents and facilitating vector similarity search for retrieving query-relevant information.
