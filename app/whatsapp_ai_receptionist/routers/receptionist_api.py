from fastapi import APIRouter , Request , Depends
from fastapi.responses import Response , PlainTextResponse
from main import main_app
from dotenv import load_dotenv , find_dotenv
from whatsapp_util import send_whatsapp
from web_scraping import crawl
from pathlib import Path
from rag_pipeline import ai_response , load_document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from database import get_db
from sqlalchemy.orm import Session
from whatsapp_ai_receptionist.models.business_profile import BusinessProfile , PreLoadedVerticalClinic , PreLoadedVerticalCACS
from whatsapp_ai_receptionist.schemas.business_schemas import businessProfile , PreLoadedVerticalFAQSClinic , PreLoadedVerticalFAQSCACS
import os
import uuid
from datetime import datetime
from rag_pipeline.vector_creation import build_vectorstore

app = APIRouter()

load_dotenv(find_dotenv())

#webhook access token 
VERIFY_TOKEN = os.getenv('ACCESS_TOKEN')

#vector store paths
current_directory = Path(__file__).parent.parent
crawling_document_path = os.path.join(current_directory , "Crawl Document")
vector_store_path = os.path.join(current_directory, "Vector Database")
file_path = os.path.join(vector_store_path , "whatsapp_ai_receptionist")
index_file_path = os.path.join(file_path , "index.faiss")

#embeddings for rag
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

@app.get("/status")
def get_status():
    return ("status" , "Receptionist API is running")


@app.post('/crawling-website')
def crawling_website(url: str):
    crawling_document_name = os.path.join(crawling_document_path , "whatsapp_ai_receptionist.txt")
    try:
        crawl.crawler(url , crawl_document_path=crawling_document_name)
    except Exception as e:
        print(f"❌ Error during crawling: {e}")
        return {"status": "error", "message": str(e)}
    
    #Creating vector database
    try:
        #load document
        documents = load_document.load_txt_data(crawling_document_name)

        vector_store = build_vectorstore(save_path=file_path , website_docs=documents)
    except Exception as e:
        print(f"❌ Error during vector store creation: {e}")
        return {"status": "error", "message": str(e)}
    
    return {
        "status": "success",
        "message": "Website crawled and vector store created successfully"
    }
        
@app.post("/add-preload-faqs_clinic")
def add_preload_faqs(faqs: list[PreLoadedVerticalFAQSClinic] , db : Session = Depends(get_db)):
    try:
        for faq in faqs:
            new_faq = PreLoadedVerticalClinic(
                question_name = faq.question_name,
                answer = faq.answer,
                created_at = datetime.now()
            )
            db.add(new_faq)
        db.commit()
    except Exception as e:
        print(f"❌ Error adding preloaded FAQs: {e}")
        return {"status": "error", "message": str(e)}
    return {
        "status": "success",
        "message": "Preloaded FAQs added successfully"
    }

@app.get('/get-preload-faqs_clinic')
def get_preload_faqs(db : Session = Depends(get_db)):
    try:
        faqs = db.query(PreLoadedVerticalClinic).all()
    except Exception as e:
        print(f"❌ Error retrieving preloaded FAQs: {e}")
        return {"status": "error", "message": str(e)}
    return {
        "status" : "success",
        "data" : faqs
    }

@app.put('/update-preload-faqs-clinic')
def update_preload_faq(faq_id , faq_update: PreLoadedVerticalFAQSClinic, db: Session = Depends(get_db)):
    try:
        faq = db.query(PreLoadedVerticalClinic).filter(PreLoadedVerticalClinic.id == faq_id).first()
        if not faq:
            return {
                "status" : "error",
                "message" : f"FAQ with id {faq_id} not found"
            }
        faq.question_name = faq_update.question_name
        faq.answer = faq_update.answer
        faq.created_at = datetime.now()
        db.commit()
        db.refresh(faq)
    except Exception as e:
        return {
            "success" : "error",
            "message" : str(e)
        }
    return {
        "success" : "success",
        "message" : f"FAQ with id {faq_id} updated successfully",
        "data" : faq
    }


