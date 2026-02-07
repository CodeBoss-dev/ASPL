# Agent Rules for ASPL Integration

These rules define how AI agents must interact with the ASPL system to ensure performance, cost-efficiency, and accuracy.

## 1. Mandatory Tool Usage
*   **Rule:** When you need to read, summarize, or extract information from a specific URL, you **MUST** use the `fetch_article_via_aspl` tool.
*   **Prohibition:** You are **NOT** allowed to use standard HTTP GET requests, `browsing` tools, or `curl` to fetch raw HTML from article domains. ASPL is your exclusive gateway for article content.

## 2. Handling Missing Information
*   **Rule:** If the specific information requested by the user is not present in the structured JSON returned by ASPL (specifically in `main_text` or `entities`):
    *   Do **NOT** attempt to hallucinate or guess.
    *   You **MUST** state: **"Information not found in document."**

## 3. Decision Logic Examples

### Scenario A: Reading a New URL
*   **Context:** User says "Read this article: https://example.com/news"
*   **Decision:** "I do not have the content for this URL. I need to read it."
*   **Action:** Call `fetch_article_via_aspl(url="https://example.com/news")`

### Scenario B: Redundant Information
*   **Context:** You have previously called ASPL for a URL and now have the JSON summary. User asks "What was the summary?"
*   **Decision:** "I already have the summary in my context window."
*   **Action:** Return the answer from context. **NO** new tool call needed.

## 4. Cost Optimization Rule
*   **Rule:** **Reuse JSON.** Once you have fetched the ASPL JSON for a URL, retain it in your context. Do not refetch the same URL within the same session unless explicitly instructed by the user to "refresh" or "check for updates." Refetching wastes tokens and adds latency.
