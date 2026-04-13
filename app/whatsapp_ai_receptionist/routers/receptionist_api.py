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
from whatsapp_ai_receptionist.models.business_profile import BusinessProfile , PreLoadedVerticalClinic , PreLoadedVerticalCACS , Manual , Conversation
from whatsapp_ai_receptionist.schemas.business_schemas import businessProfile , PreLoadedVerticalFAQSClinic , PreLoadedVerticalFAQSCACS , ManualFAQS
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

load_dotenv(find_dotenv())

#webhook access token 
VERIFY_TOKEN = os.getenv('ACCESS_TOKEN')

# Define scope
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

#vector store paths
current_directory = Path(__file__).parent.parent
crawling_document_path = os.path.join(current_directory , "Crawl Document")
vector_store_path = os.path.join(current_directory, "Vector Database")
file_path = os.path.join(vector_store_path , "whatsapp_ai_receptionist")
index_file_path = os.path.join(file_path , "index.faiss")

# Load credentials
creds = ServiceAccountCredentials.from_json_keyfile_name(
    os.path.join(Path(__file__).parent, "service-account-key.json"), scope
)

client = gspread.authorize(creds)

# Open Google Sheet
sheet = client.open_by_key("1LMyoMPYHRbs52sxZP8M-nuKPPIZ98UI0VrTanpqoVsU").sheet1


#embeddings for rag
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

@app.get("/status")
def get_status():
    return ("status" , "Receptionist API is running")


