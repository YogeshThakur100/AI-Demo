from fastapi import APIRouter , Request
from fastapi.responses import Response , PlainTextResponse
from main import main_app
from dotenv import load_dotenv , find_dotenv
from whatsapp_util import send_whatsapp
from web_scraping import crawl
from pathlib import Path
from rag_pipeline import ai_response , load_document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os

app = APIRouter()

load_dotenv(find_dotenv())

VERIFY_TOKEN = os.getenv('ACCESS_TOKEN')
current_directory = Path(__file__).parent
vector_store_path = os.path.join(current_directory, "Vector Database")
file_path = os.path.join(vector_store_path , "whatsapp_ai_receptionist")
index_file_path = os.path.join(file_path , "index.faiss")

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

@app.get("/status")
def get_status():
    return ("status" , "Receptionist API is running")


@app.get("/whatsapp/webhook")
async def verify_webhook(request: Request):

    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge)

    return PlainTextResponse("Verification failed", status_code=403)


@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request):

    data = await request.json()
    print("data ----->" , data)

    value = data['entry'][0]['changes'][0]['value']

    if "messages" not in value:   
        print("No messages found in the webhook data")
        return {"status" : "ignored"}

    message = data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
    sender = data["entry"][0]["changes"][0]["value"]["messages"][0]["from"]

    print("Message:", message)
    print("Sender:", sender)

    #######################################################
    try:
        vectorstore = FAISS.load_local(
                    file_path,  # ✅ Pass directory path, not file path
                    embeddings, 
                    allow_dangerous_deserialization=True
                )
        response = ai_response.create_rag_qa(vectorstore , message , sender)
    except Exception as e:
        print(f"❌ Error loading vector store from {file_path}: {e}")
        ai_reply = "Sorry, I'm unable to process your request right now. Please try again later."
        await send_whatsapp.send_whatsapp_message(sender, ai_reply)
        return {"status": "error", "message": str(e)}

    #######################################################


    # send to AI
    ai_reply = response["answer"]
    await send_whatsapp.send_whatsapp_message(sender , ai_reply)

    # await send_whatsapp_message(sender, ai_reply)



main_app.include_router(app , prefix="/api/receptionist" , tags=["Receptionist API"])