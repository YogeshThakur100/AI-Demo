import os
import time
import gc
import shutil
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS


def build_vectorstore(user_email, website_docs, pdf_docs):
    """Build a fresh vectorstore for a user, completely replacing old one"""
    
    # 1. FIRST delete any existing files on disk
    current_directory = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.abspath(os.path.join(current_directory, "Vector Store"))
    save_path = os.path.abspath(os.path.join(folder_path, user_email))
    
    # Delete old vectorstore from disk FIRST
    if os.path.exists(save_path):
        try:
            shutil.rmtree(save_path, ignore_errors=True)
            # Wait a bit to ensure files are released
            
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ Error deleting old vectorstore for {user_email}: {e}")
    
    # 2. Clear memory
    gc.collect()
    
    # 3. Prepare documents
    if pdf_docs is not None:
        all_docs = website_docs + pdf_docs
    else:
        all_docs = website_docs
    
    if not all_docs:
        raise ValueError("No documents provided")
    
    # 4. Split documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " "]
    )
    
    split_docs = text_splitter.split_documents(all_docs)

    #######################################Cost Estimation########################
    # total_embedding_tokens = 0

    # for doc in split_docs:
    #     total_embedding_tokens += estimate_cost.tokens_for_embedding(doc.page_content)

    # print(f"Estimated tokens for embedding all chunks: {total_embedding_tokens} tokens")

    # total_embedding_cost = estimate_cost.estimate_cost_for_embedding(total_embedding_tokens)
    # print(f"Estimated cost for embedding all chunks: ${total_embedding_cost:.6f}")  

    #######################################Cost Estimation########################
    
    if len(split_docs) == 0:
        raise ValueError("No text content extracted from documents")
    
    # 5. Create fresh embeddings and vectorstore
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # Create a completely new FAISS index
        vectorstore = FAISS.from_documents(split_docs, embeddings)
        
    except Exception as e:
        raise 
    
    # 6. Ensure directory exists
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # 7. Save to disk with verification
    try:
        vectorstore.save_local(save_path)
        
        # Verify the save
        if os.path.exists(os.path.join(save_path, "index.faiss")):
            print(f"✅ FAISS index saved successfully at {save_path}")
        else:
            raise Exception("FAISS index file not saved properly")
            
    except Exception as e:
        raise 
    
    # 8. Return the fresh vectorstore
    return {
        "vectorstore": vectorstore,
        # "embedding_tokens": total_embedding_tokens,
        # "embedding_cost": total_embedding_cost
    }