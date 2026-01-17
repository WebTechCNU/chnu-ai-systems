from constants import Topic
from pydantic import BaseModel

class IngestionRequest(BaseModel):
    url: str
    topic: Topic

class QARequest(BaseModel):
    question: str
    context: str
    chat_history: list[str]

class MathFacultyRequest(BaseModel):
    question: str
    context: str
    chat_history: list[str]

class RomanianCultureRequest(BaseModel):
    question: str
    context: str
    chat_history: list[str]

class LocationsRequest(BaseModel):
    location_name: str
    context: str
    chat_history: list[str]

