from pydantic import BaseModel

class ManualFAQS(BaseModel):
    question: str
    answer: str

class businessProfile(BaseModel):
    business_website_url : str = None
    business_type: str = None
    business_name: str = None
    business_phone_number: str = None
    business_email: str = None
    business_address: str = None
    business_working_hours: str = None
    business_services: list[str] = None
    persona_selector: str = None
    manual_faqs: list[ManualFAQS] = None


class PreLoadedVerticalFAQSClinic(BaseModel):
    question: str
    answer: str

class PreLoadedVerticalFAQSCACS(BaseModel):
    question: str
    answer: str

