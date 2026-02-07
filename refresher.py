from fastapi import BackgroundTasks
from typing import Dict

# ... imports ...
from src.crawler import fetch_page, BrowserManager
from src.cleaner import clean_html
from src.extractor import extract_metadata
from src.schemas import ArticleSchema, MonitoredSource, ChangeEvent
from src.monitor_service import MonitorService
from src.utils import compute_content_hash
from src.cache import CacheService 
from src.config import MONITOR_DEFAULT_TTL
from datetime import datetime, timezone
from src.webhook import trigger_webhooks
# Make sure to invalidate cache on refresh? 
# or just bypass cache during refresh.

async def process_url_internal(url: str, cache_service: CacheService) -> ArticleSchema:
    """
    Internal function to process a URL: Crawl -> Clean -> Extract.
    This bypasses the standard 'read' cache but updates it.
    """
    # 1. Crawl
    print(f"[Refresher] Crawling {url}...")
    try:
        html_content = await fetch_page(url)
    except Exception as e:
        print(f"[Refresher] Failed to crawl {url}: {e}")
        raise e

    # 2. Clean
    try:
        markdown_content = clean_html(html_content)
    except Exception as e:
        print(f"[Refresher] Failed to clean {url}: {e}")
        raise e

    # 3. Extract
    try:
        article = await extract_metadata(markdown_content, url)
    except Exception as e:
        print(f"[Refresher] Failed to extract {url}: {e}")
        raise e
        
    # Update main read cache so subsequent reads are fast
    await cache_service.set_article(url, article)
    
    return article

async def refresh_monitored_sources_task(monitor_service: MonitorService, cache_service: CacheService):
    """
    Task to refresh all monitored sources and detect changes.
    """
    print("[Refresher] Starting refresh job...")
    
    sources = await monitor_service.get_all_sources()
    # Use timezone-aware UTC
    now = datetime.now(timezone.utc)
    
    for source in sources:
        try:
            # Check TTL
            if source.last_checked_at:
                # Ensure source.last_checked_at is aware. If naive, assume UTC.
                last_checked = source.last_checked_at
                if last_checked.tzinfo is None:
                    last_checked = last_checked.replace(tzinfo=timezone.utc)
                
                elapsed = (now - last_checked).total_seconds()
                if elapsed < MONITOR_DEFAULT_TTL:
                    # Skip this source
                    continue

            # Re-process the article
            # Note: We knowingly bypass the 'get' cache here because we WANT to see if it changed on the web.
            # However, `process_url_internal` *updates* the cache with the new version.
            new_article = await process_url_internal(source.url, cache_service)
            
            new_hash = compute_content_hash(new_article)
            
            # First time check
            if source.last_content_hash is None:
                print(f"[Refresher] Initial check for {source.url}. Setting hash.")
                source.last_content_hash = new_hash
                source.last_checked_at = new_article.fetched_at
                await monitor_service.add_source(source) # Update
                
            # Change detected
            elif new_hash != source.last_content_hash:
                print(f"[Refresher] CHANGE DETECTED for {source.url}!")
                
                event = ChangeEvent(
                    url=source.url,
                    source_id=source.id,
                    detected_at=new_article.fetched_at,
                    old_hash=source.last_content_hash,
                    new_hash=new_hash,
                    change_type="content_updated"
                )
                
                await monitor_service.add_change_event(event)

                # Trigger Webhooks
                await trigger_webhooks(event, monitor_service)
                
                # Update source state
                source.last_content_hash = new_hash
                source.last_checked_at = new_article.fetched_at
                await monitor_service.add_source(source)
            else:
                print(f"[Refresher] No change for {source.url}")
                # Still update checked_at?
                source.last_checked_at = new_article.fetched_at
                await monitor_service.add_source(source)

        except Exception as e:
            print(f"[Refresher] Error refreshing {source.url}: {e}")
            
    print("[Refresher] Job complete.")
