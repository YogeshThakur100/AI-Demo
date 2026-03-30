from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from prompts import clinic_prompt , ca_firm_prompt
from langchain.chains import LLMChain
import utilities
from whatsapp_ai_receptionist.models.business_profile import BusinessProfile , PreLoadedVerticalClinic , PreLoadedVerticalCACS , Manual
import json
from sqlalchemy.orm import Session
from database import SessionLocal
chat_history_store = {}
business_info_cache = {}
faq_cache = {}

def get_preloaded_faqs(db: Session, persona: str):
    """
    Load preloaded FAQs based on the persona.
    Returns FAQ content as a formatted string.
    Uses existing helper methods for data retrieval.
    """
    faq_key = f"faq_{persona}"
    
    if faq_key in faq_cache:
        return faq_cache[faq_key]
    
    try:
        # Use existing helper methods that query the database correctly
        if persona == "clinic":
            faqs_data = get_preloaded_faqs_clinic(db)
        elif persona == "ca_firm":
            faqs_data = get_preloaded_faqs_cacs(db)
        else:
            return ""
        
        # Handle error responses from helper methods
        if isinstance(faqs_data, dict) and "status" in faqs_data:
            print(f"⚠️ Error getting FAQs for {persona}: {faqs_data.get('message', 'Unknown error')}")
            return ""
        
        if not faqs_data:
            return ""
        
        faq_text = f"\n\n=== PRELOADED {persona.upper()} FAQs ===\n"
        for faq in faqs_data:
            question = faq.get("question", "")
            answer = faq.get("answer", "")
            if question and answer:
                faq_text += f"\nQ: {question}\nA: {answer}\n"
        
        faq_cache[faq_key] = faq_text
        return faq_text
    
    except Exception as e:
        print(f"⚠️ Error loading preloaded FAQs: {e}")
        return ""

def get_business_info(db : Session):
    # if company_name not in business_info_cache:
        business_info = db.query(BusinessProfile).first()
        return business_info

def get_preloaded_faqs_clinic(db: Session):
    try:
        faqs = db.query(PreLoadedVerticalClinic).all()
        data = [{"question": faq.question, "answer": faq.answer} for faq in faqs]
        return data
    except Exception as e:
        print(f"❌ Error retrieving preloaded FAQs: {e}")
        return {"status": "error", "message": str(e)}

def get_preloaded_faqs_cacs(db: Session):
    try:
        faqs = db.query(PreLoadedVerticalCACS).all()
        data = [{"question": faq.question, "answer": faq.answer} for faq in faqs]
        return data
    except Exception as e:
        print(f"❌ Error retrieving preloaded FAQs: {e}")
        return {"status": "error", "message": str(e)}
    
def get_manual_faqs(db: Session):
    try:
        faqs = db.query(Manual).all()
        if faqs:
            faq_text = ""
            for faq in faqs:
                faq_text += f"\nQ: {faq.question}\nA: {faq.answer}\n"
            return faq_text
        else:
            return ""
    except Exception as e:
        print(f"❌ Error retrieving manual FAQs: {e}")
        return {"status": "error", "message": str(e)}

