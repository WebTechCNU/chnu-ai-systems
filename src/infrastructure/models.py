from infrastructure.constants import Topic
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
    # context: str
    chat_history: list[str]
    user_status: str

class RomanianCultureRequest(BaseModel):
    question: str
    context: str
    chat_history: list[str]

class LocationsRequest(BaseModel):
    context: str
    latitude: float
    longitude: float
    purpose: str
    radius: int
    chat_history: list[str]


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "user"  # "admin" | "user"

class LoginRequest(BaseModel):
    username: str
    password: str