@app.post('/crawling-website')
def crawling_website(url: str , db : Session = Depends(get_db)):
    business_profile = db.query(BusinessProfile).first()
    if business_profile:
        return JSONResponse(
            status_code=400,
            content = {
                "success" : False,
                "message" : "Please delete the exisiting business profile to add new one"
            }
        )
    crawling_document_name = os.path.join(crawling_document_path , "whatsapp_ai_receptionist.txt")
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
        new_business_profile = BusinessProfile(
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
def update_business_profile(usePreLoadedVerticals: bool, profile : businessProfile , business_id : str = None, db : Session = Depends(get_db)):
    try:
        business_profile = db.query(BusinessProfile).first()
        if not business_profile:
            new_business_profile = BusinessProfile(
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
                existing_faq = db.query(Manual).filter(faq.question == Manual.question , Manual.business_id == business_profile.id).first()
                if not existing_faq:
                    new_faq = Manual(
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
        faq = db.query(Manual).filter(Manual.id == faq_id).first()
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
        business_profile = db.query(BusinessProfile).first()
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
        business_profile = db.query(BusinessProfile).first()

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

@app.delete('/delete-business-profile')
def delete_business_profile(db : Session = Depends(get_db)):
    try:
        business_profile = db.query(BusinessProfile).first()
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
def add_preload_faqs(faqs: list[PreLoadedVerticalFAQSClinic] , db : Session = Depends(get_db)):
    try:
        for faq in faqs:
            new_faq = PreLoadedVerticalClinic(
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
        faqs = db.query(PreLoadedVerticalClinic).all()
        data = []
        for faq in faqs:
            data.append({
                "id" : faq.id,
                "question" : faq.question,
                "answer" : faq.answer,
                "created_at" : faq.created_at,
                "source" : "template",
            })
        manual_faqs = db.query(Manual).all()
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
def update_preload_faq(faq_id , faq_update: PreLoadedVerticalFAQSClinic, db: Session = Depends(get_db)):
    try:
        faq = db.query(PreLoadedVerticalClinic).filter(PreLoadedVerticalClinic.id == faq_id).first()
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
        faq = db.query(PreLoadedVerticalClinic).filter(PreLoadedVerticalClinic.id == faq_id).first()
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
def add_preload_faqs(faqs: list[PreLoadedVerticalFAQSCACS] , db : Session = Depends(get_db)):
    try:
        for faq in faqs:
            new_faq = PreLoadedVerticalCACS(
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
        faqs = db.query(PreLoadedVerticalCACS).all()
        data = []
        for faq in faqs:
            data.append({
                "id" : faq.id,
                "question" : faq.question,
                "answer" : faq.answer,
                "created_at" : faq.created_at,
                "source" : "template",
            })
        manual_faqs = db.query(Manual).all()
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
def update_preload_faq(faq_id, faq_update: PreLoadedVerticalFAQSCACS, db: Session = Depends(get_db)):
    try:
        faq = db.query(PreLoadedVerticalCACS).filter(PreLoadedVerticalCACS.id == faq_id).first()
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
        faq = db.query(PreLoadedVerticalCACS).filter(PreLoadedVerticalCACS.id == faq_id).first()
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
def add_manual_faqs(faqs: list[ManualFAQS] , business_id : str , db : Session = Depends(get_db)):
    try:
        for faq in faqs:
            new_faq = Manual(
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
        faqs = db.query(Manual).filter(Manual.business_id == business_id).all()
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
        conversations = db.query(Conversation).order_by(Conversation.created_at).all()
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
        conversations = db.query(Conversation).all()
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


@app.get("/whatsapp/webhook")
async def verify_webhook(request: Request):

    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge)

    return PlainTextResponse("Verification failed", status_code=403)


################ Websocket connection for real time communication with whatsapp ################


manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        manager.disconnect(websocket)


main_app.include_router(app , tags=["websocket"])

################ Websocket connection for real time communication with whatsapp ################


@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request , db : Session = Depends(get_db)):
    business_profile = db.query(BusinessProfile).first()
    data = await request.json()
    print("data ----->" , data)

    value = data['entry'][0]['changes'][0]['value']

    if "messages" not in value:   
        return {"status" : "ignored"}
    
    sender = data["entry"][0]["changes"][0]["value"]["messages"][0]["from"]
    if data["entry"][0]["changes"][0]["value"]["messages"][0]['type'] == "interactive" and data["entry"][0]["changes"][0]["value"]["messages"][0]["interactive"]["type"] == "nfm_reply":
        # Extract form data from the flow submission
        nfm_reply = data["entry"][0]["changes"][0]["value"]["messages"][0]["interactive"]["nfm_reply"]
        flow_token = nfm_reply.get("flow_token")
        response_json = nfm_reply.get("response_json")
        
        # Parse the response_json to get form fields
        import json
        try:
            form_data = json.loads(response_json)
            print(f"Form data submitted by {sender}: {form_data}")
            new_data = {
                "name" : form_data.get("name", "N/A"),
                "doctor" : form_data.get("doctor", "N/A"),
                "day" : form_data.get("day", "N/A"),
                "time" : form_data.get("time", "N/A"),
                "phone" : form_data.get("phone", "N/A"),
            }
            df = pd.DataFrame([new_data])
            data = df.values.tolist()
            sheet.append_row(data[0])
            print("Data added to Google Sheet successfully")
        except json.JSONDecodeError as e:
            print(f"Error parsing form data: {e}")

        await manager.broadcast({
            "phone_number" : sender,
            "message" : "Form Filled",
            "timestamp" : datetime.now().isoformat()
        })
        await manager.broadcast({
            "phone_number" : sender,
            "response" : "Appointment is booked successfully. We will contact you soon to confirm the details.",
            "timestamp" : datetime.now().isoformat()
        })
         
        await send_whatsapp.send_whatsapp_message(sender , "Appointment is booked successfully. We will contact you soon to confirm the details.")
        new_conversation = Conversation(
            business_id = business_profile.id,
            phone_number = sender,
            user_message = "Form Filled",
            bot_response = "Appointment is booked successfully. We will contact you soon to confirm the details.",
            response_time = 0,
            escalated = False,
            created_at = datetime.now()
            )
        db.add(new_conversation)
        db.commit()
        return
        
    message = data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
    if "appointment" in message.lower() or "schedule" in message.lower():
        await manager.broadcast({
            "phone_number" : sender,
            "message" : message,
            "timestamp" : datetime.now().isoformat()
        })
        await manager.broadcast({
            "phone_number" : sender,
            "response" : "Please fill the form to book an appointment",
            "timestamp" : datetime.now().isoformat()
        })
        await send_whatsapp.send_flow(sender)
        new_conversation = Conversation(
            business_id = business_profile.id,
            phone_number = sender,
            user_message = message,
            bot_response = "Please fill the form to book an appointment",
            response_time = 0,
            escalated = False,
            created_at = datetime.now()
            )
        db.add(new_conversation)
        db.commit()
        return
    await manager.broadcast({
        "phone_number" : sender,
        "message" : message,
        "timestamp" : datetime.now().isoformat()
    })
    try:
        print("os.path.exists(file_path) --- >" , os.path.exists(file_path))
        vectorstore = None
        if os.path.exists(file_path):
            vectorstore = FAISS.load_local(   
                        file_path, 
                        embeddings, 
                        allow_dangerous_deserialization=True
                    )
        start_time = time.time()
        response = ai_response.create_rag_qa(vectorstore=vectorstore , query=message , session_id=sender , application_name="whatsapp_ai_receptionist")
        end_time = time.time()
        response_time = round(end_time - start_time , 2)
    except Exception as e:
        print(f"❌ Error loading vector store from {e}")
        ai_reply = "Sorry, I'm unable to process your request right now. Please try again later."
        await send_whatsapp.send_whatsapp_message(sender, ai_reply)
        return {"status": "error", "message": str(e)}


    ai_reply = response["answer"]
    new_conversation = Conversation(
        business_id = business_profile.id,
        phone_number = sender,
        user_message = message,
        bot_response = ai_reply,
        response_time = response_time,
        escalated = response['escalated'],
        created_at = datetime.now()
    )
    db.add(new_conversation)
    db.commit()

    await send_whatsapp.send_whatsapp_message(sender , ai_reply)
    await manager.broadcast({
        "phone_number" : sender,
        "response" : ai_reply,
        "timestamp" : datetime.now().isoformat()
    })



main_app.include_router(app , prefix="/api/receptionist" , tags=["Receptionist API"])