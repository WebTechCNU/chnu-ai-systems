from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from matplotlib.pylab import byte
from pydantic import BaseModel
from models.constants import Topic
from models.models import IngestionRequest, QARequest, MathFacultyRequest, RomanianCultureRequest, LocationsRequest

app = FastAPI()

# CORS:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://webtechcnu.github.io", "http://127.0.0.1:5500", "http://127.0.0.1:5501"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/math-faculty")
async def math_faculty(request: MathFacultyRequest):
    print("Received data:", request)
    return {"status": "success", "data_received": request}

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
async def ingestion_job(ingestionData: IngestionRequest):
    print("Received data:", ingestionData)
    return {"status": "success", "data_received": ingestionData}

@app.post("/api/ingestion-text")
async def ingest_text_data(ingestionData: bytes):
    print("Received data:", ingestionData)
    return {"status": "success", "data_received": ingestionData}