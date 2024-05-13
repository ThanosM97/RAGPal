"""This module implements a Flask API for the RAGPal application.

Endpoints:
'/' : Endpoint for home/index page (methods: GET)
'/upload' : Endpoint for uploading text files or text input to the knowledge
            base of the RAG model. (methods: GET, POST)
'/view' : Endpoint for viewing the contents of the knowledge base, with an
          option to delete entries. (methods: GET, POST)

WebSockets:
'/send_message' : WebSocket for sending a request to the LLM to obtain a
                  response based on user's prompt. Sends the streamed
                  response through the websocket.

Clients:
'VectorDatabaseClient' : Implements the required operations in Qdrant.
'RAGClient' : Implements the functionality of the RAG pattern.
"""
import time

import uvicorn
from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from clients import RAGClient, VectorDatabaseClient

# Initialize FASTAPI app
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set config path
config_path = 'config.yaml'

# Initialize the vector database client
vector_db = VectorDatabaseClient(config_path=config_path)

# Initialize the RAG client
rag_client = RAGClient(config_path=config_path)


@app.get('/', response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html",
                                      context={"request": request})


@app.websocket("/send_message")
async def send_message(websocket: WebSocket) -> None:
    await websocket.accept()

    args = await websocket.receive_json()

    user_input = args['prompt']
    rag_enabled = args['ragEnabled']
    history = args['history']

    try:
        relevant_documents = rag_client.retrieve_documents(
            user_input, vector_db) if rag_enabled else None

        await rag_client.generate_completion(
            websocket, user_input, history, relevant_documents)

    except Exception:
        await websocket.close(code=1011)


@app.get("/upload", response_class=HTMLResponse)
def upload_get(request: Request):

    return templates.TemplateResponse(
        "upload.html",  context={
            "request": request, "alert_type": None, "alert": None})


@app.post("/upload", response_class=HTMLResponse)
async def upload_post(request: Request):
    alert = None
    alert_type = None
    document = None

    form_data = await request.form()

    try:
        if 'text' in form_data:  # Text field was used
            document = form_data.get('text')
            alert_type = "success"
            alert = "Text sucessfully uploaded."
        elif 'file' in form_data:  # File was selected
            document = await form_data.get('file').read()
            document = document.decode('utf-8')
            alert_type = "success"
            alert = "Files sucessfully uploaded."
    except Exception as e:
        alert_type = "danger"
        alert = "No files were uploaded. " + str(e)

    if document is not None:  # Text or file was uploaded
        short_desc = " ".join(document.split(" ")[:15]) + "..."

        try:
            # Generate document embeddings
            embd = rag_client.create_embedding(text=document)
        except Exception:
            return Response(status=500)

        doc = {
            "content": document,
            "short_desc": short_desc,
            "uploaded": time.time()
        }

        # # Add document to knowledge base
        vector_db.add(embd, doc)

    return templates.TemplateResponse(
        "upload.html",  context={
            "request": request, "alert_type": alert_type, "alert": alert})


@app.get("/view", response_class=HTMLResponse)
def view_get(request: Request, limit: int = 10):

    scroll_results = vector_db.scroll(limit)

    documents = [(record.id, record.payload["short_desc"])
                 for record in scroll_results]

    return templates.TemplateResponse(
        "view.html",  context={
            "request": request, "documents": documents})


@app.delete("/view")
async def view_delete(request: Request) -> Response:
    form_data = await request.form()

    try:
        vector_db.delete(form_data.get('id'))
        return Response("Succesfully deleted.", status_code=200)
    except Exception:
        return Response("Document not found.", status_code=404)


if __name__ == "__main__":
    uvicorn.run('app:app', port=5000, reload=True, host='0.0.0.0')
