from pydantic import BaseModel
from typing import Optional

class ManualFAQS_Website_ai(BaseModel):
    question: str
    answer: str

class businessProfile_Website_ai(BaseModel):
    business_website_url : str = None
    business_type: str = None
    business_name: str = None
    business_phone_number: str = None
    business_email: str = None
    business_address: str = None
    business_working_hours: str = None
    business_services: list[str] = None
    persona_selector: str = None
    manual_faqs: list[ManualFAQS_Website_ai] = None


class PreLoadedVerticalFAQSClinic_Website_ai(BaseModel):
    question: str
    answer: str

class PreLoadedVerticalFAQSCACS_Website_ai(BaseModel):
    question: str
    answer: str

class GradientItem(BaseModel):
    color : list[str] | None = None
    angle : int | None = None

class GradientRequest(BaseModel):
    header_gradient : Optional[GradientItem] = None
    user_gradient : Optional[GradientItem] = None
    chatbot_name : Optional[str] = None
    chatbot_welcome_message : Optional[str] = None
    
class WebsiteChatbotUser(BaseModel):
    user_name : str
    user_email : Optional[str] = None
    user_mobile_number : Optional[str] = None
