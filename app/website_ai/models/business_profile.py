from database import Base
from sqlalchemy import UUID , Column , String , TIMESTAMP , JSON , ForeignKey , Float , Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from typing import List

class BusinessProfileWebsiteAI(Base):
    __tablename__ = "business_profiles_website_ai"
    id = Column(UUID , primary_key=True , unique=True , index= True , default=uuid.uuid4)
    business_type = Column(String , nullable=True)
    websiteLink = Column(String, nullable=True)
    urlsCrawled = Column(JSON, nullable=True)
    businessName = Column(String, nullable=True)
    phoneNumber = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)
    officeHours = Column(String, nullable=True)
    services = Column(JSON, nullable=True)
    personaSelector = Column(String, nullable=True) 
    usePreLoadedVerticals = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True) , default=None)

class PreLoadedVerticalClinicWebsiteAI(Base):
    __tablename__ = "preloaded_verticals_clinic_website_ai"
    id = Column(UUID , primary_key=True , unique=True , index= True , default=uuid.uuid4)
    question = Column(String , nullable=False)
    answer = Column(String , nullable=False)
    created_at = Column(TIMESTAMP(timezone=True) , default=None)


class PreLoadedVerticalCACSWebsiteAI(Base):
    __tablename__ = "preloaded_verticals_cacs_website_ai"
    id = Column(UUID , primary_key=True , unique=True , index= True , default=uuid.uuid4)
    question = Column(String , nullable=False)
    answer = Column(String , nullable=False)
    created_at = Column(TIMESTAMP(timezone=True) , default=None)

class ManualWebsiteAI(Base):
    __tablename__ = "manual_faqs_website_ai"
    id = Column(UUID , primary_key=True , unique=True , index= True , default = uuid.uuid4)
    business_id = Column(UUID, ForeignKey("business_profiles_website_ai.id" , ondelete="CASCADE") ,nullable=False)
    question = Column(String , nullable=False)
    answer = Column(String , nullable=False)
    created_at = Column(TIMESTAMP(timezone=True) , default=None)

class ConversationWebsiteAI(Base):
    __tablename__ = "conversations_website_ai"
    id = Column(UUID , primary_key=True , unique=True , index= True , default = uuid.uuid4)
    business_id = Column(UUID, ForeignKey("business_profiles_website_ai.id" , ondelete="CASCADE"))
    user_message = Column(String , nullable=False)
    bot_response = Column(String , nullable=False)
    response_time = Column(Float , nullable=True)
    escalated = Column(Boolean , nullable=True)
    created_at = Column(TIMESTAMP(timezone=True) , default=None)

