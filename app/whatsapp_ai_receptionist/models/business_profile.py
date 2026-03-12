from database import Base
from sqlalchemy import UUID , Column , String , TIMESTAMP , JSON
from sqlalchemy.dialects.postgresql import UUID
import uuid
from typing import List

class BusinessProfile(Base):
    __tablename__ = "business_profiles"
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
    created_at = Column(TIMESTAMP(timezone=True) , default=None)

class PreLoadedVerticalClinic(Base):
    __tablename__ = "preloaded_verticals_clinic"
    id = Column(UUID , primary_key=True , unique=True , index= True , default=uuid.uuid4)
    question_name = Column(String , nullable=False)
    answer = Column(String , nullable=False)
    created_at = Column(TIMESTAMP(timezone=True) , default=None)


class PreLoadedVerticalCACS(Base):
    __tablename__ = "preloaded_verticals_cacs"
    id = Column(UUID , primary_key=True , unique=True , index= True , default=uuid.uuid4)
    question_name = Column(String , nullable=False)
    answer = Column(String , nullable=False)
    created_at = Column(TIMESTAMP(timezone=True) , default=None)