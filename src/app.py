from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from constants import Topic

app = FastAPI()

# CORS:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://webtechcnu.github.io", "http://127.0.0.1:5500", "http://127.0.0.1:5501"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Ingestion(BaseModel):
    url: str
    topic: Topic

@app.post("/api/math-faculty")
async def math_faculty(data: dict):
    print("Received data:", data)
    return {"status": "success", "data_received": data}

@app.post("/api/locations")
async def locations(data: dict):
    print("Received data:", data)
    return {"status": "success", "data_received": data}

@app.post("/api/qa")
async def qa(data: dict):
    print("Received data:", data)
    return {"status": "success", "data_received": data}

@app.post("/api/romanian-culture")
async def romanian_culture(data: dict):
    print("Received data:", data)
    return {"status": "success", "data_received": data}


@app.post("/api/ingestion-job")
async def ingestion_job(ingestionData: Ingestion):
    print("Received data:", ingestionData)
    return {"status": "success", "data_received": ingestionData}