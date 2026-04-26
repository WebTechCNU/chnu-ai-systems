# Migration to Structured Ingestion - Quick Start

## 🎯 What Changed

Your RAG system now uses **structured ingestion** that keeps teacher profiles intact instead of splitting them into random chunks.

---

## ⚡ Quick Migration (5 Minutes)

### Step 1: Backup Current Data (Optional)
```powershell
# Backup your current vector store
Copy-Item -Recurse src\data\faiss_store\math-faculty src\data\faiss_store\math-faculty.backup
```

### Step 2: Start Server
```powershell
cd src
uvicorn app:app --reload
```

### Step 3: Re-Ingest with Structured Mode

```powershell
# Login
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/login" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username": "admin", "password": "yourpassword"}'

$token = ($response.Content | ConvertFrom-Json).access_token

# Re-ingest (this will overwrite old data)
Invoke-WebRequest -Uri "http://localhost:8000/api/ingestion-job" `
  -Method POST `
  -ContentType "application/json" `
  -Headers @{"Authorization" = "Bearer $token"} `
  -Body '{
    "urls": ["https://your-faculty-site.com/teachers"],
    "topic": "math-faculty",
    "use_structured": true
  }'
```

**Expected Output:**
```
Processing: https://...
  ✓ Added teacher profile: [Teacher Name]
  ✓ Added 5 course documents
...
Total documents to index: 150
✅ Vector store saved
```

### Step 4: Test the System

Test query about a teacher:
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/math-faculty" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{
    "question": "Хто викладає математичний аналіз?",
    "chat_history": [],
    "user_status": "student"
  }'
```

**What to Look For:**
- ✅ Complete teacher name in response
- ✅ List of courses they teach
- ✅ Contact information (email, phone)
- ✅ Position/title

---

## 📝 Validation Checklist

After re-ingestion, verify:

- [ ] Teacher names are always mentioned in responses
- [ ] Courses are linked to specific teachers
- [ ] Contact information appears when relevant
- [ ] Related information stays together (not fragmented)
- [ ] Search by course name returns the teacher
- [ ] Search by teacher name returns their courses

---

## 🔄 Rollback Plan

If you need to go back to the old system:

```powershell
# Restore backup
Remove-Item -Recurse src\data\faiss_store\math-faculty
Copy-Item -Recurse src\data\faiss_store\math-faculty.backup src\data\faiss_store\math-faculty

# Or re-ingest with legacy mode
# Set "use_structured": false in the ingestion request
```

---

## 🎓 Understanding the Differences

### Before (Generic Chunking):
- Teacher: "Іванов" [chunk 1]
- Description: "професор математики" [chunk 2]  
- Course: "Математичний аналіз" [chunk 3]
- Email: "ivanov@..." [chunk 4]

**Query:** "Хто викладає математичний аналіз?"  
**Response:** "Математичний аналіз" ❌ (no teacher name)

### After (Structured):
- **One complete document:**
  ```
  Викладач: Іванов Іван Іванович
  Посада: Професор
  Email: ivanov@...
  
  Курси:
  • Математичний аналіз I
  • Математичний аналіз II
  ```

**Query:** "Хто викладає математичний аналіз?"  
**Response:** "Математичний аналіз викладає професор Іванов Іван Іванович. Email: ivanov@..." ✅

---

## 🛠️ Customization

If teacher profiles aren't being detected, customize the parser:

Edit `src/services/ingest_structured.py`, line ~40:

```python
# Add your site's HTML patterns here
name_selectors = [
    'h1',                           # Generic
    'div.teacher-card h2',         # Your custom structure
    'span.profile-name',           # Another pattern
]
```

---

## 📊 Performance Notes

**Ingestion Time:**
- May take slightly longer (parsing HTML structure)
- But creates fewer, higher-quality documents

**Retrieval Quality:**
- Significantly improved context coherence
- Better entity relationships
- More complete answers

**Storage:**
- Slightly larger documents (less fragmentation)
- But better deduplication

---

## ✅ Success Stories

**Query Type 1 - Teacher Lookup:**
```
Q: "Розкажіть про професора Іванова"
A: [Complete profile with courses, contacts, research areas]
```

**Query Type 2 - Course Lookup:**
```
Q: "Хто викладає диференціальні рівняння?"
A: "Професор Іванов Іван Іванович викладає цей курс. 
    Контакт: ivanov@..."
```

**Query Type 3 - Multi-Entity:**
```
Q: "Які курси математичного аналізу доступні?"
A: "Математичний аналіз I та II викладає професор Іванов.
    Функціональний аналіз викладає доцент Петров..."
```

---

## 🆘 Need Help?

**Issue: No teacher profiles detected**
→ Check [STRUCTURED_INGESTION_GUIDE.md](STRUCTURED_INGESTION_GUIDE.md) section "Troubleshooting"

**Issue: Courses not linked to teachers**
→ Verify course list HTML structure in your pages

**Issue: Empty responses**
→ Check vector store loaded successfully in startup logs

---

## 📚 Additional Resources

- [STRUCTURED_INGESTION_GUIDE.md](STRUCTURED_INGESTION_GUIDE.md) - Full technical details
- [RAG_SYSTEM_REVIEW.md](RAG_SYSTEM_REVIEW.md) - Original bug analysis
- [QUICKSTART.md](QUICKSTART.md) - Initial setup guide

---

**Time to Complete:** 5-10 minutes  
**Risk Level:** Low (can rollback easily)  
**Impact:** High (much better answer quality)  

🚀 **Ready to migrate? Start with Step 1 above!**
