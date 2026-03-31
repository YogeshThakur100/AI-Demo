from fastapi import APIRouter , Request , Depends , WebSocket
from fastapi.responses import Response , PlainTextResponse , JSONResponse
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
from website_ai.models.business_profile import BusinessProfileWebsiteAI , PreLoadedVerticalClinicWebsiteAI , PreLoadedVerticalCACSWebsiteAI , ManualWebsiteAI , ConversationWebsiteAI
from website_ai.schemas.business_schemas import businessProfile_Website_ai , PreLoadedVerticalFAQSClinic_Website_ai , PreLoadedVerticalFAQSCACS_Website_ai , ManualFAQS_Website_ai
import os
import uuid
from datetime import datetime
from rag_pipeline.vector_creation import build_vectorstore
import time
from websocketConnection import ConnectionManager
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests


app = APIRouter()

#vector store paths
current_directory = Path(__file__).parent.parent
crawling_document_path = os.path.join(current_directory , "Crawl Document")
if not os.path.exists(crawling_document_path):
    os.makedirs(crawling_document_path)
vector_store_path = os.path.join(current_directory, "Vector Database")
if not os.path.exists(vector_store_path):
    os.makedirs(vector_store_path)
file_path = os.path.join(vector_store_path , "website_ai")
index_file_path = os.path.join(file_path , "index.faiss")

#embeddings for rag
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

@app.get('/status')
def get_status():
    return {"status" : "Website AI is up and running!"}

@app.post('/crawling-website')
def crawling_website(url: str , db : Session = Depends(get_db)):
    business_profile = db.query(BusinessProfileWebsiteAI).first()
    if business_profile:
        return JSONResponse(
            status_code=400,
            content = {
                "success" : False,
                "message" : "Please delete the exisiting business profile to add new one"
            }
        )
    crawling_document_name = os.path.join(crawling_document_path , "website_ai.txt")
    try:
        crawl_document = crawl.crawler(url , crawl_document_path=crawling_document_name)
        print(f"✅ Successfully crawled {url} and crawled urls {crawl_document}")
    except Exception as e:
        print(f"❌ Error during crawling: {e}")
        return {"status": "error", "message": str(e)}
    
    try:
        documents = load_document.load_txt_data(crawling_document_name)

        vector_store = build_vectorstore(save_path=file_path , website_docs=documents)
    except Exception as e:
        print(f"❌ Error during vector store creation: {e}")
        return {"status": "error", "message": str(e)}
    
    vectorstore = FAISS.load_local(
                    file_path, 
                    embeddings, 
                    allow_dangerous_deserialization=True
                )
    response = ai_response.get_business_profile(vectorstore)

    try:
        new_business_profile = BusinessProfileWebsiteAI(
            businessName = response.get("business_name", "N/A"),
            phoneNumber = response.get("business_phone_number", "N/A"),
            email = response.get("business_email", "N/A"),
            address = response.get("business_address", "N/A"),
            officeHours = response.get("business_working_hours", "N/A"),
            services = response.get("business_services", []),
            urlsCrawled = list(crawl_document),
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
        "message": "Website crawled and vector store created successfully",
        "data" : {
            "Business_Information" : response,
            "business_id" : str(new_business_profile.id),
            "crawled_urls" : list(crawl_document)
        }
    }

