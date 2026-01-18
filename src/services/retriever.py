from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os

VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH")

def load_vector_store() -> FAISS:
    embeddings = OpenAIEmbeddings()
    vector_store = FAISS.load_local(VECTOR_DB_PATH, embeddings)
    return vector_store