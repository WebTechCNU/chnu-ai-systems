import os
from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain_core.documents import Document
from src.infrastructure.models import IngestionRequest, LoginRequest, QARequest, QADocument, QAIngestionRequest, MathFacultyRequest, RegisterRequest, RomanianCultureRequest, LocationsRequest, SearchRequest
from src.services import security
from src.services.auth import get_db, register_user, login_user, get_current_user, require_role
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from src.domain.database import Base, engine
from src.domain.entities import User
from src.services.ingest import initialize_injestion
from src.services.ingest_structured import initialize_structured_ingestion
from src.services.retriever import get_llm_wrapper, get_vector_store, load_vector_store, get_vector_store_buk, get_vector_store_qa, VECTOR_DB_PATH
from src.services.rag_chain import query_math_faculty, query_qa, query_romanian_culture
from src.services.location_service import get_recommendation_from_ai
from src.infrastructure.constants import TestCase, Topic
from src.services.validation import validate
from src.services.search import search_documents, search_with_reranking, multi_query_search
from src.services.qa_helper import LLMClient, IntentClassifier, WebTester, APITester, LogAnalyzer
import json
import io
import importlib
from src.services.retrieval_enhanced import retrieve_with_metadata_boost, format_structured_context
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("Loading vector stores...")
    print("=" * 60)

    vector_stores = reload_vector_stores(app)

    # Validate and report status
    print("\n" + "=" * 60)
    print("Vector Store Loading Status:")
    print("=" * 60)
    all_loaded = True
    for name, store in vector_stores.items():
        if store is None:
            print(f"❌ FAILED: {name} vector store did not load!")
            all_loaded = False
        else:
            print(f"✅ SUCCESS: {name} vector store loaded")

    if not all_loaded:
        print("\n⚠️  WARNING: Some vector stores failed to load.")
        print("   Check VECTOR_DB_PATH in .env and ensure FAISS indices exist.")
    else:
        print("\n✅ All vector stores loaded successfully!")
    print("=" * 60 + "\n")

    yield
    print("Shutting down...")


def reload_vector_stores(app: FastAPI):
    vector_stores = {
        "math_faculty": load_vector_store(Topic.MATH_FACULTY.value),
        "romanian_culture": load_vector_store(Topic.ROMANIAN_CULTURE.value),
        "qa_helper": load_vector_store(Topic.QA_HELPER.value)
    }

    app.state.vector_store = vector_stores["math_faculty"]
    app.state.vector_store_buk = vector_stores["romanian_culture"]
    app.state.vector_store_qa = vector_stores["qa_helper"]

    OPEN_API_KEY = os.getenv("OPEN_API_KEY")
    app.state.llm_wrapper = LLMClient(OPEN_API_KEY)

    return vector_stores


def inject_documents_into_qa_store(app: FastAPI, documents: list[Document], topic: str = Topic.QA_HELPER.value):
    embeddings = OpenAIEmbeddings()
    vector_store = app.state.vector_store_qa

    if vector_store is None:
        vector_store = FAISS.from_documents(documents, embeddings)
    else:
        vector_store.add_documents(documents)

    app.state.vector_store_qa = vector_store

    save_path = os.path.join(VECTOR_DB_PATH, topic)
    os.makedirs(save_path, exist_ok=True)
    vector_store.save_local(save_path)
    return vector_store


def parse_uploaded_document(file: UploadFile) -> str:
    filename = file.filename or "uploaded_document"
    extension = os.path.splitext(filename)[1].lower()

    if extension == ".txt":
        raw = file.file.read()
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="replace")

    if extension == ".pdf":
        raw = file.file.read()
        try:
            PdfReader = importlib.import_module("PyPDF2").PdfReader
        except Exception as e:
            raise ValueError("PDF parsing requires PyPDF2. Install it with `pip install PyPDF2`.") from e

        reader = PdfReader(io.BytesIO(raw))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages).strip()

    raise ValueError(f"Unsupported file type: {extension}. Only .pdf and .txt are supported.")


app = FastAPI(lifespan=lifespan)

