from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import uuid
import logging
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
        for step in range(5):
            log.append(f"Step {step+1}: Processing {current_url}")
            
            # 1. Scrape
            content = await fetch_page_content(current_url)
            log.append("Page scraped successfully")
            
            # 2. Solve
            result = solve_challenge(content)
            if "error" in result:
                log.append(f"Solver Error: {result['error']}")
                TASKS[task_id]["status"] = "failed"
                return

            answer = result.get("answer")
            submit_url = result.get("submit_url")
            log.append(f"Generated Answer: {answer}")
            
            # 3. Submit
            payload = {
                "email": email,
                "secret": secret,
                "url": current_url,
                "answer": answer
            }
            
            async with httpx.AsyncClient() as client:
                resp = await client.post(submit_url, json=payload, timeout=10)
                resp_data = resp.json()
                
            log.append(f"Submission Response: {resp_data}")
            
            if resp_data.get("correct"):
                next_url = resp_data.get("url")
                if next_url:
                    current_url = next_url
                    continue # Go to next step
                else:
                    TASKS[task_id]["status"] = "completed"
                    log.append("Quiz Finished!")
                    return
            else:
                TASKS[task_id]["status"] = "failed"
                log.append(f"Incorrect Answer: {resp_data.get('reason')}")
                return

    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        TASKS[task_id]["status"] = "error"
        log.append(f"Critical Error: {str(e)}")
