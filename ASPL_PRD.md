
# 📄 PRD: ASPL – AI Schema Protocol Layer (Phase 1: Article-Based Websites)

## 1. Product Overview

ASPL (AI Schema Protocol Layer) is a system that takes arbitrary **article-based webpages** (news sites, blogs, knowledge articles) and transforms them into a **machine-readable, unified semantic format**.  
The goal is to allow AI agents to navigate, understand, and extract content **with lower latency, lower compute cost, and higher reliability** than raw webpage scraping or full-page LLM analysis.

ASPL exposes a **Universal Article Schema (UAS)** and a **Semantic Gateway API**.  
Any AI agent can request structured data for a given URL and receive:

- Clean article text  
- Title  
- Author(s)  
- Publish date  
- Summary (optional)  
- Named entities (people, places, organizations, dates)  
- Topic/category  
- Canonical metadata  

ASPL Phase 1 focuses **only on article-based content** because:
- It is structurally simpler  
- Has fewer anti-bot barriers  
- Has immediate real-world value  
- Produces great demo results for a portfolio  

---

## 2. Goals & Non-Goals

### 2.1 Goals
- Provide a **single endpoint** that transforms any article webpage into structured JSON following UAS.
- Use **LLM-powered extraction** + **structural heuristics** for high accuracy.
- Maintain a **cache** to minimize repeated LLM inference costs.
- Provide a **testing/demo harness** for validating output quality.
- Demonstrate **latency improvements** over direct LLM reading of webpage HTML.
- Produce clean “before → after” examples suitable for portfolio presentation.

### 2.2 Non-Goals
- Not indexing the entire internet (no global crawling).  
- Not supporting transactional schemas (e-commerce, bookings).  
- Not bypassing aggressive paywalls.  
- Not performing sentiment analysis or personalization.  

---

## 3. System Architecture Overview

### Pipeline:

```
             ┌────────────────────┐
             │ Incoming Request    │
             │   (URL provided)    │
             └─────────┬──────────┘
                       │
                       ▼
        ┌─────────────────────────────────┐
        │ 1. Cache Layer (Redis)          │
        │ - If URL exists → return JSON   │
        └─────────────────────────────────┘
                       │ Miss
                       ▼
        ┌─────────────────────────────────┐
        │ 2. Headless Crawler (Playwright)│
        │ - Load page                     │
        │ - Wait for DOM stability        │
        │ - Scroll/auto-trigger content   │
        │ - Extract HTML + Visible Text   │
        └─────────────────────────────────┘
                       │
                       ▼
        ┌─────────────────────────────────┐
        │ 3. Preprocessing Layer          │
        │ - HTML → Markdown (Jina/Firecrawl)
        │ - Strip navigation, ads, menus  │
        └─────────────────────────────────┘
                       │
                       ▼
        ┌─────────────────────────────────┐
        │ 4. LLM Extraction Engine        │
        │ - Apply UAS schema              │
        │ - Extract: title, author, etc.  │
        │ - Extract entities              │
        │ - Validate output               │
        └─────────────────────────────────┘
                       │
                       ▼
        ┌─────────────────────────────────┐
        │ 5. Validation & Schema Registry │
        │ - Enforce Universal Article     │
        │   Schema (JSON Schema)          │
        └─────────────────────────────────┘
                       │
                       ▼
        ┌─────────────────────────────────┐
        │ 6. Cache Result (Redis)         │
        └─────────────────────────────────┘
                       │
                       ▼
             ┌────────────────────┐
             │ Structured JSON API│
             │  (Semantic Gateway)│
             └────────────────────┘
```

---

## 4. Universal Article Schema (UAS)

```json
{
  "type": "object",
  "properties": {
    "url": {"type": "string"},
    "title": {"type": "string"},
    "subtitle": {"type": "string"},
    "authors": {"type": "array", "items": {"type": "string"}},
    "published_date": {"type": ["string", "null"], "format": "date-time"},
    "modified_date": {"type": ["string", "null"], "format": "date-time"},
    "main_text": {"type": "string"},
    "summary": {"type": "string"},
    "entities": {
      "type": "object",
      "properties": {
        "people": {"type": "array", "items": {"type": "string"}},
        "organizations": {"type": "array", "items": {"type": "string"}},
        "locations": {"type": "array", "items": {"type": "string"}},
        "dates": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {"raw": {"type": "string"}, "normalized": {"type": "string"}}
          }
        }
      }
    },
    "canonical_url": {"type": "string"},
    "topics": {"type": "array", "items": {"type": "string"}},
    "word_count": {"type": "integer"},
    "fetched_at": {"type": "string", "format": "date-time"}
  },
  "required": ["url", "title", "main_text", "word_count", "fetched_at"]
}
```