# CORS:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://webtechcnu.github.io", "http://127.0.0.1:5500", "http://127.0.0.1:5501", "http://127.0.0.1:3000", "https://maxvonlancaster.github.io"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

@app.post("/api/math-faculty")
async def math_faculty(request: MathFacultyRequest, vector_store = Depends(get_vector_store)):
    # Check if vector store is available
    if vector_store is None:
        return {
            "status": "failed", 
            "error": "Vector store not available. Please check server logs."
        }
    
    validation = validate(request.question)
    if not validation["meaningful"]:
        return {"status": "failed", "reasons": validation["reasons"]}
    result = query_math_faculty(request.question, request.chat_history, vector_store)
    return {"status": "success", "answer": result}

@app.post("/api/locations")
async def locations(request: LocationsRequest):
    result = get_recommendation_from_ai(
        user_lat=request.latitude,
        user_lon=request.longitude,
        purpose=request.purpose,
        radius=request.radius
    )
    return {"status": "success", "answer": result}

# @app.post("/api/qa")
# async def qa(request: QARequest, vector_store = Depends(get_vector_store_qa)):
#     # Check if vector store is available
#     if vector_store is None:
#         return {
#             "status": "failed", 
#             "error": "QA vector store not available. Please check server logs."
#         }
    
#     result = query_qa(request.question, request.chat_history, vector_store)
#     return {"status": "success", "answer": result}

@app.post("/api/romanian-culture")
async def romanian_culture(request: RomanianCultureRequest, vector_store = Depends(get_vector_store_buk)):
    # Check if vector store is available
    if vector_store is None:
        return {
            "status": "failed", 
            "error": "Romanian culture vector store not available. Please check server logs."
        }
    validation = validate(request.question)
    if not validation["meaningful"]:
        return {"status": "failed", "reasons": validation["reasons"]}
    
    result = query_romanian_culture(request.question, request.chat_history, vector_store)
    return {"status": "success", "answer": result}


