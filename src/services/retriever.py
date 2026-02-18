from dotenv import load_dotenv
from fastapi import Request
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os
from pathlib import Path

load_dotenv()

VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH")
BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DB_PATH = os.path.join(BASE_DIR, VECTOR_DB_PATH) if VECTOR_DB_PATH else os.path.join(BASE_DIR, "vector_store")

def load_vector_store() -> FAISS:
    embeddings = OpenAIEmbeddings()
    vector_store = FAISS.load_local(
        VECTOR_DB_PATH, 
        embeddings,
        allow_dangerous_deserialization=True)
    return vector_store


def get_vector_store(request: Request):
    return request.app.state.vector_store