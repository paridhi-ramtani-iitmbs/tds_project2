import os
import json
import re
import subprocess
import sys
import uuid
import logging
from openai import OpenAI
# Import LLM_MODEL from config
from config import API_KEY, OPENAI_BASE_URL, LLM_MODEL 

logger = logging.getLogger("uvicorn")

client = OpenAI(api_key=API_KEY, base_url=OPENAI_BASE_URL)

def solve_challenge(task_text: str):
    logger.info("Generating solution code...")
    
    # Escape triple quotes
    safe_text = task_text.replace('"""', "'''")
    
    system_prompt = """
You are a Python Data Analyst.
Goal: Write a script to solve the user's question.

Environment:
- Python 3.10
- Libraries: pandas, numpy, requests, httpx, beautifulsoup4, pdfplumber, pytesseract, PIL, sklearn.
- Workdir: /app (You can save temp files here).

Rules:
1. Parse the `context` variable to understand the task.
2. If the task requires downloading a file (CSV, PDF, Image), use `requests` to download it to the current directory.
3. If it's a PDF, use `pdfplumber`. If it's an image, use `pytesseract`.
4. Calculate the ANSWER.
5. Identify the SUBMIT_URL from the text.
6. FINAL OUTPUT must be JSON printed to stdout:
   {"answer": <calculated_value>, "submit_url": "<url>"}
7. Do not print debug info to stdout.
    """
    
    user_prompt = f"context = \"\"\"{safe_text}\"\"\"\n\nWrite the script."

    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,  # <--- Updated to use variable
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )
        llm_output = response.choices[0].message.content
        
        # Extract code
        code = llm_output
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.split("```")[1].split("```")[0]
            
        return execute_and_parse(code.strip())

    except Exception as e:
        logger.error(f"Agent failed: {e}")
        return {"error": str(e)}

def execute_and_parse(code: str):
    filename = f"task_{uuid.uuid4().hex}.py"
    try:
        with open(filename, "w") as f:
            f.write(code)
            
        result = subprocess.run(
            [sys.executable, filename],
            capture_output=True,
            text=True,
            timeout=45
        )
        
        output = result.stdout
        
        if result.stderr:
            logger.info(f"Script stderr: {result.stderr}")

        matches = re.findall(r'\{.*\}', output, re.DOTALL)
        if matches:
            try:
                return json.loads(matches[-1])
            except:
                pass
        
        return {"error": "No JSON found", "raw": output, "stderr": result.stderr}

    except subprocess.TimeoutExpired:
        return {"error": "Script timed out"}
    except Exception as e:
        return {"error": f"Execution failed: {e}"}
    finally:
        if os.path.exists(filename):
            os.remove(filename)
