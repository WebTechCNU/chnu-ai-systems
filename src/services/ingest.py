from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

def ingest_web_content(url: list[str], chunk_size: int = 1000): 
    all_texts = []

    for link in url:
        loader = WebBaseLoader(link)
        data = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=0,
            separators=["\n\n", "\n", " ", ""]
        )

        texts = text_splitter.split_documents(data)
        all_texts.extend(texts)

    embeddings = OpenAIEmbeddings()
    vector_store = FAISS.from_documents(all_texts, embeddings)

    VECTOR_DB_PATH = "faiss_store"
    vector_store.save_local(VECTOR_DB_PATH)

    return vector_store
