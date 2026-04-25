from src.infrastructure.constants import Topic
from pydantic import BaseModel

class IngestionRequest(BaseModel):
    urls: list[str]
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

class SearchRequest(BaseModel):
    query: str
    topic: Topic = Topic.MATH_FACULTY
    k: int = 10
    score_threshold: float = 0.7
    search_type: str = "similarity_score_threshold"  # "similarity", "mmr", "similarity_score_threshold"
    use_reranking: bool = False
    use_multi_query: bool = False
    filters: dict | None = None