import logging
import asyncio
from playwright.async_api import async_playwright

logger = logging.getLogger("uvicorn")

async def fetch_page_content(url: str) -> str:
    logger.info(f"Scraping URL: {url}")
    async with async_playwright() as p:
        # Launch options
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url, timeout=15000)
            
            # Wait for content to likely load
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=5000)
            except:
                pass
                
            # Extract text first (better for tokens)
            text = await page.inner_text("body")
            
            # If text is too short, get HTML (maybe it's all in scripts)
            if len(text) < 50:
                text = await page.content()
                
            return text
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            raise e
        finally:
            await browser.close()
