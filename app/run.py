import uvicorn
# from main import main_app
from whatsapp_ai_receptionist import receptionist_api

if __name__ == "__main__":
    uvicorn.run("main:main_app" , host='0.0.0.0' , port=8000 , reload=True)