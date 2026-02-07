# ASPL Integration Guide for Agents

This guide explains how to integrate the **ASPL (AI Schema Protocol Layer)** into your AI agent or optional toolset.

## 1. Tool Definition

If you are defining a tool for an LLM (e.g., OpenAI functions, LangChain tools), use the following specification:

- **Tool Name:** `fetch_article_via_aspl`
- **Description:** Fetches an article from a URL and returns structured, cleaned content (including summary, entities, and full text). Use this for reading news, blogs, or documentation. Do ONLY operate on specific article URLs, not general domain roots.
- **Input Schema:**
  ```json
  {
    "type": "object",
    "properties": {
      "url": {
        "type": "string",
        "description": "The absolute URL of the article to read."
      }
    },
    "required": ["url"]
  }
  ```
- **Output:** structured `ArticleSchema` JSON.

## 2. Usage Rules

> **System Prompt Rule:**
> "When the user asks to read a specific URL, or when you decide you need to visit a URL to gather information, you MUST call the `fetch_article_via_aspl` tool instead of requesting raw HTML or guessing the content."

## 3. Scenarios

### Scenario A: User-Driven Request
**User:** "Can you summarize this article for me? https://example.com/news/tech-trends"

**Agent Behavior:**
1.  Recognizes the intent to read a URL.
2.  Calls tool: `fetch_article_via_aspl(url="https://example.com/news/tech-trends")`
3.  Receives JSON.
4.  Generates summary based on `json.summary` and `json.main_text`.

### Scenario B: Agent-Driven Research
**User:** "Find out what Paul Graham thinks about Lisp."

**Agent Behavior:**
1.  Agent searches and finds a relevant link: `http://www.paulgraham.com/avg.html`.
2.  Agent decides to read it.
3.  Calls tool: `fetch_article_via_aspl(url="http://www.paulgraham.com/avg.html")`.
4.  Receives JSON.
5.  Extracts key points from `json.main_text` to answer the user's question.

### Scenario C: Change Monitoring (Feed Subscription)
**Context:** An agent needs to keep a knowledge base updated with the latest news from specific sources.

**Workflow:**
1.  **Subscribe:** Call `POST /monitor` with the URLs to track.
2.  **Poll for Changes:** Periodically call `GET /changes?since_time={LAST_SEEN_TIMESTAMP}&include_uas=true`.
3.  **Process:** Iterate through the returned `ChangeEvent` list.
    *   For each event, `current_article` contains the latest content.
    *   Update the local knowledge base (RAG/Vector DB) with the new text.
4.  **Checkpoint:** Store the latest `detected_at` timestamp from the response to use as `since_time` in the next call.

## 4. Prompt & Execution Examples

### Example 1: The Tool Call
**LLM Thought:** "I need to read the content of the provided link to answer the user."
**Tool Call:**
```json
{
  "name": "fetch_article_via_aspl",
  "arguments": {
    "url": "https://www.paulgraham.com/avg.html"
  }
}
```

### Example 2: The Logic (Returned JSON)
**System (ASPL) Response:**
```json
{
  "title": "Beating the Averages",
  "authors": ["Paul Graham"],
  "summary": "Paul Graham discusses the strategic advantage of using Lisp in startups...",
  "main_text": "In the summer of 1995, my friend Robert Morris and I started a startup called Viaweb...",
  "entities": {
    "organizations": ["Viaweb", "Yahoo"]
  }
}
```

### Example 3: The Final Answer
**LLM Response:**
"According to the article **'Beating the Averages'** by **Paul Graham**, he believes that using powerful languages like Lisp can give startups a significant competitive advantage (a 'secret weapon'). He illustrates this with the story of **Viaweb**, which was able to outpace competitors by developing faster thanks to Lisp's features."
