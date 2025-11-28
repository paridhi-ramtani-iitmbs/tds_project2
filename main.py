from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import uuid
import logging
import os
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

@app.post("/run")
async def run_task(req: RunRequest, bg: BackgroundTasks):
    # Verify Secret
    if req.secret != USER_SECRET:
        raise HTTPException(status_code=403, detail="Invalid Secret")
        
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "running", "logs": []}
    
    # Start background process
    bg.add_task(process_quiz, task_id, req.email, req.secret, req.url)
    
    return {"task_id": task_id, "status": "started"}

@app.get("/tasks/{task_id}")
def get_status(task_id: str):
    return TASKS.get(task_id, {"status": "not_found"})

async def process_quiz(task_id: str, email: str, secret: str, start_url: str):
    log = TASKS[task_id]["logs"]
    current_url = start_url
    max_steps = 10  # Safety break
    step_count = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        while current_url and step_count < max_steps:
            step_count += 1
            log.append(f"Step {step_count}: Processing {current_url}")
            
            try:
                # 1. Scrape
                content = await fetch_page_content(current_url)
                log.append(f"Page scraped ({len(content)} chars)")
                
                # 2. Solve (Initial Attempt)
                feedback = ""
                attempts = 0
                max_attempts = 2 # Allow 1 retry on failure
                
                while attempts < max_attempts:
                    attempts += 1
                    
                    # If retrying, append feedback to context
                    context_for_agent = content
                    if feedback:
                        context_for_agent += f"\n\nPREVIOUS ATTEMPT FAILED. REASON: {feedback}\nFix the code."

                    result = solve_challenge(context_for_agent)
                    
                    if "error" in result:
                        log.append(f"Solver Error: {result['error']}")
                        # If syntax error, maybe retry? For now, break to fail.
                        break

                    answer = result.get("answer")
                    submit_url = result.get("submit_url")
                    
                    # Sanity check on submit_url
                    if not submit_url or not submit_url.startswith("http"):
                        # Sometimes LLM gives relative path
                        # Simplified assumption: usually absolute in this specific quiz type
                        log.append(f"Warning: Invalid submit_url {submit_url}")

                    log.append(f"Generated Answer: {answer} (Attempt {attempts})")
                    
                    # 3. Submit
                    payload = {
                        "email": email,
                        "secret": secret,
                        "url": current_url,
                        "answer": answer
                    }
                    
                    log.append(f"Submitting to {submit_url}...")
                    resp = await client.post(submit_url, json=payload)
                    
                    try:
                        resp_data = resp.json()
                    except:
                        resp_data = {"error": resp.text}

                    log.append(f"Response: {resp_data}")
                    
                    if resp.status_code == 200 and resp_data.get("correct"):
                        # Success! Check for next URL
                        next_url = resp_data.get("url")
                        if next_url:
                            log.append("Correct! Moving to next question.")
                            current_url = next_url
                            break # Break retry loop, continue main loop
                        else:
                            TASKS[task_id]["status"] = "completed"
                            log.append("Quiz Finished Successfully!")
                            return
                    else:
                        # Failed
                        feedback = resp_data.get("reason", "Unknown error")
                        log.append(f"Incorrect: {feedback}")
                        if attempts == max_attempts:
                            TASKS[task_id]["status"] = "failed"
                            return
                        # If not last attempt, loop continues and calls solver again with feedback

            except Exception as e:
                logger.error(f"Workflow failed: {e}")
                log.append(f"Critical Error: {str(e)}")
                TASKS[task_id]["status"] = "error"
                return