@app.post("/add-preload-faqs_cacs")
def add_preload_faqs(faqs: list[PreLoadedVerticalFAQSCACS] , db : Session = Depends(get_db)):
    try:
        for faq in faqs:
            new_faq = PreLoadedVerticalCACS(
                question_name = faq.question_name,
                answer = faq.answer,
                created_at = datetime.now()
            )
            db.add(new_faq)
        db.commit()
    except Exception as e:
        print(f"❌ Error adding preloaded FAQs: {e}")
        return {"status": "error", "message": str(e)}
    return {
        "status": "success",
        "message": "Preloaded FAQs added successfully"
    }
@app.get('/get-preload-faqs_cacs')
def get_preload_faqs(db : Session = Depends(get_db)):
    try:
        faqs = db.query(PreLoadedVerticalCACS).all()
    except Exception as e:
        print(f"❌ Error retrieving preloaded FAQs: {e}")
        return {"status": "error", "message": str(e)}
    return {
        "status" : "success",
        "data" : faqs
    }

@app.put('/update-preload-faqs-cacs')
def update_preload_faq(faq_id, faq_update: PreLoadedVerticalFAQSCACS, db: Session = Depends(get_db)):
    try:
        faq = db.query(PreLoadedVerticalCACS).filter(PreLoadedVerticalCACS.id == faq_id).first()
        if not faq:
            return {
                "status" : "error",
                "message" : f"FAQ with id {faq_id} not found"
            }
        faq.question_name = faq_update.question_name
        faq.answer = faq_update.answer
        faq.created_at = datetime.now()
        db.commit()
        db.refresh(faq)
    except Exception as e:
        return {
            "status" : "error",
            "message" : str(e)
        }
    return {
        "status" : "success",
        "message" : f"FAQ with id {faq_id} updated successfully",
        "data" : faq
    }


@app.get("/whatsapp/webhook")
async def verify_webhook(request: Request):

    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge)

    return PlainTextResponse("Verification failed", status_code=403)


@app.get("/get-business-profile")
def get_business_profile(db : Session = Depends(get_db)):
    try:
        vectorstore = FAISS.load_local(
                    file_path, 
                    embeddings, 
                    allow_dangerous_deserialization=True
                )
        response = ai_response.get_business_profile(vectorstore)
    except Exception as e:
        print(e)
        return {"status": "error", "message": str(e)}
    
    try:
        new_business_profile = BusinessProfile(
            businessName = response.get("business_name", "N/A"),
            phoneNumber = response.get("business_phone_number", "N/A"),
            email = response.get("business_email", "N/A"),
            address = response.get("business_address", "N/A"),
            officeHours = response.get("business_working_hours", "N/A"),
            services = response.get("business_services", []),
            created_at = datetime.now()
        )
    except Exception as e:
        print(f"Error creating BusinessProfile instance: {e}")
        return {"status": "error", "message": str(e)}

    db.add(new_business_profile)
    db.commit()
    db.refresh(new_business_profile)

    return {
        "status": "success", 
        "message" : "Information retrived sucessfully",
        "data" : {
            "Business Information" : response
        }

    }


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
    try:
        vectorstore = FAISS.load_local(
                    file_path, 
                    embeddings, 
                    allow_dangerous_deserialization=True
                )
        response = ai_response.create_rag_qa(vectorstore , message , sender)
    except Exception as e:
        print(f"❌ Error loading vector store from {file_path}: {e}")
        ai_reply = "Sorry, I'm unable to process your request right now. Please try again later."
        await send_whatsapp.send_whatsapp_message(sender, ai_reply)
        return {"status": "error", "message": str(e)}

    ai_reply = response["answer"]
    await send_whatsapp.send_whatsapp_message(sender , ai_reply)



main_app.include_router(app , prefix="/api/receptionist" , tags=["Receptionist API"])