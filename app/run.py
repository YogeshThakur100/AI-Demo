import uvicorn
# from main import main_app
from whatsapp_ai_receptionist.routers import receptionist_api
from database import Base , engine

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    uvicorn.run("main:main_app" , host='0.0.0.0' , port=8000 , reload=True)