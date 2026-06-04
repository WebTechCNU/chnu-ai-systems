from src.infrastructure.constants import RomanianIntentType, TestCase, Topic
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class IngestionRequest(BaseModel):
    urls: list[str]
    topic: Topic
    use_structured: bool = True  # Default to structured ingestion
    overwrite: bool = True  # Whether to overwrite existing vector store for the topic
    depth: int = 2  # Depth for structured ingestion (e.g., heading levels to consider)

class QARequest(BaseModel):
    prompt: str
    context: str
    chat_history: list[str]

class QADocument(BaseModel):
    content: str
    title: str | None = None
    source: str | None = None
    metadata: dict[str, Any] | None = None

class QAIngestionRequest(BaseModel):
    website: str | None = None
    documents: list[QADocument]

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


class UserRequest(BaseModel):
    prompt: str

class IntentResult(BaseModel):
    case: TestCase
    extracted_data: Dict[str, Any]
    confidence: float

class PageIssue(BaseModel):
    type: str  # console_error, html_issue, accessibility, performance
    severity: str  # critical, major, minor
    description: str
    location: Optional[str] = None
    suggestion: str

class BugReport(BaseModel):
    title: str
    description: str
    steps_to_reproduce: List[str]
    expected_result: str
    actual_result: str
    severity: str
    additional_context: Optional[Dict] = None

class RomanianIntentResult(BaseModel):
    intent: RomanianIntentType
    confidence: float
    extracted_text: Optional[str] = None
    target_language: Optional[str] = None

class Requirement(BaseModel):
    id: str
    description: str
    category: str
    severity: str