from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH")
USER_AGENT = os.getenv("USER_AGENT")
OPEN_API_KEY = os.getenv("OPEN_API_KEY")

BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DB_PATH = os.path.join(BASE_DIR, VECTOR_DB_PATH) if VECTOR_DB_PATH else os.path.join(BASE_DIR, "vector_store")

# OPEN_API_KEY

def initialize_injestion(urls: list[str], topic: str): 
    links = fetch_and_parse_links(urls, depth=10)
    vector_store = ingest_web_content(links, topic, chunk_size=1000)
    return vector_store

def ingest_web_content(url: list[str], topic: str, chunk_size: int = 1000): 
    all_texts = []
    
    for link in url:
        loader = WebBaseLoader(link)
        try:
            data = loader.load() # data is a list of Document objects
            
            # Extract a clean title if possible for the metadata
            page_title = link.split('/')[-1].replace('-', ' ').replace('.html', '')

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=500, # Increased overlap helps keep context together
                separators=["\n\n", "\n", " ", ""]
            )
            
            texts = text_splitter.split_documents(data)
            
            # --- CRITICAL FIX: Inject context into the text itself ---
            for doc in texts:
                # We prepend the page context to the chunk text so the embedding 
                # catches the relationship between the name and the content.
                doc.page_content = f"Source: {link} (Subject: {page_title})\nContent: {doc.page_content}"
                doc.metadata["source"] = link
                
            all_texts.extend(texts)
        except Exception as e:
            print(f"Skipping {link}: {e}")

    embeddings = OpenAIEmbeddings(api_key=OPEN_API_KEY)

    # 2. Batch Ingestion to avoid OpenAI Token Limits
    batch_size = 100  # Number of chunks per API call
    vector_store = None

    print(f"Total chunks to embed: {len(all_texts)}")

    for i in range(0, len(all_texts), batch_size):
        batch = all_texts[i : i + batch_size]
        if vector_store is None:
            # Create the store with the first batch
            vector_store = FAISS.from_documents(batch, embeddings)
        else:
            # Add subsequent batches to the existing store
            vector_store.add_documents(batch)
        
        print(f"Indexed {i + len(batch)} / {len(all_texts)} chunks...")

    # 3. Save
    save_path = os.path.join(VECTOR_DB_PATH, topic)
    vector_store.save_local(save_path)
    
    return vector_store


def fetch_and_parse_links(urls: list[str], depth: int) -> list[str]:
    parsed = set()
    links = urls.copy()
    url = urls[0] if urls else ""

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

    print(links)
    return links