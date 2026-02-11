from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH")
USER_AGENT = os.getenv("USER_AGENT")
OPEN_API_KEY = os.getenv("OPEN_API_KEY")

# OPEN_API_KEY

def initialize_injestion(url: str): 
    links = fetch_and_parse_links(url, depth=2)
    vector_store = ingest_web_content(links, chunk_size=1000)
    return vector_store

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

    embeddings = OpenAIEmbeddings(
        api_key=OPEN_API_KEY
    )
    vector_store = FAISS.from_documents(all_texts, embeddings)

    vector_store.save_local(VECTOR_DB_PATH)

    return vector_store


def fetch_and_parse_links(url: str, depth: int) -> list[str]:
    parsed = set()
    links = [url]

    for i in range(depth):
        new_links = []
        for link in links:
            if link not in parsed:
                try:
                    response = requests.get(link, headers={"User-Agent": USER_AGENT})
                    soup = BeautifulSoup(response.content, "html.parser")
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        if href.startswith("/"):
                            href = url + href[1:]
                        if href.startswith(url) and href not in parsed and 'pdf' not in href.lower() and 'jpg' not in href.lower() and 'png' not in href.lower() and 'jpeg' not in href.lower() and 'docx' not in href.lower() and 'doc' not in href.lower() and 'xls' not in href.lower() and 'xlsx' not in href.lower() and 'pptx' not in href.lower() and 'ppt' not in href.lower() and 'email-protection' not in href.lower() and 'mailto' not in href.lower() and 'tel' not in href.lower() and 'javascript' not in href.lower() and 'webp' not in href.lower() and 'svg' not in href.lower() and 'mp4' not in href.lower() and 'avi' not in href.lower() and 'mov' not in href.lower() and 'mkv' not in href.lower() and 'flv' not in href.lower() and 'wmv' not in href.lower() and 'mp3' not in href.lower() and 'wav' not in href.lower():
                            new_links.append(href)
                except Exception as e:
                    print(f"Error fetching {link}: {e}")
                parsed.add(link)
        links.extend(new_links)
        links = list(set(links))  # remove duplicates
        i += 1

    return links