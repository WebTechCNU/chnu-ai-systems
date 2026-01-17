from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

VECTOR_DB_PATH = "faiss_store"

def load_vector_store() -> FAISS:
    embeddings = OpenAIEmbeddings()
    vector_store = FAISS.load_local(VECTOR_DB_PATH, embeddings)
    return vector_store