@app.post("/api/search")
async def search(request: Request, search_request: SearchRequest):
    """
    Standalone search endpoint that retrieves documents without LLM generation.
    Supports multiple search strategies and reranking.
    """
    # Use cached vector stores from app.state instead of reloading
    if search_request.topic == Topic.MATH_FACULTY:
        vector_store = request.app.state.vector_store
    elif search_request.topic == Topic.ROMANIAN_CULTURE:
        vector_store = request.app.state.vector_store_buk
    elif search_request.topic == Topic.QA_HELPER:
        vector_store = request.app.state.vector_store_qa
    else:
        return {"status": "failed", "error": "Invalid topic"}
    
    if vector_store is None:
        return {"status": "failed", "error": f"Vector store not found for topic: {search_request.topic.value}"}
    
    try:
        # Choose search strategy
        if search_request.use_multi_query:
            results = multi_query_search(
                query=search_request.query,
                vector_store=vector_store,
                k=search_request.k,
                score_threshold=search_request.score_threshold
            )
        elif search_request.use_reranking:
            results = search_with_reranking(
                query=search_request.query,
                vector_store=vector_store,
                k=search_request.k,
                initial_k=search_request.k * 5,
                score_threshold=search_request.score_threshold
            )
        else:
            results = search_documents(
                query=search_request.query,
                vector_store=vector_store,
                k=search_request.k,
                score_threshold=search_request.score_threshold,
                filter_metadata=search_request.filters,
                search_type=search_request.search_type
            )
        
        return {
            "status": "success", 
            "results": results, 
            "count": len(results),
            "query": search_request.query,
            "topic": search_request.topic.value
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


@app.post("/api/ingestion-job")
async def ingestion_job(
        ingestionData: IngestionRequest, admin: User = Depends(require_role("admin"))):
    print("Received data:", ingestionData)
    
    # Use structured ingestion by default for better entity relationship preservation
    use_structured = getattr(ingestionData, 'use_structured', True)

    if (ingestionData.topic == Topic.ROMANIAN_CULTURE) or not use_structured:
        print("Using LEGACY ingestion (basic chunking)")
        initialize_injestion(ingestionData.urls, ingestionData.topic.value,
                            overwrite=ingestionData.overwrite,
                            depth=ingestionData.depth)
    
    else:
        print("Using STRUCTURED ingestion (preserves teacher profiles, courses)")
        initialize_structured_ingestion(ingestionData.urls, ingestionData.topic.value, 
                                        overwrite=ingestionData.overwrite,
                                        depth=ingestionData.depth)
    
    return {"status": "success", "data_received": ingestionData, "method": "structured" if use_structured else "legacy"}

@app.post("/api/reload-vectorstores")
async def reload_vectorstores_endpoint(admin: User = Depends(require_role("admin"))):
    vector_stores = reload_vector_stores(app)
    status = {
        name: ("success" if store is not None else "failed")
        for name, store in vector_stores.items()
    }
    overall = "success" if all(store is not None for store in vector_stores.values()) else "partial"
    return {
        "status": overall,
        "vectorstores": status
    }

@app.post("/api/ingestion-text")
async def ingest_text_data(ingestionData: bytes, admin: User = Depends(require_role("admin"))):
    print("Received data:", ingestionData)
    return {"status": "success", "data_received": ingestionData}


@app.post("/api/qa/documents")
async def ingest_qa_documents(request_data: QAIngestionRequest, admin: User = Depends(require_role("admin"))):
    """Ingest website-related documents into the QA vector store.

    Example request body:
    {
        "website": "https://example.com",
        "documents": [
            {
                "title": "Homepage overview",
                "content": "The homepage has a signup link and a featured product section.",
                "source": "https://example.com",
                "metadata": {"section": "homepage"}
            },
            {
                "title": "API documentation",
                "content": "The /api/login endpoint expects JSON with username and password.",
                "source": "https://example.com/docs/api",
                "metadata": {"section": "api"}
            }
        ]
    }
    """
    if not request_data.documents:
        return JSONResponse(status_code=400, content={"error": "No documents provided."})

    document_objects = []
    for doc in request_data.documents:
        content = doc.content
        if doc.title:
            content = f"{doc.title}\n\n{content}"

        metadata = doc.metadata.copy() if doc.metadata else {}
        if doc.source:
            metadata["source"] = doc.source
        if request_data.website:
            metadata["website"] = request_data.website

        document_objects.append(Document(page_content=content, metadata=metadata))

    inject_documents_into_qa_store(app, document_objects)
    return {
        "status": "success",
        "added_documents": len(document_objects),
        "topic": Topic.QA_HELPER.value
    }


@app.post("/api/qa/documents/upload")
async def upload_qa_documents(
    files: list[UploadFile] = File(...),
    website: str | None = Form(None),
    source: str | None = Form(None),
    metadata: str | None = Form(None),
    admin: User = Depends(require_role("admin"))
):
    if not files:
        return JSONResponse(status_code=400, content={"error": "At least one file must be uploaded."})

    parsed_metadata = {}
    if metadata:
        try:
            parsed_metadata = json.loads(metadata)
        except Exception:
            return JSONResponse(status_code=400, content={"error": "Metadata must be valid JSON."})

    document_objects = []
    for upload in files:
        try:
            text = parse_uploaded_document(upload)
        except ValueError as ve:
            return JSONResponse(status_code=400, content={"error": str(ve)})
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": f"Failed to parse {upload.filename}: {e}"})

        if not text.strip():
            continue

        doc_metadata = parsed_metadata.copy()
        if source:
            doc_metadata["source"] = source
        if website:
            doc_metadata["website"] = website
        doc_metadata["filename"] = upload.filename

        document_objects.append(Document(page_content=text, metadata=doc_metadata))

    if not document_objects:
        return JSONResponse(status_code=400, content={"error": "No usable text was extracted from the uploaded files."})

    inject_documents_into_qa_store(app, document_objects)
    return {
        "status": "success",
        "added_documents": len(document_objects),
        "uploaded_files": [upload.filename for upload in files],
        "topic": Topic.QA_HELPER.value
    }


@app.post("/api/qa")
async def qa(request: QARequest, llm_client = Depends(get_llm_wrapper), vector_store = Depends(get_vector_store_qa)):
    """Handle QA requests: analyze content (web/api/logs) and augment with RAG from QA vectorstore.

    Returns both the analysis (bug reports) and RAG-provided context/answer when available.
    """
    validation = validate(request.prompt)
    if not validation["meaningful"]:
        return {"status": "failed", "reasons": validation["reasons"]}

    related_context = None
    if vector_store is not None:
        try:
            # Use the URL or prompt to find related QA documents
            query = request.prompt
            intent_classifier = IntentClassifier(llm_client)
            intent = await intent_classifier.classify(request.prompt)
            if intent.case in (TestCase.WEB_PAGE, TestCase.API_ENDPOINT):
                query = intent.extracted_data.get("url", request.prompt)

            related_docs = retrieve_with_metadata_boost(query, vector_store, k=5, score_threshold=0.3)
            related_context = format_structured_context(related_docs)
        except Exception as doc_exc:
            related_context = f"Related documents could not be retrieved: {doc_exc}"
    else:
        intent_classifier = IntentClassifier(llm_client)
        intent = await intent_classifier.classify(request.prompt)

    try:
        # Step 2: Execute the appropriate testing service
        if intent.case == TestCase.WEB_PAGE:
            url = intent.extracted_data.get("url")
            if not url:
                return JSONResponse(
                    status_code=400,
                    content={"error": "No URL found for web page testing"}
                )

            web_tester = WebTester(llm_client)
            bug_report = await web_tester.test_page(url, related_context=related_context)

        elif intent.case == TestCase.API_ENDPOINT:
            url = intent.extracted_data.get("url")
            method = intent.extracted_data.get("method", "GET")

            if not url:
                return JSONResponse(
                    status_code=400,
                    content={"error": "No URL found for API testing"}
                )

            api_tester = APITester(llm_client)
            bug_report = await api_tester.test_endpoint(url, method, related_context=related_context)

        elif intent.case == TestCase.LOGS:
            log_content = intent.extracted_data.get("logs", request.prompt)
            log_analyzer = LogAnalyzer(llm_client)
            bug_report = await log_analyzer.analyze_logs(log_content)

        else:
            # Unknown intent - let LLM provide a helpful response.
            # Include any retrieved QA vector store context to guide the answer.
            prompt = request.prompt
            if related_context:
                prompt = f"{request.prompt}\n\nRelevant QA documents:\n{related_context}"

            response = await llm_client.generate(
                prompt,
                system_prompt="You are a QA testing assistant. Help the user with testing questions."
            )
            return {
                "response": response,
                "case": "general_help",
                "related_context": related_context
            }

        # Step 3: RAG augmentation - query QA vector store if available
        # rag_answer = None
        # try:
        #     if vector_store is None:
        #         rag_answer = {"status": "skipped", "reason": "QA vector store not available"}
        #     else:
        #         try:
        #             rag_result = query_qa(request.prompt, request.chat_history, vector_store)
        #             rag_answer = {"status": "success", "answer": rag_result}
        #         except Exception as inner_e:
        #             docs = retrieve_with_metadata_boost(request.prompt, vector_store, k=5, score_threshold=0.5)
        #             formatted = format_structured_context(docs)
        #             rag_answer = {"status": "partial", "error": str(inner_e), "context": formatted}
        # except Exception as e:
        #     rag_answer = {"status": "failed", "error": str(e)}

        serialized_reports = []
        if isinstance(bug_report, list):
            serialized_reports = [report.dict() for report in bug_report]
        elif bug_report is not None:
            serialized_reports = [bug_report.dict()]

        summary_text = None
        if isinstance(bug_report, list) and bug_report:
            summary_text = f"🔍 {bug_report[0].title}\n\n{bug_report[0].description[:500]}..."
        elif hasattr(bug_report, "title"):
            summary_text = f"🔍 {bug_report.title}\n\n{bug_report.description[:500]}..."

        return {
            "case": intent.case,
            "confidence": intent.confidence,
            "bug_reports": serialized_reports,
            "related_context": related_context,
            "summary": summary_text
            # "rag": rag_answer
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    data = login_user(request, db)
    return data

@app.post("/api/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    data = register_user(request, db)
    return data




