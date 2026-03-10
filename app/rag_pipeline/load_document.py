import json
from langchain.schema import Document
from langchain_community.document_loaders import TextLoader

def load_txt_data(txt_path):
    loader = TextLoader(txt_path , encoding='utf-8')
    txt_docs = loader.load()

    return txt_docs

def loading_website_data(json_path):
    with open(json_path , 'r' , encoding='utf-8') as f:
        data = json.load(f)

    docs = []
     
    for entry in data:
        docs.append(
            Document(
                page_content = entry['content'],
                metadata={"source" : entry['url']}
            )
        )

    return docs