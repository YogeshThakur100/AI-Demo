from pydantic import BaseModel

class businessProfile(BaseModel):
    business_type: str
    business_name: str
    business_phone_number: str
    business_email: str
    business_address: str
    business_working_hours: str
    business_services: list[str]
    office_hours: str
    persona_selector: str


class PreLoadedVerticalFAQSClinic(BaseModel):
    question_name: str
    answer: str

class PreLoadedVerticalFAQSCACS(BaseModel):
    question_name: str
    answer: str