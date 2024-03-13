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

## Getting Started
1. In order for RAGPal to work, you would need to have access to AzureOpenAI resources for chat-completion and embeddings. Then, you can modify `config.yaml` to the corresponding resources that you have access to.
2. Create a .env file in the root directory with the following variables
   ```
   OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
   OPENAI_API_BASE=<OPENAI_API_ENDPOINT>
   ```
3. Run the application:
     * **Docker**:
       If you have docker installed, you can build a docker image and deploy the RAGPal application using the following commands in the root directory.
       ```bash
       docker build -t ragpal .
       docker run -d -p 5000:5000 --name RAGPAL ragpal
       ```
   * **Python (conda)**: The RAGPal application was developed in Python 3.9. Use the following commands in the root directory to create a virtual environment with conda, install the required packages, and run the application.
     ```bash
     # Create a virtual environment with conda
     conda create -n ragpal python=3.9

     # Activate conda environment
     conda activate ragpal

     # Install required packages
     pip install -r requirements.txt

     # Run the RAGPal app
     python app.py
     ```
    * **Python**: The RAGPal application was developed in Python 3.9, and it needs to be installed prior to the creation of the virtual environment. Use the following commands in the root directory to create a python virtual environment, install the required packages, and run the application.
       ```bash
       # Create a Python virtual environment
       python3.9 -m venv venv
  
       # Activate the virtual environment on Windows
       venv\Scripts\activate
  
       # Activate the virtual environment on Linux/macOS
       source venv/bin/activate
  
       # Install required packages
       pip install -r requirements.txt
  
       # Run the RAGPal app
       python app.py
       ```
