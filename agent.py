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
You are a Python Data Analyst expert at solving quiz tasks.
Your goal: Write a COMPLETE Python script to solve the user's question.

CRITICAL RULES:
1. The task description is in the variable `context`. CAREFULLY READ AND PARSE IT.
2. The task may include:
   - Instructions to download/fetch data from URLs (CSV, PDF, API, web pages)
   - Data processing requirements (cleaning, filtering, aggregating)
   - A submission URL where you need to POST the answer
3. Use appropriate libraries: `httpx` for HTTP requests, `pandas` for CSV/data, `beautifulsoup4` for HTML parsing
4. If the task involves scraping a webpage, extract the ACTUAL CONTENT/INSTRUCTIONS from the HTML
5. Extract ONLY the submit URL (just the URL, nothing else)
6. Calculate ONLY the answer requested - not the entire submission payload
7. YOUR FINAL OUTPUT MUST BE EXACTLY THIS JSON FORMAT printed to stdout:
   {"answer": <your_calculated_answer>, "submit_url": "<url_only>"}
8. The "answer" field should contain ONLY the calculated result
9. The "submit_url" field should contain ONLY the URL - no examples, no extra text
10. DO NOT print anything else to stdout except the final JSON
11. Handle errors gracefully and make reasonable assumptions if data is unclear

EXAMPLES OF CORRECT OUTPUT:
✓ {"answer": 12345, "submit_url": "http://example.com/submit"}
✓ {"answer": 4, "submit_url": "http://example.com/submit"}
✓ {"answer": "hello world", "submit_url": "http://example.com/submit"}

EXAMPLES OF INCORRECT OUTPUT:
✗ {"answer": {"email": "...", "secret": "...", "answer": 12345}, ...}
✗ {"answer": "hello", "submit_url": "http://example.com/submit\n{...example...}"}
✗ {"answer": {"answer": "hello world"}, ...}

Remember: 
- answer = ONLY the direct answer value
- submit_url = ONLY the URL, nothing after it
"""
    
    user_prompt = f"""context = '''{safe_text}'''

Write a complete Python script to solve this task. Remember:
- Parse the context carefully to understand what's being asked
- Extract the submission URL from the context
- Calculate/fetch the required answer
- Output ONLY the JSON: {{"answer": <result>, "submit_url": "<url>"}}
"""

    # Try each API in order until one succeeds
    for idx, config in enumerate(API_CONFIGS):
        try:
            logger.info(f"Attempting with {config['name']} API (attempt {idx + 1}/{len(API_CONFIGS)})")
            
            client = OpenAI(
                api_key=config["api_key"],
                base_url=config["base_url"],
                timeout=60.0,  # Increased timeout
                max_retries=2  # Reduced retries to fail faster
            )
            
            response = client.chat.completions.create(
                model=config["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1  # Slightly higher for better reasoning
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
            error_msg = str(e)
            logger.warning(f"✗ {config['name']} API failed: {error_msg}")
            
            # If this was the last API, return the error
            if idx == len(API_CONFIGS) - 1:
                logger.error("All APIs failed!")
                return {"error": f"All APIs failed. Last error: {error_msg}"}
            
            # Otherwise, continue to next API
            logger.info(f"Falling back to next API...")
            continue

def execute_and_parse(code: str):
    filename = f"task_{uuid.uuid4().hex}.py"
    try:
        # Add error handling wrapper to the code
        wrapped_code = f"""
import sys
import traceback

try:
{chr(10).join('    ' + line for line in code.split(chr(10)))}
except Exception as e:
    print('{{"error": "Script execution error: ' + str(e).replace('"', "'") + '"}}', file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
"""
        
        with open(filename, "w") as f:
            f.write(wrapped_code)
        
        logger.info(f"Executing generated script: {filename}")
        
        # Run the script
        result = subprocess.run(
            [sys.executable, filename],
            capture_output=True,
            text=True,
            timeout=45  # Increased timeout for data processing
        )
        
        output = result.stdout.strip()
        stderr = result.stderr.strip()
        
        if stderr:
            logger.warning(f"Script stderr: {stderr}")
        
        if not output:
            logger.error("Script produced no output")
            return {"error": "Script produced no output", "stderr": stderr}

        # Robust JSON Extraction using Regex
        # Looks for the last occurrence of {...}
        matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', output, re.DOTALL)
        
        if matches:
            try:
                parsed = json.loads(matches[-1])
                
                # Clean the submit_url if it has extra text
                if "submit_url" in parsed and isinstance(parsed["submit_url"], str):
                    # Extract just the URL part (everything before newline or whitespace block)
                    url = parsed["submit_url"].split('\n')[0].strip()
                    # Remove any trailing JSON-like characters
                    url = url.rstrip('{ \t\n\r')
                    parsed["submit_url"] = url
                
                logger.info(f"Parsed result: {parsed}")
                return parsed
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error: {e}")
                logger.error(f"Attempted to parse: {matches[-1][:200]}")
        
        logger.error(f"No valid JSON found in output: {output[:500]}")
        return {"error": "No valid JSON found in output", "raw": output[:1000]}

    except subprocess.TimeoutExpired:
        logger.error("Script execution timeout")
        return {"error": "Script execution timeout (45s)"}
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return {"error": f"Execution failed: {e}"}
    finally:
        if os.path.exists(filename):
            os.remove(filename)
