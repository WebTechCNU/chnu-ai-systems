# Structured Data Ingestion Guide

## 🎯 Problem Solved

**Before:** Teacher names, descriptions, and courses were split into random 300-character chunks, losing semantic relationships.

**After:** Teacher profiles are kept intact with all related information (name, position, courses, contacts) in single structured documents.

---

## 🏗️ How Structured Ingestion Works

### 1. **HTML Parsing**
The system now intelligently parses teacher profile pages to extract:
- Teacher name (from `<h1>`, `<h2>`, or class-based selectors)
- Position/title (професор, доцент, викладач)
- Email addresses (from `mailto:` links)
- Phone numbers (pattern matching)
- Course lists (from `<ul>`, `<ol>` near course-related headings)
- Descriptions (main content paragraphs)

### 2. **Document Structure**
Each teacher gets **two types of documents**:

#### A. Teacher Profile Document
```
Викладач: Іванов Іван Іванович
Посада: Професор кафедри математичного аналізу
Email: ivanov@example.com
Телефон: +380 XX XXX XXXX

Опис:
[Full biographical description and research interests]

Курси які викладає:
• Математичний аналіз I
• Математичний аналіз II
• Диференціальні рівняння
```

**Metadata:**
- `type`: "teacher_profile"
- `teacher_name`: "Іванов Іван Іванович"
- `position`: "Професор"
- `courses`: "Математичний аналіз I|Математичний аналіз II|..."
- `num_courses`: 3

#### B. Course-Specific Documents
For each course, a separate document links back to the teacher:

```
Курс: Математичний аналіз I

Викладач: Іванов Іван Іванович
Посада: Професор
Email: ivanov@example.com

[Brief description...]
```

**Metadata:**
- `type`: "course_info"
- `course_name`: "Математичний аналіз I"
- `teacher_name`: "Іванов Іван Іванович"

This dual approach ensures:
- **Searching by teacher name** → Get complete profile
- **Searching by course name** → Get teacher who teaches it

### 3. **Enhanced Retrieval**
New retrieval functions:
- **Deduplication:** Removes duplicate teacher profiles
- **Metadata boosting:** Prioritizes teacher_profile documents
- **Structured formatting:** Groups related information in context
- **Entity-aware search:** Can filter by document type

---

## 🚀 How to Use

### Step 1: Re-Ingest Your Data

The new structured ingestion is **enabled by default**. Just call the ingestion API:

```bash
# Login as admin
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/login" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username": "admin", "password": "admin123"}'

$token = ($response.Content | ConvertFrom-Json).access_token

# Ingest with structured parsing
Invoke-WebRequest -Uri "http://localhost:8000/api/ingestion-job" `
  -Method POST `
  -ContentType "application/json" `
  -Headers @{"Authorization" = "Bearer $token"} `
  -Body '{
    "urls": ["https://your-math-faculty-site.com/teachers"],
    "topic": "math-faculty",
    "use_structured": true
  }'
```

**What happens:**
1. System crawls all teacher profile pages
2. Parses HTML structure to extract entities
3. Creates comprehensive teacher documents
4. Creates course-specific documents
5. Saves to FAISS with rich metadata

### Step 2: Monitor Ingestion

Watch the console for structured parsing messages:

```
Processing: https://example.com/teachers/ivanov
  ✓ Added teacher profile: Іванов Іван Іванович
  ✓ Added 5 course documents

Processing: https://example.com/teachers/petrov
  ✓ Added teacher profile: Петров Петро Петрович
  ✓ Added 3 course documents

============================================================
Total documents to index: 150
============================================================

Indexed 100 / 150 documents...
Indexed 150 / 150 documents...

✅ Vector store saved to: c:\...\src\data\faiss_store\math-faculty
```

### Step 3: Test Queries

Now your queries will return complete, structured information:

**Query:** "Хто викладає математичний аналіз?"

**Response (before fix):**
```
Математичний аналіз
... це курс про функції ...
```
❌ No teacher name, no contact info

**Response (after fix):**
```
Математичний аналіз I та II викладає професор Іванов Іван Іванович.

Контактна інформація:
- Email: ivanov@example.com
- Телефон: +380 XX XXX XXXX
- Посада: Професор кафедри математичного аналізу

Професор Іванов також викладає:
• Диференціальні рівняння
• Функціональний аналіз
```
✅ Complete information with all relationships preserved

---

## 🔧 Configuration

### Customize HTML Parsing

Edit `src/services/ingest_structured.py` to adjust selectors for your site structure:

```python
def parse_teacher_profile(soup: BeautifulSoup, url: str):
    # Customize these selectors for your HTML structure
    name_selectors = [
        'h1',                    # Most common
        'h2.teacher-name',       # Custom class
        '.profile-name',         # Another pattern
        '[class*="name"]'        # Any class containing "name"
    ]
    
    # Add your own patterns here
```