@app.put('/update-business-profile')
def update_business_profile(usePreLoadedVerticals: bool, profile : businessProfile_Website_ai , business_id : str = None, db : Session = Depends(get_db)):
    try:
        business_profile = db.query(BusinessProfileWebsiteAI).first()
        if not business_profile:
            new_business_profile = BusinessProfileWebsiteAI(
                businessName = profile.business_name,
                phoneNumber = profile.business_phone_number,
                email = profile.business_email,
                address = profile.business_address,
                officeHours = profile.business_working_hours,
                services = profile.business_services,
                business_type = profile.business_type,
                personaSelector = profile.persona_selector,
                created_at = datetime.now(),
                usePreLoadedVerticals = usePreLoadedVerticals
            )
            db.add(new_business_profile)
            db.commit()
            db.refresh(new_business_profile)
            return JSONResponse(
                content={
                    "success" : True,
                    "message" : "Business profile created successfully",
                    "data" : {
                        "businessName" : new_business_profile.businessName,
                        "phoneNumber" : new_business_profile.phoneNumber,
                        "email" : new_business_profile.email,
                        "address" : new_business_profile.address,
                        "officeHours" : new_business_profile.officeHours,
                        "services" : new_business_profile.services,
                    }
                }
            )
        else:
            business_profile.websiteLink = profile.business_website_url
            business_profile.businessName = profile.business_name
            business_profile.phoneNumber = profile.business_phone_number
            business_profile.email = profile.business_email
            business_profile.address = profile.business_address
            business_profile.officeHours = profile.business_working_hours
            business_profile.services = profile.business_services
            business_profile.business_type = profile.business_type
            business_profile.personaSelector = profile.persona_selector
            business_profile.created_at = datetime.now()
            business_profile.usePreLoadedVerticals = usePreLoadedVerticals
            db.commit()
            db.refresh(business_profile)

        if profile.manual_faqs:
            for faq in profile.manual_faqs:
                existing_faq = db.query(ManualWebsiteAI).filter(faq.question == ManualWebsiteAI.question , ManualWebsiteAI.business_id == business_profile.id).first()
                if not existing_faq:
                    new_faq = ManualWebsiteAI(
                        business_id = business_profile.id,
                        question = faq.question,
                        answer = faq.answer,
                        created_at = datetime.now()
                    )
                    db.add(new_faq)
            db.commit()
    except Exception as e:
        print(e)
        return JSONResponse(
            status_code=500,
            content={
                "success" : False,
                "message" : str(e)
            }
        )
    
    return JSONResponse(
        content={
            "success" : True,
            "message" : "Business profile updated successfully",
            "data" : {
                "businessName" : business_profile.businessName,
                "phoneNumber" : business_profile.phoneNumber,
                "email" : business_profile.email,
                "address" : business_profile.address,
                "officeHours" : business_profile.officeHours,
                "services" : business_profile.services,
            }
        }
    )

@app.delete('/delete-manual-faq')
def delete_manual_faq(faq_id : str , db : Session = Depends(get_db)):
    try:
        faq = db.query(ManualWebsiteAI).filter(ManualWebsiteAI.id == faq_id).first()
        if not faq:
            return JSONResponse(
                status_code=404,
                content={
                    "success" : False,
                    "message" : f"Manual FAQ with id {faq_id} not found"
                }
            )
        db.delete(faq)
        db.commit()
        return JSONResponse(
            status_code=200,
            content={
                "success" : True,
                "message" : f"Manual FAQ with id {faq_id} deleted successfully"
            }
        )
    except Exception as e:
        print(e)
        return JSONResponse(
            status_code=500,
            content={
                "success" : False,
                "message" : str(e)
            }
        )
    
