from fastapi import APIRouter , UploadFile , File
from dotenv import load_dotenv , find_dotenv
from main import main_app
from fastapi.responses import JSONResponse
from rag_pipeline import ai_response
from pathlib import Path
import os

current_directory = Path(__file__).parent.parent
documents_directory = os.path.join(current_directory, "documents")

if not os.path.exists(documents_directory):
    os.makedirs(documents_directory)

app = APIRouter()

load_dotenv(find_dotenv())

@app.post("/read_document")
def read_document(persona : str , file: UploadFile = File(...)):
    try:
        file_path = os.path.join(documents_directory , file.filename)
        with open(file_path , "wb") as f:
            f.write(file.file.read())

        response = ai_response.document_reader(file_path , persona)
        return JSONResponse(
            status_code=200,
            content={
                "success" : True,
                "message" : "Document read successfully",
                "data" : {
                    "data" : response
                }
            }
        )
    except Exception as e:
        print(f"Error reading document: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success" : False,
                "message" : f"Error reading document: {str(e)}"
            }
        )

    
@app.post('/read_batch_documents')
def read_batch_documents(persona : str , files: list[UploadFile] = File(...)):
    try:
        responses = []
        for file in files:
            file_path = os.path.join(documents_directory , file.filename)
            with open(file_path , "wb") as f:
                f.write(file.file.read())

            response = ai_response.document_reader(file_path , persona)
            responses.append({
                "file_name" : file.filename,
                "data" : response
            })

        return JSONResponse(
            status_code=200,
            content={
                "success" : True,
                "message" : "Batch documents read successfully",
                "data" : responses
            }
        )
    except Exception as e:
        print(f"Error reading batch documents: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success" : False,
                "message" : f"Error reading batch documents: {str(e)}"
            }
        )



main_app.include_router(app , prefix="/api/document_reader" , tags=["Document Reader API"])