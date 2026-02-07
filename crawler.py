from playwright.async_api import async_playwright
from fastapi import HTTPException
import asyncio

class BrowserManager:
    _instance = None
    _browser = None
    _playwright = None

    @classmethod
    async def get_browser(cls):
        if cls._browser is None:
            cls._playwright = await async_playwright().start()
            cls._browser = await cls._playwright.chromium.launch(headless=True)
        return cls._browser

    @classmethod
    async def close(cls):
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None

async def fetch_page(url: str) -> str:
    """
    Fetches the raw HTML content of a page using a shared Playwright browser instance.
    """
    try:
        browser = await BrowserManager.get_browser()
        
        # Create a new context with a realistic user agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = await context.new_page()
        
        # Block unnecessary resources to speed up loading
        await page.route("**/*", lambda route: route.abort() 
            if route.request.resource_type in ["image", "stylesheet", "font", "media"] 
            else route.continue_())

        # Navigate to the URL
        # Wait for domcontentloaded to ensure basic content is there. 
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        if not response:
            await context.close()
            raise HTTPException(status_code=400, detail="Failed to load page")
        
        if response.status >= 400:
            await context.close()
            raise HTTPException(status_code=response.status, detail=f"Page returned status {response.status}")

        # Get the full HTML
        content = await page.content()
        
        await context.close()
        return content

    except Exception as e:
        # In production, log this error
        print(f"Crawler error for {url}: {e}")
        raise HTTPException(status_code=500, detail=f"Crawler error: {str(e)}")
