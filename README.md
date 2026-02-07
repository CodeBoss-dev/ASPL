# ASPL - AI Schema Protocol Layer

ASPL is a semantic gateway that transforms messy, article-based webpages into clean, machine-readable JSON (Universal Article Schema). It allows AI agents to "read" the web faster, cheaper, and more reliably than ever before.

## Performance Story

Why fetch raw HTML when you can get structured data instantly?

1.  **Cold Fetch (First Visit):** ~10–12 seconds
    The first time a URL is requested, ASPL does the hard work: spinning up a headless browser, rendering JavaScript, cleaning the HTML, and using an LLM to extract metadata. It's computationally expensive, but it only happens once.

2.  **Warm Fetch (Cached):** ~0.004 seconds
    Once processed, the result is cached. Any subsequent request—whether from you or another agent—returns the JSON instantly. This is **3,000x faster** than a standard web request.

3.  **Token Savings (Cost):**
    Raw HTML is bloated with inline styles, scripts, and navigation markup. ASPL returns only the pure content in JSON. This reduces the context window usage for your downstream LLM agents by **50% to 90%**, significantly lowering your inference costs.

### Benchmark Results

| Metric | Direct Web Crawl / Cold Fetch | ASPL Warm Fetch |
| :--- | :--- | :--- |
| **Latency** | 10.0s - 15.0s | **0.004s** |
| **Reliability** | Variable (popups, ads) | **100% Structured** |
| **Token Cost** | High (Raw HTML noise) | **Low (Pure Content)** |
| **Agent Experience** | Slow & Fragile | **Instant & Robust** |

> **The Bottom Line:** After the first extraction, LLMs can visit any article through ASPL in milliseconds.
