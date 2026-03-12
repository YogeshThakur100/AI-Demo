import os
import time
import gc
import shutil
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


def build_vectorstore(save_path,user_email=None, website_docs=None, pdf_docs=None):
    if os.path.exists(save_path):
        try:
            shutil.rmtree(save_path, ignore_errors=True)
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ Error deleting old vectorstore for {user_email}: {e}")
    
    gc.collect()
    
    if pdf_docs is not None:
        all_docs = website_docs + pdf_docs
    else:
        all_docs = website_docs
    
    if not all_docs:
        raise ValueError("No documents provided")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " "]
    )
    
    split_docs = text_splitter.split_documents(all_docs)
    
    if len(split_docs) == 0:
        raise ValueError("No text content extracted from documents")
    
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        vectorstore = FAISS.from_documents(split_docs, embeddings)
        
    except Exception as e:
        raise 
    try:
        vectorstore.save_local(save_path)
        
        if os.path.exists(os.path.join(save_path, "index.faiss")):
            print(f"✅ FAISS index saved successfully at {save_path}")
        else:
            raise Exception("FAISS index file not saved properly")
            
    except Exception as e:
        raise 
    
    return {
        "vectorstore": vectorstore,
    }