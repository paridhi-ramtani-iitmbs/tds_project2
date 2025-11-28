from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import uuid
import logging
import asyncio
from typing import Dict, Any

from config import USER_SECRET
from scraper import fetch_page_content
from agent import solve_challenge

# Setup Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

app = FastAPI()

# Mount Frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory DB
TASKS: Dict[str, Any] = {}

class RunRequest(BaseModel):
    email: str
    secret: str
    url: str

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/run")
async def run_task(req: RunRequest, bg: BackgroundTasks):
    if req.secret != USER_SECRET:
        raise HTTPException(status_code=403, detail="Invalid Secret")
        
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "running", "logs": []}
    
    bg.add_task(process_quiz, task_id, req.email, req.secret, req.url)
    
    return {"task_id": task_id, "status": "started"}

@app.get("/tasks/{task_id}")
def get_status(task_id: str):
    return TASKS.get(task_id, {"status": "not_found"})

@app.get("/tasks")
def get_all_tasks():
    return TASKS

async def process_quiz(task_id: str, email: str, secret: str, start_url: str):
    log = TASKS[task_id]["logs"]
    current_url = start_url
    
    try:
        # Loop to handle multi-step quizzes
        max_steps = 10  # Increased to handle longer quiz chains
        
        for step in range(max_steps):
            log.append(f"===== Step {step+1} =====")
            log.append(f"Processing: {current_url}")
            
            # 1. Scrape with retry
            max_scrape_retries = 2
            content = None
            
            for scrape_attempt in range(max_scrape_retries):
                try:
                    content = await fetch_page_content(current_url)
                    log.append(f"✓ Page scraped successfully ({len(content)} chars)")
                    break
                except Exception as e:
                    log.append(f"✗ Scrape attempt {scrape_attempt+1} failed: {str(e)[:100]}")
                    if scrape_attempt == max_scrape_retries - 1:
                        TASKS[task_id]["status"] = "failed"
                        log.append("Failed to scrape page after retries")
                        return
                    await asyncio.sleep(2)
            
            if not content:
                TASKS[task_id]["status"] = "failed"
                log.append("No content retrieved")
                return
            
            # 2. Solve with retry
            max_solve_retries = 2
            result = None
            
            for solve_attempt in range(max_solve_retries):
                result = solve_challenge(content)
                
                if "error" not in result:
                    break
                    
                log.append(f"✗ Solve attempt {solve_attempt+1} failed: {result.get('error', 'Unknown')[:100]}")
                
                if solve_attempt == max_solve_retries - 1:
                    log.append(f"Solver Error: {result['error']}")
                    TASKS[task_id]["status"] = "failed"
                    return
                    
                await asyncio.sleep(2)
            
            if not result or "error" in result:
                log.append(f"Failed to generate solution")
                TASKS[task_id]["status"] = "failed"
                return

            answer = result.get("answer")
            submit_url = result.get("submit_url")
            
            log.append(f"✓ Generated Answer: {str(answer)[:200]}")
            log.append(f"✓ Submit URL: {submit_url}")
            
            # 3. Submit
            payload = {
                "email": email,
                "secret": secret,
                "url": current_url,
                "answer": answer
            }
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(submit_url, json=payload)
                    resp_data = resp.json()
                    
                log.append(f"✓ Submission Response: {resp_data}")
                
                if resp_data.get("correct"):
                    log.append("✓ Answer CORRECT!")
                    next_url = resp_data.get("url")
                    
                    if next_url:
                        current_url = next_url
                        log.append(f"→ Moving to next step: {next_url}")
                        await asyncio.sleep(1)  # Brief pause between steps
                        continue  # Go to next step
                    else:
                        TASKS[task_id]["status"] = "completed"
                        log.append("🎉 Quiz Finished Successfully!")
                        return
                else:
                    reason = resp_data.get("reason", "No reason provided")
                    log.append(f"✗ Answer INCORRECT: {reason}")
                    
                    # Check if we can skip to next question
                    next_url = resp_data.get("url")
                    if next_url:
                        log.append(f"→ Skipping to next question: {next_url}")
                        current_url = next_url
                        await asyncio.sleep(1)
                        continue
                    else:
                        TASKS[task_id]["status"] = "failed"
                        log.append("No next URL provided. Quiz ended.")
                        return
                        
            except httpx.HTTPStatusError as e:
                log.append(f"✗ HTTP Error during submission: {e.response.status_code}")
                TASKS[task_id]["status"] = "failed"
                return
            except Exception as e:
                log.append(f"✗ Submission failed: {str(e)[:200]}")
                TASKS[task_id]["status"] = "failed"
                return
        
        # If we exit the loop without completing
        log.append(f"Reached maximum steps ({max_steps})")
        TASKS[task_id]["status"] = "incomplete"

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        TASKS[task_id]["status"] = "error"
        log.append(f"❌ Critical Error: {str(e)}")
