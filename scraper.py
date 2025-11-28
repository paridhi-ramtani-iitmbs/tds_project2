import logging
import asyncio
from playwright.async_api import async_playwright

logger = logging.getLogger("uvicorn")

async def fetch_page_content(url: str) -> str:
    logger.info(f"Scraping URL: {url}")
    async with async_playwright() as p:
        # Launch with User-Agent to avoid bot detection
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            await page.goto(url, timeout=30000) # Increased timeout
            
            # Wait for generic load state
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except:
                pass
            
            # Get text
            content = await page.inner_text("body")
            
            # Fallback to full HTML if text is empty
            if not content.strip():
                logger.warning("Empty body text, falling back to HTML content")
                content = await page.content()
                
            return content
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            raise e
        finally:
            await browser.close()
