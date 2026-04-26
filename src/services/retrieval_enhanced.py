"""
Enhanced retrieval strategies for structured data.
Supports metadata filtering and entity-aware search.
"""

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from typing import List, Optional, Dict, Any


def retrieve_with_metadata_boost(
    query: str,
    vector_store: FAISS,
    k: int = 5,
    score_threshold: float = 0.5,
    entity_type: Optional[str] = None
) -> List[Document]:
    """
    Retrieve documents with optional metadata filtering.
    
    Args:
        query: Search query
        vector_store: FAISS vector store
        k: Number of results
        score_threshold: Minimum relevance score
        entity_type: Optional filter by type (e.g., "teacher_profile", "course_info")
    
    Returns:
        List of documents with relevance scores
    """
    
    # Build search kwargs
    search_kwargs = {
        "k": k * 2,  # Get more candidates for filtering
        "score_threshold": score_threshold
    }
    
    # Add metadata filter if specified
    if entity_type:
        search_kwargs["filter"] = {"type": entity_type}
    
    # Retrieve documents
    retriever = vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs=search_kwargs
    )
    
    docs = retriever.get_relevant_documents(query)
    
    # Post-process: boost teacher profile docs if query mentions names
    # This helps ensure complete profiles are returned
    if docs and "викладач" in query.lower() or "professor" in query.lower():
        # Sort to prioritize teacher_profile documents
        docs.sort(key=lambda d: (
            d.metadata.get("type") == "teacher_profile",  # Teacher profiles first
            -len(d.page_content)  # Then by content length (fuller profiles)
        ), reverse=True)
    
    return docs[:k]


def deduplicate_by_teacher(docs: List[Document]) -> List[Document]:
    """
    Remove duplicate teacher profiles, keeping the most complete one.
    
    Args:
        docs: List of retrieved documents
    
    Returns:
        Deduplicated list
    """
    seen_teachers = {}
    result = []
    
    for doc in docs:
        teacher_name = doc.metadata.get("teacher_name")
        doc_type = doc.metadata.get("type")
        
        if doc_type == "teacher_profile" and teacher_name:
            # Keep the longest/most complete profile
            if teacher_name not in seen_teachers:
                seen_teachers[teacher_name] = doc
                result.append(doc)
            elif len(doc.page_content) > len(seen_teachers[teacher_name].page_content):
                # Replace with more complete profile
                result.remove(seen_teachers[teacher_name])
                seen_teachers[teacher_name] = doc
                result.append(doc)
        else:
            # Keep non-teacher documents
            result.append(doc)
    
    return result


def format_structured_context(docs: List[Document]) -> str:
    """
    Format documents into context string, preserving structure.
    Groups related information together.
    
    Args:
        docs: List of documents to format
    
    Returns:
        Formatted context string
    """
    if not docs:
        return "No relevant context found."
    
    # Deduplicate teacher profiles
    docs = deduplicate_by_teacher(docs)
    
    # Group by type
    teacher_profiles = []
    course_info = []
    general_content = []
    
    for doc in docs:
        doc_type = doc.metadata.get("type", "general_content")
        if doc_type == "teacher_profile":
            teacher_profiles.append(doc)
        elif doc_type == "course_info":
            course_info.append(doc)
        else:
            general_content.append(doc)
    
    # Build structured context
    context_parts = []
    
    if teacher_profiles:
        context_parts.append("=== ІНФОРМАЦІЯ ПРО ВИКЛАДАЧІВ ===\n")
        for doc in teacher_profiles:
            context_parts.append(doc.page_content)
            context_parts.append("\n" + "-" * 60 + "\n")
    
    if course_info:
        context_parts.append("\n=== ІНФОРМАЦІЯ ПРО КУРСИ ===\n")
        for doc in course_info:
            context_parts.append(doc.page_content)
            context_parts.append("\n" + "-" * 60 + "\n")
    
    if general_content:
        context_parts.append("\n=== ДОДАТКОВА ІНФОРМАЦІЯ ===\n")
        for doc in general_content:
            context_parts.append(doc.page_content)
            context_parts.append("\n" + "-" * 60 + "\n")
    
    return "\n".join(context_parts)
