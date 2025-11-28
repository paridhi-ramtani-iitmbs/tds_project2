import os
import json
import re
import subprocess
import sys
import uuid
import logging
from openai import OpenAI
from config import API_CONFIGS

logger = logging.getLogger("uvicorn")

def solve_challenge(task_text: str):
    """
    1. Ask LLM to write code based on task_text with fallback support.
    2. Execute code.
    3. Parse JSON output.
    """
    logger.info("Generating solution code...")
    
    # Escape triple quotes to prevent syntax errors in the prompt
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
2. The `context` contains the TEXT of the webpage.
3. EXTRACT the question and any URLs from the `context`. 
4. DO NOT INVENT URLS. If a URL is not in the context, do not use it.
5. If the task requires downloading a file (CSV, PDF, Image), use `requests` to download it.
6. Calculate the ANSWER.
7. FINAL OUTPUT must be JSON printed to stdout:
   {"answer": <calculated_value>, "submit_url": "<url_found_in_context>"}
8. Do not print debug info to stdout.
    """
    
    user_prompt = f"context = \"\"\"{safe_text}\"\"\"\n\nWrite the script."

    # Try each API in order until one succeeds
    for idx, config in enumerate(API_CONFIGS):
        try:
            logger.info(f"Attempting with {config['name']} API (attempt {idx + 1}/{len(API_CONFIGS)})")
            
            client = OpenAI(
                api_key=config["api_key"],
                base_url=config["base_url"]
            )
            
            response = client.chat.completions.create(
                model=config["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0
            )
            
            llm_output = response.choices[0].message.content
            logger.info(f"✓ {config['name']} API succeeded!")
            
            # Extract code block
            code = llm_output
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0]
            elif "```" in code:
                code = code.replace("```", "")
                
            return execute_and_parse(code.strip())

        except Exception as e:
            logger.warning(f"✗ {config['name']} API failed: {e}")
            
            # If this was the last API, return the error
            if idx == len(API_CONFIGS) - 1:
                logger.error("All APIs failed!")
                return {"error": f"All APIs failed. Last error: {str(e)}"}
            
            # Otherwise, continue to next API
            logger.info(f"Falling back to next API...")
            continue

def execute_and_parse(code: str):
    filename = f"task_{uuid.uuid4().hex}.py"
    try:
        with open(filename, "w") as f:
            f.write(code)
        
        logger.info(f"Executing generated script: {filename}")
        
        # Run the script
        result = subprocess.run(
            [sys.executable, filename],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout
        if result.stderr:
            logger.warning(f"Script stderr: {result.stderr}")

        # Robust JSON Extraction using Regex
        # Looks for the last occurrence of {...}
        matches = re.findall(r'\{.*\}', output, re.DOTALL)
        if matches:
            parsed = json.loads(matches[-1])
            logger.info(f"Parsed result: {parsed}")
            return parsed
        
        logger.error(f"No JSON found in output: {output}")
        return {"error": "No JSON found in output", "raw": output}

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return {"error": f"Execution failed: {e}"}
    finally:
        if os.path.exists(filename):
            os.remove(filename)
