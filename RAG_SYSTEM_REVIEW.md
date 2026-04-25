# RAG System Review - Critical Bugs & Recommendations

**Date:** April 25, 2026  
**System:** CHNU AI Systems - RAG-based Question Answering

---

## 🔴 CRITICAL BUGS - Data Retrieval Issues

### 1. **Vector Store Path Mismatch** ⚠️ HIGH PRIORITY
**Location:** [src/services/retriever.py](src/services/retriever.py), [src/services/ingest.py](src/services/ingest.py)

**Problem:**
- The code defaults to looking for vector stores at `src/vector_store/{topic}/`
- But your actual FAISS indices are stored at `src/data/faiss_store/{topic}/`
- This causes the retriever to fail loading the vector databases

**Evidence:**
```python
# retriever.py line 9-11
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH")
BASE_DIR = Path(__file__).resolve().parent.parent
VECTOR_DB_PATH = os.path.join(BASE_DIR, VECTOR_DB_PATH) if VECTOR_DB_PATH else os.path.join(BASE_DIR, "vector_store")
```

Your workspace structure shows:
```
src/data/faiss_store/
    index.faiss
    math-faculty/
        index.faiss
```

**Fix:**
Either:
1. Set `VECTOR_DB_PATH=data/faiss_store` in your `.env` file, OR
2. Change the default path in code to `"data/faiss_store"`

---