@app.get('/get-website-crawled-urls')
def get_website_crawled_urls(db : Session = Depends(get_db)):
    try:
        business_profile = db.query(BusinessProfileWebsiteAI).first()
        if not business_profile:
            return JSONResponse(
                status_code=404,
                content={
                    "success" : False,
                    "message" : "Business profile not found in database"
                }
            )
        return JSONResponse(
            content={
                "success" : True,
                "message" : "Crawled URLs retrieved successfully",
                "data" : {
                    "crawled_urls" : business_profile.urlsCrawled
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success" : False,
                "message" : str(e)
            }
        )
    
@app.get('/get-business-profile-from-db')
def get_business_profile_from_db(db : Session = Depends(get_db)):
    try:
        business_profile = db.query(BusinessProfileWebsiteAI).first()

        if not business_profile:
            return JSONResponse(
                status_code=404,
                content={
                    "success" : False,
                    "message" : "Business profile not found in database"
                }
            )
        
        data = []
        data.append({
            "name" : business_profile.businessName,
            "phone" : business_profile.phoneNumber,
            "email" : business_profile.email,
            "address" : business_profile.address, 
            "operatingHours" : business_profile.officeHours,
            "services" : business_profile.services,
            "type" : business_profile.business_type,
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={  
                "success" : False,
                "message" : str(e)
            }
        )
    return JSONResponse(
        content={
            "success" : True,
            "data" : data
        }
    )

@app.delete('/delete-business-profile')
def delete_business_profile(db : Session = Depends(get_db)):
    try:
        business_profile = db.query(BusinessProfileWebsiteAI).first()
        if not business_profile:
            return JSONResponse(
                status_code=404,
                content = {
                    "success" : False,
                    "message" : "Business profile not found"
                }
            )
        db.delete(business_profile)
        db.commit()

    except Exception as e:
        print(e)
        return JSONResponse(
            status_code=500,
            content = {
                "success" : False,
                "message" : str(e)
            }
        )
    return JSONResponse(
        content = {
            "success" : True,
            "message" : "Business profile deleted successfully"
        }
    )

@app.post("/add-preload-faqs_clinic")
def add_preload_faqs(faqs: list[PreLoadedVerticalFAQSClinic_Website_ai] , db : Session = Depends(get_db)):
    try:
        for faq in faqs:
            new_faq = PreLoadedVerticalClinicWebsiteAI(
                question = faq.question,
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
        faqs = db.query(PreLoadedVerticalClinicWebsiteAI).all()
        data = []
        for faq in faqs:
            data.append({
                "id" : faq.id,
                "question" : faq.question,
                "answer" : faq.answer,
                "created_at" : faq.created_at,
                "source" : "template",
            })
        manual_faqs = db.query(ManualWebsiteAI).all()
        for faq in manual_faqs:
            data.append({
                "id" : str(faq.id),
                "question" : faq.question,
                "answer" : faq.answer,
                "created_at" : str(faq.created_at),
                "source" : "manual",
            })
    except Exception as e:
        print(f"❌ Error retrieving preloaded FAQs: {e}")
        return {"status": "error", "message": str(e)}
    return {
        "status" : "success",
        "data" : data
    }

@app.put('/update-preload-faqs-clinic')
def update_preload_faq(faq_id , faq_update: PreLoadedVerticalFAQSClinic_Website_ai, db: Session = Depends(get_db)):
    try:
        faq = db.query(PreLoadedVerticalClinicWebsiteAI).filter(PreLoadedVerticalClinicWebsiteAI.id == faq_id).first()
        if not faq:
            return {
                "status" : "error",
                "message" : f"FAQ with id {faq_id} not found"
            }
        faq.question = faq_update.question
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

@app.delete('/delete-preload-faqs-clinic')
def delete_preload_faqs(faq_id , db: Session = Depends(get_db)):
    try:
        faq = db.query(PreLoadedVerticalClinicWebsiteAI).filter(PreLoadedVerticalClinicWebsiteAI.id == faq_id).first()
        if not faq:
            return {
                "success" : False,
                "message" : f"FAQ with id {faq_id} not found"
            }
        db.delete(faq)
        db.commit()
    except Exception as e:
        return {
            "success" : False,
            "message" : str(e)
        }
    return {
        "success" : True,
        "message" : f"FAQ with id {faq_id} deleted successfully"
    }

@app.post("/add-preload-faqs_cacs")
def add_preload_faqs(faqs: list[PreLoadedVerticalFAQSCACS_Website_ai] , db : Session = Depends(get_db)):
    try:
        for faq in faqs:
            new_faq = PreLoadedVerticalCACSWebsiteAI(
                question = faq.question,
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
        faqs = db.query(PreLoadedVerticalCACSWebsiteAI).all()
        data = []
        for faq in faqs:
            data.append({
                "id" : faq.id,
                "question" : faq.question,
                "answer" : faq.answer,
                "created_at" : faq.created_at,
                "source" : "template",
            })
        manual_faqs = db.query(ManualWebsiteAI).all()
        for faq in manual_faqs:
            data.append({
                "id" : str(faq.id),
                "question" : faq.question,
                "answer" : faq.answer,
                "created_at" : str(faq.created_at),
                "source" : "manual",
            })
    except Exception as e:
        print(f"❌ Error retrieving preloaded FAQs: {e}")
        return {"status": "error", "message": str(e)}
    return {
        "status" : "success",
        "data" : data
    }

@app.put('/update-preload-faqs-cacs')
def update_preload_faq(faq_id, faq_update: PreLoadedVerticalFAQSCACS_Website_ai, db: Session = Depends(get_db)):
    try:
        faq = db.query(PreLoadedVerticalCACSWebsiteAI).filter(PreLoadedVerticalCACSWebsiteAI.id == faq_id).first()
        if not faq:
            return {
                "status" : "error",
                "message" : f"FAQ with id {faq_id} not found"
            }
        faq.question = faq_update.question
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

@app.delete('/delete-preload-faqs-cacs')
def delete_preload_faqs(faq_id , db: Session = Depends(get_db)):
    try:
        faq = db.query(PreLoadedVerticalCACSWebsiteAI).filter(PreLoadedVerticalCACSWebsiteAI.id == faq_id).first()
        if not faq:
            return {
                "success" : False,
                "message" : f"FAQ with id {faq_id} not found"
            }
        
        db.delete(faq)
        db.commit()
    except Exception as e:
        return {
            "success" : False,
            "message" : str(e),
        }
    return {
        "success" : True,
        "message" : f"FAQ with id {faq_id} deleted successfully"
    }

@app.post('/add-manual-faqs')
def add_manual_faqs(faqs: list[ManualFAQS_Website_ai] , business_id : str , db : Session = Depends(get_db)):
    try:
        for faq in faqs:
            new_faq = ManualWebsiteAI(
                business_id = business_id,
                question = faq.question,
                answer = faq.answer,
                created_at = datetime.now()
            )
            db.add(new_faq)
        db.commit()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content = {
                "success" : False,
                "message" : str(e)
            }
        )
    
    return JSONResponse(
        content = {
            "success" : True,
            "message" : "Manual FAQs added successfully"
        }
    )

@app.get('/get-manual-faqs')
def get_manual_faqs(business_id : str , db : Session = Depends(get_db)):
    try:
        faqs = db.query(ManualWebsiteAI).filter(ManualWebsiteAI.business_id == business_id).all()
        data = []
        for faq in faqs:
            data.append({
                "id" : str(faq.id),
                "question" : faq.question,
                "answer" : faq.answer,
                "created_at" : str(faq.created_at),
                "source" : "manual",
            })
    except Exception as e:
        print(e)
        return JSONResponse(
            status_code=500,
            content={
                "success" : False,
                "message" : str(e)
            }
        )
    return JSONResponse(
        content = {
            "success" : True,
            "data" : data
        }
    )

@app.get('/get-conversations')
def get_conversations(db: Session = Depends(get_db)):
    try:
        conversations = db.query(ConversationWebsiteAI).order_by(ConversationWebsiteAI.created_at).all()
        data = []
        for conv in conversations:
            data.append({
                "id": str(conv.id),
                "phone_number": conv.phone_number,
                "user_message": conv.user_message,
                "bot_response": conv.bot_response,
                "created_at": str(conv.created_at)
            })
    except Exception as e:
        print(e)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": str(e)
            }
        )
    return JSONResponse(
        content={
            "success": True,
            "data": data
        }
    )


@app.get('/get-analytics')
def get_analytics(db : Session = Depends(get_db)):
    try:
        conversations = db.query(ConversationWebsiteAI).all()
        total_queries_handled = len(conversations)
        average_response_time = round(sum(conv.response_time for conv in conversations) / total_queries_handled , 2) if total_queries_handled > 0 else 0
        escalated_queries = len([conv for conv in conversations if conv.escalated])
        ai_resolution_rate = round((total_queries_handled - escalated_queries) / total_queries_handled * 100 , 2) if total_queries_handled > 0 else 0

        avg_human_time = 120
        time_saved_per_query = avg_human_time - average_response_time
        total_time_saved = round(time_saved_per_query * total_queries_handled / 60 , 2)
        return JSONResponse(
            content={
                "success" : True,
                "data" : {
                    "total_queries_handled" : total_queries_handled,
                    "average_response_time_seconds" : average_response_time,
                    "escalated_queries" : escalated_queries,
                    "ai_resolution_rate_percentage" : ai_resolution_rate,
                    "total_time_saved" : total_time_saved
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content= {
                "success" : False,
                "message" : str(e)
            }
        )


@app.post('/chat')
def chat(query : str , db : Session = Depends(get_db)):
    business_profile = db.query(BusinessProfileWebsiteAI).first()
    vectorstore = None
    if os.path.exists(file_path):
        try:
            vectorstore = FAISS.load_local(
                file_path, 
                embeddings, 
                allow_dangerous_deserialization=True
            )
        except Exception as e:
            print(f"❌ Error loading vector store: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "success" : False,
                    "message" : "Error loading vector store"
                }
            )
    try:
        start_time = time.time()
        response = ai_response.create_rag_qa(vectorstore=vectorstore , query=query , session_id="test_session" , application_name="website_ai")
        end_time = time.time()
        response_time = round(end_time - start_time , 2)
        ai_reply = response['answer']
    except Exception as e:
        ai_reply = "Sorry, I'm having trouble retrieving the information right now. Please try again later."


    new_conversation = ConversationWebsiteAI(
        business_id = business_profile.id,
        user_message = query,
        bot_response = ai_reply,
        response_time = response_time,
        escalated = response['escalated'],
        created_at = datetime.now()
    )

    db.add(new_conversation)
    db.commit()

    return JSONResponse(
        content={
            "success" : True,
            "data" : {
                "response" : ai_reply,
                "response_time_seconds" : response_time,
                "escalated" : response['escalated']
            }
        }
    )

main_app.include_router(app , prefix = '/api/website_ai' , tags = ['website_ai'])