import os
import json
import re
import subprocess
import sys
import uuid
import logging
from openai import OpenAI
from config import API_KEY, OPENAI_BASE_URL

logger = logging.getLogger("uvicorn")

client = OpenAI(api_key=API_KEY, base_url=OPENAI_BASE_URL)

def solve_challenge(task_text: str):
    """
    1. Ask LLM to write code based on task_text.
    2. Execute code.
    3. Parse JSON output.
    """
    logger.info("Generating solution code...")
    
    # Escape triple quotes to prevent syntax errors in the prompt
    safe_text = task_text.replace('"""', "'''")
    
    system_prompt = """
You are a Python Data Analyst. 
Your goal: Write a Python script to solve the user's question.

Rules:
1. The user's task description is in the variable `context`. Parse it.
2. If the task involves a URL (CSV/API), use `httpx` or `pandas` to fetch it.
3. Compute the answer.
4. FINAL OUTPUT MUST be a valid JSON string printed to stdout:
   {"answer": <calculated_value>, "submit_url": "<url_to_submit>"}
5. Do NOT print anything else to stdout.
    """
    
    user_prompt = f"context = \"\"\"{safe_text}\"\"\"\n\nWrite the script."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Use mini to save cost, switch to gpt-4o if needed
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )
        llm_output = response.choices[0].message.content
        
        # Extract code block
        code = llm_output
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0]
        elif "```" in code:
            code = code.replace("```", "")
            
        return execute_and_parse(code.strip())

    except Exception as e:
        logger.error(f"Agent failed: {e}")
        return {"error": str(e)}

def execute_and_parse(code: str):
    filename = f"task_{uuid.uuid4().hex}.py"
    try:
        with open(filename, "w") as f:
            f.write(code)
            
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
            return json.loads(matches[-1])
        
        return {"error": "No JSON found in output", "raw": output}

    except Exception as e:
        return {"error": f"Execution failed: {e}"}
    finally:
        if os.path.exists(filename):
            os.remove(filename)