### 2. **Missing Error Handling During Vector Store Loading** ⚠️ HIGH PRIORITY
**Location:** [src/app.py](src/app.py#L28-L31)

**Problem:**
- If a vector store fails to load at startup, the app crashes or stores `None`
- Later requests will fail with unclear "NoneType has no attribute..." errors
- No validation that the stores actually loaded successfully

**Current Code:**
```python
app.state.vector_store = load_vector_store(Topic.MATH_FACULTY.value)
app.state.vector_store_buk = load_vector_store(Topic.ROMANIAN_CULTURE.value)
app.state.vector_store_qa = load_vector_store(Topic.QA_HELPER.value)
```

**Fix:**
```python
# Add validation after loading
vector_stores = {
    "math_faculty": load_vector_store(Topic.MATH_FACULTY.value),
    "romanian_culture": load_vector_store(Topic.ROMANIAN_CULTURE.value),
    "qa_helper": load_vector_store(Topic.QA_HELPER.value)
}

for name, store in vector_stores.items():
    if store is None:
        print(f"⚠️ WARNING: {name} vector store failed to load!")
    else:
        print(f"✓ {name} vector store loaded successfully")

app.state.vector_store = vector_stores["math_faculty"]
app.state.vector_store_buk = vector_stores["romanian_culture"]
app.state.vector_store_qa = vector_stores["qa_helper"]
```

---

### 3. **Retriever Context Formatting Issue** ⚠️ MEDIUM PRIORITY
**Location:** [src/services/rag_chain.py](src/services/rag_chain.py#L56-L59)

**Problem:**
- The RAG chain passes raw `Document` objects to the prompt template
- The template expects formatted string context
- LangChain should handle this, but explicit formatting is more reliable

**Current Code:**
```python
rag_chain = (
    {
        "context": retriever,  # ← Returns List[Document]
        "question": RunnablePassthrough()
    }
    | template
    | llm
    | StrOutputParser()
)
```

**Fix:**
Add a formatting function:
```python
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {
        "context": retriever | format_docs,  # ← Now returns formatted string
        "question": RunnablePassthrough()
    }
    | template
    | llm
    | StrOutputParser()
)
```

---

### 4. **Overly Restrictive Score Threshold** ⚠️ MEDIUM PRIORITY
**Location:** [src/services/rag_chain.py](src/services/rag_chain.py#L46-L50)

**Problem:**
- Score threshold set to `0.7` which is very high
- With `MultiQueryRetriever`, this compounds - multiple queries all need 0.7+ scores
- May result in "no context found" even for relevant questions

**Current Code:**
```python
base_retriever = vector_store.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={
        "k": 5,
        "score_threshold": 0.7  # ← Too restrictive
    }
)
```

**Recommendation:**
- Lower to `0.5` or `0.6` for better recall
- Or remove threshold entirely and just use `k` parameter
- Monitor query performance and adjust

---

### 5. **FAISS Similarity Score Conversion Error** ⚠️ MEDIUM PRIORITY
**Location:** [src/services/search.py](src/services/search.py#L78-L87)

**Problem:**
- FAISS returns L2 distance scores (lower = more similar)
- The conversion `similarity = 1 / (1 + score)` is overly simplistic
- For large distances, this always gives low scores even if documents are relevant
- The threshold check happens AFTER conversion, which may filter out good results

**Current Code:**
```python
docs_and_scores = vector_store.similarity_search_with_score(query, **search_kwargs)

results = []
for doc, score in docs_and_scores:
    # FAISS returns distance, convert to similarity
    similarity = 1 / (1 + score)  # ← Problematic conversion
    if similarity >= score_threshold:
        results.append({...})
```

**Fix:**
Use LangChain's built-in similarity methods or normalize properly:
```python
# Option 1: Use similarity_search_with_relevance_scores instead
docs_and_scores = vector_store.similarity_search_with_relevance_scores(query, **search_kwargs)

# Option 2: Better normalization for L2 distance
import numpy as np
for doc, distance in docs_and_scores:
    # Normalize L2 distance to 0-1 range using exponential decay
    similarity = np.exp(-distance)
    if similarity >= score_threshold:
        results.append({...})
```

---

### 6. **Unused chat_history Parameter** ⚠️ LOW PRIORITY
**Location:** [src/services/rag_chain.py](src/services/rag_chain.py#L26-L35)

**Problem:**
- All query functions accept `chat_history` but never use it
- This breaks conversational context and multi-turn queries
- Users expect follow-up questions to work

**Current Code:**
```python
def query_math_faculty(question: str, chat_history: list[str], vector_store):
    rag_chain = create_rag_chain(MATH_FACULTY_GENERAL, vector_store)
    return rag_chain.invoke(question)  # ← chat_history ignored
```

**Fix:**
Either:
1. Remove the parameter if not needed, OR
2. Implement chat history in the prompt:
```python
def query_math_faculty(question: str, chat_history: list[str], vector_store):
    # Format chat history
    history_text = "\n".join([f"User: {q}\nAssistant: {a}" for q, a in chat_history]) if chat_history else ""
    
    # Include in context
    full_question = f"Chat History:\n{history_text}\n\nCurrent Question: {question}"
    
    rag_chain = create_rag_chain(MATH_FACULTY_GENERAL, vector_store)
    return rag_chain.invoke(full_question)
```

---

### 7. **MultiQueryRetriever Potential Failures** ⚠️ LOW PRIORITY
**Location:** [src/services/rag_chain.py](src/services/rag_chain.py#L52-L55)

**Problem:**
- `MultiQueryRetriever` generates 3+ query variations
- If LLM fails to generate variations, retrieval may fail
- No fallback to basic retrieval

**Fix:**
```python
try:
    retriever = MultiQueryRetriever.from_llm(
        retriever=base_retriever, 
        llm=llm
    )
except Exception as e:
    print(f"MultiQueryRetriever failed: {e}, using base retriever")
    retriever = base_retriever
```

---

## 🟡 ARCHITECTURAL ISSUES

### 8. **Inconsistent Base Directory Resolution**
- [src/domain/database.py](src/domain/database.py): Uses `os.path.dirname(os.path.abspath(__file__))`
- [src/services/retriever.py](src/services/retriever.py): Uses `Path(__file__).resolve().parent`
- Mixed patterns make debugging paths difficult

**Recommendation:** Create a central `config.py` with path constants

---

### 9. **Missing Vector Store Null Checks**
**Location:** [src/app.py](src/app.py#L51-L54), [src/app.py](src/app.py#L65-L67), [src/app.py](src/app.py#L70-L72)

**Problem:**
- Endpoints don't check if vector_store is None before using it
- Will crash with unclear errors if store didn't load

**Fix:**
```python
@app.post("/api/math-faculty")
async def math_faculty(request: MathFacultyRequest, vector_store = Depends(get_vector_store)):
    if vector_store is None:
        return {"status": "failed", "error": "Vector store not available"}
    
    validation = validate(request.question)
    if not validation["meaningful"]:
        return {"status": "failed", "reasons": validation["reasons"]}
    
    result = query_math_faculty(request.question, request.chat_history, vector_store)
    return {"status": "success", "answer": result}
```

---

### 10. **Search Endpoint Vector Store Loading**
**Location:** [src/app.py](src/app.py#L80-L92)

**Problem:**
- Loads vector store on every request instead of using cached app.state
- Slower performance and potential file locking issues

**Current:**
```python
if request.topic == Topic.MATH_FACULTY:
    vector_store = load_vector_store(Topic.MATH_FACULTY.value)  # ← Loads from disk
elif request.topic == Topic.ROMANIAN_CULTURE:
    vector_store = load_vector_store(Topic.ROMANIAN_CULTURE.value)
```

**Fix:**
```python
# Reuse already-loaded stores
if request.topic == Topic.MATH_FACULTY:
    vector_store = request.app.state.vector_store
elif request.topic == Topic.ROMANIAN_CULTURE:
    vector_store = request.app.state.vector_store_buk
elif request.topic == Topic.QA_HELPER:
    vector_store = request.app.state.vector_store_qa
```

---

## 📋 RECOMMENDED FIXES PRIORITY

### Immediate (Fix Today):
1. ✅ Set correct `VECTOR_DB_PATH` in `.env` file
2. ✅ Add vector store loading validation with error messages
3. ✅ Add null checks in API endpoints

### Short Term (This Week):
4. ✅ Fix FAISS similarity score conversion
5. ✅ Lower score threshold or make it configurable
6. ✅ Add context formatting function to RAG chain
7. ✅ Use cached vector stores in search endpoint

### Medium Term (Next Sprint):
8. ✅ Implement chat history properly or remove parameter
9. ✅ Add error handling for MultiQueryRetriever
10. ✅ Create centralized configuration management

---

## 🧪 TESTING RECOMMENDATIONS

1. **Test Vector Store Loading:**
   ```bash
   # Check if paths exist
   ls src/data/faiss_store/math-faculty/
   ls src/data/faiss_store/romanian-culture/
   ls src/data/faiss_store/qa-helper/
   ```

2. **Test Retrieval:**
   - Add debug logging to see retrieved documents
   - Test with questions you KNOW should have answers in the data
   - Check relevance scores being returned

3. **Test Edge Cases:**
   - Empty queries
   - Very long queries
   - Queries with no matching context
   - Non-existent topics

---

## 🔧 IMMEDIATE ACTION PLAN

### Step 1: Fix the Path Issue
Create/update `.env` file:
```env
VECTOR_DB_PATH=data/faiss_store
```

### Step 2: Verify Vector Stores Exist
Check that these directories have `index.faiss` files:
- `src/data/faiss_store/math-faculty/`
- `src/data/faiss_store/romanian-culture/`
- `src/data/faiss_store/qa-helper/`

### Step 3: Add Debug Logging
Add to [src/services/retriever.py](src/services/retriever.py):
```python
def load_vector_store(topic: str) -> FAISS | None:
    path = os.path.join(VECTOR_DB_PATH, topic)
    
    print(f"🔍 Attempting to load vector store from: {path}")
    print(f"   - Path exists: {os.path.exists(path)}")
    if os.path.exists(path):
        print(f"   - Contents: {os.listdir(path)}")
    
    if not os.path.exists(path):
        print(f"❌ Skipping: No vector store found at {path}")
        return None 
    
    try:
        embeddings = OpenAIEmbeddings()
        vector_store = FAISS.load_local(
            path, 
            embeddings,
            allow_dangerous_deserialization=True
        )
        print(f"✅ Successfully loaded vector store for topic: {topic}")
        return vector_store
    except Exception as e:
        print(f"❌ Failed to load vector store for {topic}: {e}")
        return None
```

### Step 4: Test
Restart the app and check startup logs for vector store loading messages.

---

## 📊 ROOT CAUSE ANALYSIS

The main issue is **path misconfiguration**:
- The vector stores were saved to `src/data/faiss_store/` during ingestion
- The retriever looks for them at `src/vector_store/` by default
- No environment variable was set to override the default
- No error handling catches this mismatch

This causes all downstream retrieval to fail silently or return empty results.

---

## ✅ SUCCESS CRITERIA

After fixes, you should see:
1. ✅ All 3 vector stores load successfully on startup
2. ✅ API endpoints return relevant answers (not empty)
3. ✅ Search results have reasonable relevance scores (>0.5)
4. ✅ No "NoneType" errors in logs
5. ✅ Clear error messages if something fails

---

**End of Review**
