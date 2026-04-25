# Quick Start Guide - RAG System Fixes

## 🚀 Getting Started After Bug Fixes

Follow these steps to get your RAG system working correctly:

---

## Step 1: Set Up Environment Variables

1. **Copy the example environment file:**
   ```bash
   copy .env.example .env
   ```

2. **Edit `.env` and add your actual API keys:**
   ```env
   # REQUIRED: Add your OpenAI API key
   OPENAI_API_KEY=sk-your-actual-key-here
   OPEN_API_KEY=sk-your-actual-key-here
   
   # REQUIRED: Add your LangChain API key (for tracing)
   LANGCHAIN_API_KEY=your-langchain-key-here
   
   # CRITICAL: Path to your FAISS vector stores
   VECTOR_DB_PATH=data/faiss_store
   
   # Generate a secure secret key for JWT
   SECRET_KEY=your-secret-key-change-this
   ```

   **To generate a secure SECRET_KEY:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

---

## Step 2: Verify Vector Store Files

**Check that your FAISS indices exist:**

```bash
# List the faiss_store directory
dir src\data\faiss_store /s

# You should see:
# src\data\faiss_store\
#   ├── index.faiss
#   ├── index.pkl
#   └── math-faculty\
#       ├── index.faiss
#       └── index.pkl
```

**If you're missing vector stores**, you need to create them first by ingesting data.

---

## Step 3: Install Dependencies

```bash
# Navigate to src directory
cd src

# Install Python packages
pip install -r requirements.txt
```

---

## Step 4: Start the Server

```bash
# From the src directory
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Watch for these startup messages:**

✅ **Good output:**
```
============================================================
Loading vector stores...
============================================================
🔍 Attempting to load vector store from: c:\...\src\data\faiss_store\math-faculty
   - VECTOR_DB_PATH: c:\...\src\data\faiss_store
   - Topic: math-faculty
   - Path exists: True
   - Contents: ['index.faiss', 'index.pkl']
✅ Successfully loaded vector store for topic: math-faculty

============================================================
Vector Store Loading Status:
============================================================
✅ SUCCESS: math_faculty vector store loaded
✅ SUCCESS: romanian_culture vector store loaded
✅ SUCCESS: qa_helper vector store loaded

✅ All vector stores loaded successfully!
============================================================
```

❌ **Bad output (needs fixing):**
```
❌ Skipping: No vector store found at c:\...\src\vector_store\math-faculty
❌ FAILED: math_faculty vector store did not load!
⚠️  WARNING: Some vector stores failed to load.
```

---

## Step 5: Test the System

### Test 1: Check API Health

Open browser to: `http://localhost:8000/docs`

You should see the FastAPI interactive documentation.

### Test 2: Test Math Faculty Endpoint

```bash
# Using curl (Windows PowerShell)
Invoke-WebRequest -Uri "http://localhost:8000/api/math-faculty" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"question": "Розкажіть про математичний факультет", "chat_history": [], "user_status": "student"}'
```

**Expected response:**
```json
{
  "status": "success",
  "answer": "... detailed answer ..."
}
```

**If you get an error:**
```json
{
  "status": "failed",
  "error": "Vector store not available. Please check server logs."
}
```
→ Go back to Step 1 and check your `VECTOR_DB_PATH` setting.

---

## Step 6: Create Missing Vector Stores (If Needed)

If you don't have vector stores yet, you need to ingest data first.

### Register an Admin User:

```bash
Invoke-WebRequest -Uri "http://localhost:8000/api/register" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username": "admin", "password": "admin123", "role": "admin"}'
```

### Login to Get Access Token:

```bash
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/login" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username": "admin", "password": "admin123"}'

$token = ($response.Content | ConvertFrom-Json).access_token
```

### Ingest Data:

```bash
Invoke-WebRequest -Uri "http://localhost:8000/api/ingestion-job" `
  -Method POST `
  -ContentType "application/json" `
  -Headers @{"Authorization" = "Bearer $token"} `
  -Body '{
    "urls": ["https://example.com/your-data-page"],
    "topic": "math-faculty"
  }'
```

This will scrape the URLs and create the FAISS vector store.

---

## 🔍 Troubleshooting

### Problem: "Vector store not available"

**Solution:**
1. Check `.env` file has `VECTOR_DB_PATH=data/faiss_store`
2. Verify files exist: `dir src\data\faiss_store\math-faculty`
3. Check server startup logs for path errors
4. If paths are correct but still failing, check file permissions

### Problem: "No relevant context found"

**Solution:**
1. Your score threshold might be too high (now fixed to 0.5)
2. Your query might not match the ingested data
3. Try the `/api/search` endpoint to see what's being retrieved:

```bash
Invoke-WebRequest -Uri "http://localhost:8000/api/search" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{
    "query": "математичний факультет",
    "topic": "math-faculty",
    "k": 10,
    "score_threshold": 0.3
  }'
```

### Problem: Empty results with low relevance scores

**Solution:**
- Your embeddings might not match your data
- Try reingesting with the updated `ingest.py` that includes source context
- Check that you're using the same OpenAI API key for both ingestion and retrieval

### Problem: Server won't start

**Solution:**
1. Check Python version: `python --version` (needs 3.10+)
2. Install missing packages: `pip install -r requirements.txt`
3. Check port 8000 is not already in use: `netstat -ano | findstr :8000`

---

## 📊 Monitoring

### Enable Debug Logging

The fixed code now includes detailed logging. Watch the console for:

- 🔍 Path resolution messages
- ✅ Successful loads
- ❌ Failed loads
- ⚠️ Warnings

### Check Retrieval Quality

Use the search endpoint to test retrieval:

```bash
# Test what documents are being retrieved
Invoke-WebRequest -Uri "http://localhost:8000/api/search" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{
    "query": "your test query here",
    "topic": "math-faculty",
    "k": 5,
    "score_threshold": 0.3,
    "search_type": "similarity_score_threshold"
  }'
```

Look at the `relevance_score` values. Good matches should be > 0.6.

---

## ✅ Success Checklist

- [ ] `.env` file created with all required keys
- [ ] `VECTOR_DB_PATH=data/faiss_store` is set
- [ ] All vector stores load successfully on startup
- [ ] API endpoints return answers (not errors)
- [ ] Relevance scores are reasonable (> 0.5 for good matches)
- [ ] No "NoneType" errors in logs
- [ ] Search endpoint returns relevant documents

---

## 🎯 Next Steps

Once everything is working:

1. **Test with real queries** to verify answer quality
2. **Monitor response times** - should be < 3 seconds
3. **Adjust score thresholds** based on your data quality
4. **Implement chat history** if you need multi-turn conversations
5. **Set up proper logging** to a file for production

---

## 📞 Still Having Issues?

Check:
1. [RAG_SYSTEM_REVIEW.md](RAG_SYSTEM_REVIEW.md) - Full bug analysis
2. Server console logs for detailed error messages
3. The `/docs` endpoint for API testing interface

---

**Version:** 1.0  
**Last Updated:** April 25, 2026