---

## 5. Functional Requirements

### 5.1 Core Requirements
1. System accepts any article-based URL.  
2. Must fetch, render, extract, and convert content to UAS JSON.  
3. Must detect and extract:
   - Title  
   - Author(s)  
   - Publish date  
   - Article body  
   - Named entities  
4. Must cache results to reduce cost and latency.  
5. Must validate output against the schema.

### 5.2 LLM Requirements
- Use OpenAI GPT-4o-mini, Claude Haiku, or Llama-3-8B local.  
- Template prompt must:
  - enforce JSON-only output  
  - enforce required fields  
  - summarize article text  
  - extract entities using simple heuristics  

### 5.3 Error Handling
- Non-article sites → return structured error  
- Paywalled pages → return “restricted”  
- JavaScript errors → auto-retry  
- LLM JSON invalid → retry with smaller sampling  

---

## 6. Non-Functional Requirements

### 6.1 Performance
- **First-time fetch:** ≤2.5 seconds  
- **Cached fetch:** ≤10 ms  
- **LLM extraction:** ≤800 ms (cloud) or ≤1.5s (local GPU)  
- **Throughput target:** 50 QPS per node  

### 6.2 Cost Constraints
- Cache hit ratio target: **>70%**  
- Average cost per fresh page: **<$0.002–$0.01** depending on model  
- Local inference optional to lower cloud expense  

### 6.3 Scalability
- Horizontal scaling via:
  - worker queue for fetch jobs  
  - deduplication for same URL  
  - sharded Redis cluster  

### 6.4 Security
- Do not store copyrighted text unless it is user-requested.  
- Respect robots.txt if not overridden by user.  

---

## 7. Testing Strategy (Proof That It Works)

### 7.1 Unit Tests
- HTML → Markdown preprocessor  
- UAS schema validator  
- Entity extraction logic  
- Cache insertion and retrieval  

### 7.2 Integration Tests
1. Feed URLs from 10 real news sources:  
   - BBC  
   - CNN  
   - Reuters  
   - AP News  
   - Medium  
   - NYT (free pages)  
2. Verify output JSON adheres to schema.  
3. Compare LLM summary vs human summary.  
4. Run latency benchmarks:
   - cold fetch  
   - warm fetch  

### 7.3 Latency & Cost Benchmarking
For each URL:
- measure:
  - Playwright load time  
  - LLM inference time  
  - Total pipeline latency  
- compare cost and latency with:
  - feeding raw HTML directly to LLM  
  - feeding extracted clean text to LLM  

Expected result:
- ASPL reduces tokens by 50–90%  
- ASPL reduces latency by 20–80%  
- ASPL reduces cost by 40–95%  

### 7.4 Golden Dataset
Create 50 manually verified article examples.  
Use this to:
- measure accuracy of title extraction  
- measure entity precision/recall  
- verify publish date detection  

### 7.5 Demonstration Harness
Create a UI showing raw webpage → ASPL structured JSON.

---

## 8. Technical Stack

### Backend
- Python 3.11  
- FastAPI  

### Crawler
- Playwright (headless Chromium)  

### Extraction
- Firecrawl or Jina Reader  
- LLM (GPT, Claude, or Llama)  
- spaCy fallback  

### Cache
- Redis  

### Schema Validation
- `jsonschema`  

### Testing
- Pytest  
- Locust  

---

## 9. MVP Scope

- Submit URL → returns UAS JSON  
- Cache layer  
- Basic crawler  
- LLM-based extraction  
- Validation  
- 5–10 example sites  
- Benchmarks  

---

## 10. Future Scope

- Multi-domain schemas  
- MCP integration  
- Browser sandbox for agents  
- Delta updates  
- Distributed crawler fleet  
- Semantic search across corpus  
