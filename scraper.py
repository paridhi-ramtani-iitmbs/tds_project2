import logging
from playwright.async_api import async_playwright

logger = logging.getLogger("uvicorn")

async def fetch_page_content(url: str) -> str:
    """
    Launches a headless browser, waits for JS execution, and returns text.
    """
    logger.info(f"Scraping URL: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Create context to ensure clean session
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(url)
            # Wait for network to be idle (ensures scripts loaded)
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except:
                logger.warning("Network idle timeout, proceeding anyway")

            # Try to get readable text from body
            content = await page.inner_text("body")
            
            # If body is empty, get full HTML
            if not content.strip():
                content = await page.content()
                
            return content
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            raise e
        finally:
            await browser.close()
