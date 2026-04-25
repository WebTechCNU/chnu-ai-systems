from langchain_core.documents import Document
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
import os


def search_documents(
    query: str,
    vector_store,
    k: int = 10,
    score_threshold: float = 0.7,
    filter_metadata: Optional[Dict[str, Any]] = None,
    search_type: str = "similarity"
) -> List[Dict[str, Any]]:
    """
    Standalone search without LLM generation.
    
    Args:
        query: The search query
        vector_store: FAISS vector store instance
        k: Number of results to return
        score_threshold: Minimum relevance score (0-1)
        filter_metadata: Optional metadata filters
        search_type: 'similarity', 'mmr', or 'similarity_score_threshold'
    
    Returns:
        List of document dictionaries with content, metadata, and scores
    """
    
    if search_type == "similarity_score_threshold":
        search_kwargs = {
            "k": k,
            "score_threshold": score_threshold
        }
        
        if filter_metadata:
            search_kwargs["filter"] = filter_metadata
        
        # Get documents with scores
        docs_and_scores = vector_store.similarity_search_with_relevance_scores(
            query, 
            **search_kwargs
        )
        
        # Format results
        results = []
        for doc, score in docs_and_scores:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "relevance_score": float(score)
            })
        
        return results
    
    elif search_type == "mmr":
        # Maximum Marginal Relevance for diversity
        search_kwargs = {
            "k": k,
            "fetch_k": k * 3  # Fetch more candidates for diversity
        }
        
        if filter_metadata:
            search_kwargs["filter"] = filter_metadata
            
        docs = vector_store.max_marginal_relevance_search(query, **search_kwargs)
        
        results = []
        for doc in docs:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "relevance_score": None  # MMR doesn't return scores
            })
        
        return results
    
    else:  # similarity
        search_kwargs = {"k": k}
        
        if filter_metadata:
            search_kwargs["filter"] = filter_metadata
        
        # Use similarity_search_with_relevance_scores instead of similarity_search_with_score
        # This returns properly normalized scores (0-1) instead of raw distances
        try:
            docs_and_scores = vector_store.similarity_search_with_relevance_scores(query, **search_kwargs)
            
            results = []
            for doc, score in docs_and_scores:
                if score >= score_threshold:
                    results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "relevance_score": float(score)
                    })
        except AttributeError:
            # Fallback: If similarity_search_with_relevance_scores not available, 
            # use similarity_search_with_score with better normalization
            import numpy as np
            docs_and_scores = vector_store.similarity_search_with_score(query, **search_kwargs)
            
            results = []
            for doc, distance in docs_and_scores:
                # Better normalization: exponential decay for L2 distance
                # This handles unbounded distances better than 1/(1+score)
                similarity = np.exp(-distance / 10.0)  # Normalized L2 distance
                if similarity >= score_threshold:
                    results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "relevance_score": float(similarity)
                    })
        
        return results


def search_with_reranking(
    query: str,
    vector_store,
    k: int = 10,
    initial_k: int = 50,
    score_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Search with LLM-based reranking for improved relevance.
    
    Args:
        query: The search query
        vector_store: FAISS vector store instance
        k: Final number of results after reranking
        initial_k: Number of candidates to retrieve before reranking
        score_threshold: Minimum relevance score for initial retrieval
    
    Returns:
        Reranked list of documents
    """
    
    # Step 1: Get initial candidates
    initial_results = search_documents(
        query=query,
        vector_store=vector_store,
        k=initial_k,
        score_threshold=score_threshold
    )
    
    if len(initial_results) == 0:
        return []
    
    # Step 2: Rerank with LLM
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    rerank_prompt = f"""Given the query: "{query}"
    
    Rate the relevance of each document on a scale of 0-10.
    Respond with only a comma-separated list of scores.
    
    Documents:
    """
    
    for idx, result in enumerate(initial_results):
        rerank_prompt += f"\n{idx+1}. {result['content'][:200]}..."
    
    try:
        response = llm.invoke(rerank_prompt)
        scores = [float(s.strip()) for s in response.content.split(",")]
        
        # Combine original results with new scores
        for idx, result in enumerate(initial_results):
            if idx < len(scores):
                result["rerank_score"] = scores[idx] / 10.0  # Normalize to 0-1
        
        # Sort by rerank score
        initial_results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        
    except Exception as e:
        print(f"Reranking failed: {e}, using original order")
    
    return initial_results[:k]


def multi_query_search(
    query: str,
    vector_store,
    k: int = 10,
    score_threshold: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Generate multiple query variations and aggregate results.
    
    Args:
        query: Original search query
        vector_store: FAISS vector store instance
        k: Number of final results
        score_threshold: Minimum relevance score
    
    Returns:
        Deduplicated and ranked search results
    """
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    # Generate query variations
    variation_prompt = f"""Generate 3 alternative versions of this search query to improve retrieval:
    
    Original: {query}
    
    Respond with only 3 queries, one per line."""
    
    try:
        response = llm.invoke(variation_prompt)
        queries = [query] + [q.strip() for q in response.content.split("\n") if q.strip()][:3]
    except:
        queries = [query]
    
    # Search with all query variations
    all_results = {}
    for q in queries:
        results = search_documents(
            query=q,
            vector_store=vector_store,
            k=k * 2,  # Get more candidates
            score_threshold=score_threshold
        )
        
        # Aggregate by content (deduplicate)
        for result in results:
            content_key = result["content"][:100]  # Use first 100 chars as key
            if content_key not in all_results:
                all_results[content_key] = result
            else:
                # Keep higher score
                if result["relevance_score"] > all_results[content_key]["relevance_score"]:
                    all_results[content_key] = result
    
    # Sort by score and return top k
    final_results = sorted(
        all_results.values(), 
        key=lambda x: x["relevance_score"], 
        reverse=True
    )
    
    return final_results[:k]
