from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from src.schemas import ArticleSchema, MonitoredSource, MonitoredSourceRequest, ChangeEvent, Subscriber, SubscriberRequest, GeneralPageSchema
from typing import List, Optional, Union
from src.crawler import fetch_page, BrowserManager
from src.cleaner import clean_html
from src.extractor import extract_metadata
from src.cache import CacheService
from src.monitor_service import MonitorService
from src.refresher import refresh_monitored_sources_task
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import asyncio
import time

app = FastAPI(
    title="ASPL - AI Schema Protocol Layer",
    description="Transforms article-based webpages into machine-readable, unified semantic JSON.",
    version="0.1.0"
)

# Initialize services
cache = CacheService()
monitor_service = MonitorService()
REFRESH_INTERVAL = 300 # 5 minutes

@app.on_event("startup")
async def startup_event():
    # Warm up the browser
    await BrowserManager.get_browser()
    # Start background loop (optional, or just rely on manual trigger for now as per plan)
    asyncio.create_task(periodic_refresh())

async def periodic_refresh():
    while True:
        await asyncio.sleep(REFRESH_INTERVAL)
        # We invoke the task. 
        # Note: If this takes long, we might want to be careful with overlaps, 
        # but for MVP sequential is fine.
        await refresh_monitored_sources_task(monitor_service, cache)

@app.on_event("shutdown")
async def shutdown_event():
    await cache.close()
    await monitor_service.close()
    await BrowserManager.close()

