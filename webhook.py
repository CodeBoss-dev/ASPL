import httpx
import asyncio
from src.schemas import ChangeEvent, Subscriber
from src.monitor_service import MonitorService

async def trigger_webhooks(event: ChangeEvent, monitor_service: MonitorService):
    """
    Triggers webhooks for a given ChangeEvent.
    """
    subscribers = await monitor_service.get_all_subscribers()
    if not subscribers:
        return

    # Prepare payload once
    # We send the raw event data. Subscribers can fetch details if needed.
    payload = event.model_dump(mode="json")
    
    # We don't want to block the refresher loop too long, so gather tasks?
    # Or just sequential if volume is low. Parallel is better.
    tasks = []
    for sub in subscribers:
        if sub.is_active:
            tasks.append(notify_single_subscriber(sub, event, payload, monitor_service))
    
    if tasks:
        await asyncio.gather(*tasks)

async def notify_single_subscriber(sub: Subscriber, event: ChangeEvent, payload: dict, monitor_service: MonitorService):
    # Check filter
    if sub.url_prefix_filter and not event.url.startswith(sub.url_prefix_filter):
        return

    print(f"[Webhook] Notifying {sub.id} ({sub.callback_url}) about {event.url}")
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(sub.callback_url, json=payload, timeout=10.0)
        
        # Reset failure count on success if it was non-zero
        if sub.failure_count > 0:
            sub.failure_count = 0
            await monitor_service.update_subscriber(sub)
            
    except Exception as e:
        print(f"[Webhook] Failed to notify {sub.id}: {e}")
        sub.failure_count += 1
        if sub.failure_count >= 5:
            print(f"[Webhook] Disabling subscriber {sub.id} due to excessive failures.")
            sub.is_active = False
        await monitor_service.update_subscriber(sub)