### Adjust Chunking for Non-Teacher Pages

For pages that aren't teacher profiles, the system falls back to general chunking:

```python
# In ingest_structured.py, line ~170
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,      # Larger than before (was 300)
    chunk_overlap=200,   # More overlap for context
    separators=["\n\n", "\n", ". ", " ", ""]
)
```

### Enable Legacy Mode

If you need the old behavior:

```json
{
  "urls": ["..."],
  "topic": "math-faculty",
  "use_structured": false
}
```

---

## 📊 Comparison

| Aspect | Old (Generic Chunking) | New (Structured) |
|--------|----------------------|------------------|
| **Chunk Size** | 300 characters | Full profiles (1000-2000 chars) |
| **Teacher Name** | Sometimes lost | Always preserved |
| **Courses** | Separated from teacher | Linked to teacher |
| **Contact Info** | Random chunks | Structured in profile |
| **Searchability** | By keywords only | By entities (name, course, email) |
| **Metadata** | Only URL | Type, teacher, course, position, etc. |
| **Context Quality** | Fragmented | Complete and coherent |

---

## 🎓 Example Use Cases

### Use Case 1: Find Teacher by Name
**Query:** "Розкажіть про професора Іванова"

**Result:** Complete profile with all courses, contacts, and description

---

### Use Case 2: Find Teacher by Course
**Query:** "Хто викладає диференціальні рівняння?"

**Result:** Teacher name, profile, and how to contact them

---

### Use Case 3: Find All Teachers
**Query:** "Які викладачі працюють на факультеті?"

**Result:** List of teachers with their specializations

---

### Use Case 4: Course Details
**Query:** "Що вивчають в курсі математичного аналізу?"

**Result:** Course content + teacher who teaches it + contact info

---

## 🔍 Verification

### Check Your Data Structure

Use the search endpoint to inspect what was indexed:

```bash
Invoke-WebRequest -Uri "http://localhost:8000/api/search" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{
    "query": "викладач",
    "topic": "math-faculty",
    "k": 3,
    "score_threshold": 0.3
  }'
```

Look for:
- `"type": "teacher_profile"` documents
- `"type": "course_info"` documents
- `teacher_name`, `courses`, and other metadata fields
- Complete content with all sections

---

## 🐛 Troubleshooting

### Problem: "Not a teacher profile, using general chunking"

**Cause:** The HTML structure doesn't match expected patterns

**Solution:**
1. Inspect the HTML of your teacher pages
2. Update `name_selectors` in `parse_teacher_profile()`
3. Add custom selectors for your site's structure

Example:
```python
name_selectors = [
    'div.teacher-header h1',    # Your custom structure
    'span.full-name',            # Another pattern
    # ...
]
```

---

### Problem: No courses extracted

**Cause:** Course lists aren't detected

**Solution:**
1. Check what keywords appear near your course lists
2. Update `course_keywords` in `parse_teacher_profile()`:

```python
course_keywords = [
    'курс', 'course', 
    'дисципл', 'discipline',
    'викладає',  # Your custom keyword
    'teaches'     # Another pattern
]
```

---

### Problem: Empty teacher profiles

**Cause:** Parsing finds name but no content

**Solution:**
- Check that description paragraphs are being found
- Verify the `<p>` tags contain actual content
- May need to look for specific div classes with content

---

## ✅ Success Indicators

After re-ingestion, you should see:

1. **Startup logs show structured types:**
   ```
   ✓ Added teacher profile: [Name]
   ✓ Added 3 course documents
   ```

2. **Search returns complete profiles:**
   - Teacher name always present
   - Courses listed
   - Contact information included

3. **Metadata is populated:**
   ```json
   {
     "type": "teacher_profile",
     "teacher_name": "...",
     "courses": "Course1|Course2|...",
     "position": "..."
   }
   ```

4. **Better answer quality:**
   - Questions about courses return teacher names
   - Questions about teachers return complete profiles
   - Related information stays together

---

## 📈 Next Steps

1. **Re-ingest your data** with structured mode
2. **Test queries** about teachers and courses
3. **Customize HTML parsing** for your specific site
4. **Monitor answer quality** and adjust as needed

---

## 🔗 Related Files

- **Ingestion:** [src/services/ingest_structured.py](src/services/ingest_structured.py)
- **Enhanced Retrieval:** [src/services/retrieval_enhanced.py](src/services/retrieval_enhanced.py)
- **RAG Chain:** [src/services/rag_chain.py](src/services/rag_chain.py)
- **Prompt Templates:** [src/infrastructure/prompt_templates.py](src/infrastructure/prompt_templates.py)
- **API Endpoint:** [src/app.py](src/app.py) (line ~185)

---

**Version:** 2.0  
**Date:** April 26, 2026  
**Status:** ✅ Ready for Production