@app.get("/")
async def root():
    return {"message": "ASPL API is running. Documentation at /docs"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/.well-known/aspl.json")
@app.get("/aspl-manifest")
async def get_manifest():
    """
    Returns the ASPL Agent Integration Manifest.
    """
    return {
        "service_name": "ASPL - AI Schema Protocol Layer",
        "version": "0.1.0",
        "description": "A semantic gateway that transforms raw article-based webpages into machine-readable, structured Universal Article Schema (UAS) JSON.",
        "endpoints": [
            {
                "path": "/parse",
                "method": "POST",
                "action": "fetch_article",
                "input": {
                    "url": "string (The target article URL)"
                },
                "output_schema": "ArticleSchema"
            },
            {
                "path": "/monitor",
                "method": "POST",
                "action": "add_monitor",
                "input": {"url": "string", "type": "string"},
                "output_schema": "MonitoredSource"
            },
            {
                "path": "/monitor",
                "method": "GET",
                "action": "list_monitors",
                "input": {},
                "output_schema": "List[MonitoredSource]"
            },
            {
                "path": "/changes",
                "method": "GET",
                "action": "list_changes",
                "input": {
                    "since_time": "datetime (ISO)",
                    "limit": "integer"
                },
                "output_schema": "List[ChangeEvent]"
            },
            {
                "path": "/subscribe",
                "method": "POST",
                "action": "add_subscriber",
                "input": {"callback_url": "string"},
                "output_schema": "Subscriber"
            }
        ],
        "schema_definition": {
            "fields": [
                {"name": "url", "type": "string", "description": "The requested URL"},
                {"name": "title", "type": "string", "description": "Extracted headline"},
                {"name": "subtitle", "type": "string", "description": "Subtitle or deck"},
                {"name": "authors", "type": "array[string]", "description": "List of author names"},
                {"name": "published_date", "type": "datetime", "description": "Original publication date"},
                {"name": "main_text", "type": "string", "description": "Full cleaned content in Markdown"},
                {"name": "summary", "type": "string", "description": "AI-generated executive summary"},
                {"name": "entities", "type": "object", "description": "Named entities (people, orgs, locations, dates)"},
                {"name": "topics", "type": "array[string]", "description": "Key topics/categories"},
                {"name": "fetched_at", "type": "datetime", "description": "Timestamp of processing"}
            ]
        }
    }

@app.post("/parse", response_model=Union[ArticleSchema, GeneralPageSchema])
async def parse_article(url: str):
    """
    Main endpoint to parse an article URL into UAS JSON.
    """
    # Timings dictionary
    timings = {
        "total": 0,
        "cache_read": 0,
        "crawl": 0,
        "clean": 0,
        "extract": 0,
        "cache_write": 0
    }
    
    start_total = time.time()
    
    # 0. Check Cache
    t0 = time.time()
    cached_article = await cache.get_article(url)
    timings["cache_read"] = time.time() - t0
    
    if cached_article:
        print(f"Cache HIT for {url}")
        timings["total"] = time.time() - start_total
        # Inject timings into response if schema allowed, but for now just print/log
        print(f"Timings: {timings}")
        return cached_article

    print(f"Cache MISS for {url}. Fetching...")
    
    # 1. Crawl
    t1 = time.time()
    try:
        html_content = await fetch_page(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch page: {str(e)}")
    timings["crawl"] = time.time() - t1
    
    # 2. Clean
    print("Cleaning content...")
    t2 = time.time()
    try:
        markdown_content = clean_html(html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clean content: {str(e)}")
    timings["clean"] = time.time() - t2
        
    # 3. Extract
    print("Extracting metadata with LLM...")
    t3 = time.time()
    try:
        article = await extract_metadata(markdown_content, html_content, url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract metadata: {str(e)}")
    timings["extract"] = time.time() - t3
    
    # 4. Cache Result
    t4 = time.time()
    await cache.set_article(url, article)
    timings["cache_write"] = time.time() - t4
    
    # Calculate processing time
    timings["total"] = time.time() - start_total
    print(f"Processed {url} in {timings['total']:.2f}s")
    print(f"Detailed Timings: {timings}")
    
    # We could add timings to the response headers
    # response.headers["X-Timings"] = json.dumps(timings)
    
    return article

# --- Monitor Endpoints ---

@app.post("/monitor", response_model=MonitoredSource)
async def monitor_source(request: MonitoredSourceRequest):
    """
    Register a new URL to be monitored.
    """
    new_source = MonitoredSource(
        url=request.url,
        type=request.type
    )
    await monitor_service.add_source(new_source)
    return new_source

@app.get("/monitor", response_model=List[MonitoredSource])
async def list_monitored_sources():
    """
    List all monitored sources.
    """
    return await monitor_service.get_all_sources()

@app.delete("/monitor/{source_id}")
async def delete_monitored_source(source_id: UUID):
    """
    Stop monitoring a specific source.
    """
    await monitor_service.delete_source(source_id)
    return {"status": "deleted", "id": str(source_id)}

@app.get("/changes", response_model=List[ChangeEvent])
async def list_changes(
    since_time: Optional[datetime] = None,
    limit: int = 50,
    include_uas: bool = False
):
    """
    List detected change events.
    
    - **since_time**: Optional ISO datetime.
    - **limit**: Max number of events.
    - **include_uas**: If True, includes the full current ArticleSchema in the response (from cache).
    """
    events = await monitor_service.get_change_events(limit=limit, since_time=since_time)
    
    if include_uas:
        for event in events:
            # Try to populate current_article from cache
            # We assume the URL's current cache state corresponds roughly to this event 
            # (especially for the latest event).
            article = await cache.get_article(event.url)
            if article:
                event.current_article = article
                
    return events

@app.post("/refresh-monitored")
async def trigger_refresh(background_tasks: BackgroundTasks):
    """
    Manually trigger the monitoring refresh job in the background.
    """
    background_tasks.add_task(refresh_monitored_sources_task, monitor_service, cache)
    return {"status": "refresh_logic_triggered"}

# --- Subscriber Endpoints ---

@app.post("/subscribe", response_model=Subscriber)
async def subscribe_webhook(request: SubscriberRequest):
    """
    Register a webhook to receive change events.
    """
    new_sub = Subscriber(
        callback_url=request.callback_url,
        url_prefix_filter=request.url_prefix_filter
    )
    await monitor_service.add_subscriber(new_sub)
    return new_sub

@app.get("/subscribe", response_model=List[Subscriber])
async def list_subscribers():
    """
    List all registered webhook subscribers.
    """
    return await monitor_service.get_all_subscribers()

@app.delete("/subscribe/{sub_id}")
async def delete_subscriber(sub_id: UUID):
    """
    Remove a webhook subscriber.
    """
    await monitor_service.delete_subscriber(sub_id)
    return {"status": "deleted", "id": str(sub_id)}
