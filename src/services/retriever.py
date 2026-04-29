from dotenv import load_dotenv
from fastapi import Request
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os
from pathlib import Path
from src.infrastructure.constants import Topic

load_dotenv()

VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH")
BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DB_PATH = os.path.join(BASE_DIR, VECTOR_DB_PATH) if VECTOR_DB_PATH else os.path.join(BASE_DIR, "vector_store")


def load_vector_store(topic: str) -> FAISS | None:
    path = os.path.join(VECTOR_DB_PATH, topic)
    
    # Debug logging for path resolution
    print(f"🔍 Attempting to load vector store from: {path}")
    print(f"   - VECTOR_DB_PATH: {VECTOR_DB_PATH}")
    print(f"   - Topic: {topic}")
    print(f"   - Path exists: {os.path.exists(path)}")
    
    if os.path.exists(path):
        try:
            files = os.listdir(path)
            print(f"   - Contents: {files}")
            if 'index.faiss' not in files:
                print(f"⚠️  WARNING: index.faiss not found in {path}")
        except Exception as e:
            print(f"   - Error listing directory: {e}")
    
    if not os.path.exists(path):
        print(f"❌ Skipping: No vector store found at {path}")
        return None 
    
    try:
        embeddings = OpenAIEmbeddings()
        vector_store = FAISS.load_local(
            path, 
            embeddings,
            allow_dangerous_deserialization=True
        )
        print(f"✅ Successfully loaded vector store for topic: {topic}")
        return vector_store
    except Exception as e:
        print(f"❌ Failed to load vector store for {topic}: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_vector_store(request: Request):
    return request.app.state.vector_store

def get_vector_store_buk(request: Request):
    return request.app.state.vector_store_buk

def get_vector_store_qa(request: Request):
    return request.app.state.vector_store_qa

def get_llm_wrapper(request: Request):
    return request.app.state.llm_wrapper