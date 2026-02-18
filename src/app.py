from fastapi import FastAPI, Depends
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from infrastructure.models import IngestionRequest, LoginRequest, QARequest, MathFacultyRequest, RegisterRequest, RomanianCultureRequest, LocationsRequest
from services import security
from services.auth import get_db, register_user, login_user, get_current_user, require_role
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from domain.database import Base, engine
from domain.entities import User
from services.ingest import initialize_injestion
from services.retriever import get_vector_store, load_vector_store
from fastapi import Request
from services.rag_chain import query

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading vector store...")
    app.state.vector_store = load_vector_store()
    print("Vector store loaded.")
    yield
    print("Shutting down...")


app = FastAPI(lifespan=lifespan)

# CORS:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://webtechcnu.github.io", "http://127.0.0.1:5500", "http://127.0.0.1:5501"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

@app.post("/api/math-faculty")
async def math_faculty(request: MathFacultyRequest, vector_store = Depends(get_vector_store)):
    result = query(request.question, request.chat_history, vector_store)
    return {"status": "success", "answer": result}

@app.post("/api/locations")
async def locations(request: LocationsRequest):
    print("Received data:", request)
    return {"status": "success", "data_received": request}

@app.post("/api/qa")
async def qa(request: QARequest):
    print("Received data:", request)
    return {"status": "success", "data_received": request}

@app.post("/api/romanian-culture")
async def romanian_culture(request: RomanianCultureRequest):
    print("Received data:", request)
    return {"status": "success", "data_received": request}


@app.post("/api/ingestion-job")
async def ingestion_job(
        ingestionData: IngestionRequest, admin: User = Depends(require_role("admin"))):
    print("Received data:", ingestionData)
    initialize_injestion(ingestionData.url)
    return {"status": "success", "data_received": ingestionData}

@app.post("/api/ingestion-text")
async def ingest_text_data(ingestionData: bytes, admin: User = Depends(require_role("admin"))):
    print("Received data:", ingestionData)
    return {"status": "success", "data_received": ingestionData}


@app.post("/api/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    data = login_user(request, db)
    return data

@app.post("/api/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    data = register_user(request, db)
    return data