def create_rag_qa( query, session_id ,vectorstore=None, company_email = "yogeshthaur3100@gmail.com"):
    print("Vector store --->" , vectorstore)
    if vectorstore:
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})
   
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    db = SessionLocal()
    try:
        business_info = get_business_info(db=db)
        print(f"\n✅ Business info retrieved: {business_info}")
        
        if vectorstore:
            relevant_docs = retriever.get_relevant_documents(query)
            vectorstore_context = "\n\n".join([doc.page_content for doc in relevant_docs])
            print(f"📄 Found {len(relevant_docs)} relevant documents from vectorstore")
            print(f"📝 Vectorstore context length: {len(vectorstore_context)} characters")
        print(f"\n📄 Query: {query}")
        
        persona = business_info.business_type if business_info.business_type else "clinic"
        preloaded_faqs = ""
        if business_info.usePreLoadedVerticals:
            preloaded_faqs = get_preloaded_faqs(db, persona)
        print(f"📚 Loaded preloaded FAQs ({persona}): {len(preloaded_faqs)} characters")

        manual_faqs = get_manual_faqs(db)
        print(f"📚 Loaded manual FAQs: {len(manual_faqs)} characters")
        manual_faqs = manual_faqs
        
    finally:
        db.close()

    chain = LLMChain(llm=llm, prompt=clinic_prompt if persona == "clinic" else ca_firm_prompt)

    if session_id not in chat_history_store:
        chat_history_store[session_id] = []
    
    chat_history_str = "\n".join(
        chat_history_store[session_id]
    ) if chat_history_store[session_id] else ""
    
    if chat_history_str:
        full_question = f"Previous conversation:\n{chat_history_str}\n\nCurrent question: {query}"
    else:
        full_question = query

    try:
        result = chain.invoke({
            "manual_faqs": manual_faqs,
            "vectorstore_context" : vectorstore_context if vectorstore else "No vectorstore context available",
            "preloaded_faqs" : preloaded_faqs,
            "question": full_question,
            "name": business_info.businessName if business_info.businessName else "Not found in database",
            "phone": business_info.phoneNumber if business_info.phoneNumber else "Not found in database",
            "email": business_info.email if business_info.email else "Not found in database",
            "address": business_info.address if business_info.address else "Not found in database",
            "hours": business_info.officeHours if business_info.officeHours else "Not found in database",
            "services": business_info.services if business_info.services else "Not found in database",
            "persona" : business_info.personaSelector if business_info.personaSelector else "Not found in database"
        })
        
        response_text = result.get("text", "")
        print(f"✅ Response gene rated: {response_text[:100]}...")
        
    except Exception as e:
        print(f"❌ Error generating response: {e}")
        response_text = "Sorry, I'm unable to process your request right now. Please try again later."

    escalated = False
    if "We don't have the information currently" in response_text and company_email:
        print("❓ Unknown question asked, sending email to admin...")
        print(f"Company email to notify: {company_email}")
        escalated = True
        # try:
        #     utilities.Utilities_class.send_email_ai_response(company_email, query)
        #     print("✅ Email sent successfully")
        # except Exception as e:
        #     print(f"⚠️ Failed to send email: {e}")
    
    chat_history_store[session_id].append(f"User: {query}")
    chat_history_store[session_id].append(f"Assistant: {response_text}")
    
    if len(chat_history_store[session_id]) > 20:
        chat_history_store[session_id] = chat_history_store[session_id][-20:]
    
    return {
        "answer": response_text,
        "escalated" : escalated
    }


def get_business_profile(vectorstore):
    """
    Extract business information directly from the vectorstore context.
    Retrieves relevant documents and extracts structured business data.
    """
    retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    search_query = "business contact information phone email address hours services"
    retrieved_docs = retriever.get_relevant_documents(search_query)
    
    context_text = "\n\n".join([doc.page_content for doc in retrieved_docs])
    
    print(f"\n📄 Retrieved {len(retrieved_docs)} documents for business profile extraction")
    print(f"📝 Context length: {len(context_text)} characters")

    prompt = ChatPromptTemplate.from_template("""
    You are a business information extraction assistant.
    
    Extract the business information from the provided context.
    
    Context:
    {context}
    
    Based ONLY on the context provided above, extract and return the following business information in JSON format:
    
    Rules:
    - Extract ONLY information that exists in the context
    - If information is not found in the context, use "Not found in context"
    - Do NOT make up, assume, or hallucinate any information
    - Do NOT wrap the JSON in markdown or code blocks
    - Do NOT include ```json or any code markers
    - Return ONLY the JSON object, nothing else
    
    Return exactly this JSON structure:
    {{
        "business_name": "...",
        "business_phone_number": "...",
        "business_email": "...",
        "business_address": "...",
        "business_working_hours": "...",
        "business_services": ["...", "..."]
    }}
    """)

    # Format and invoke the prompt
    formatted_prompt = prompt.format(context=context_text)
    
    try:
        result = llm.invoke(formatted_prompt)
        result_text = result.content if hasattr(result, 'content') else str(result)
        
        print(f"\n✅ Raw extraction result:\n{result_text}")
        
        # Parse the JSON response
        business_info = json.loads(result_text)
        
    except json.JSONDecodeError as e:
        print(f"\n❌ Failed to parse business info JSON: {e}")
        print(f"Raw result was: {result_text}")
        business_info = {
            "business_name": "Not found in context",
            "business_phone_number": "Not found in context",
            "business_email": "Not found in context",
            "business_address": "Not found in context",
            "business_working_hours": "Not found in context",
            "business_services": ["Not found in context"]
        }
    except Exception as e:
        print(f"\n❌ Error extracting business profile: {e}")
        business_info = {}
    
    print(f"\n✅ Parsed business profile: {business_info}")

    return {
        "business_name": business_info.get("business_name", "Not found in context"),
        "business_phone_number": business_info.get("business_phone_number", "Not found in context"),
        "business_email": business_info.get("business_email", "Not found in context"),
        "business_address": business_info.get("business_address", "Not found in context"),
        "business_working_hours": business_info.get("business_working_hours", "Not found in context"),
        "business_services": business_info.get("business_services", ["Not found in context"])
    }
