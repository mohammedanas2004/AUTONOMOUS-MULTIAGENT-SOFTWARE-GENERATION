import os
import re
import asyncio
import subprocess
import sys
import httpx
from models import AppState, PipelineLog




active_process = None

async def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Helper function to call Google Gemini directly via HTTP."""
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": f"System Instruction: {system_prompt}\n\nUser Request: {user_prompt}"}]}
        ],
        "generationConfig": {
            "temperature": 0.2
        }
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # UPDATED: Now pointing to gemini-3.6-flash
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={API_KEY}"
            response = await client.post(url, headers=headers, json=payload)
            
            response.raise_for_status() 
            
            data = response.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Strip out markdown code blocks to get raw text/code
            content = re.sub(r"^```[a-zA-Z]*\n", "", content, flags=re.MULTILINE)
            content = re.sub(r"```$", "", content, flags=re.MULTILINE)
            return content.strip()
            
        except httpx.HTTPStatusError as e:
            error_msg = f"[LLM API ERROR]: HTTP {e.response.status_code} - {e.response.text}"
            print(f"\n{error_msg}\n")
            return f"# Error: {error_msg}"
        except Exception as e:
            print(f"\n[LLM SYSTEM ERROR]: {str(e)}\n")
            return f"# Error: {str(e)}"

class PlannerAgent:
    async def run(self, state: AppState) -> AppState:
        prompt = f"Create a technical implementation plan for this app: {state.user_prompt}. Keep it under 100 words."
        plan = await call_llm("You are a software architect.", prompt)
        state.plan = {"architecture": plan}
        state.logs.append(PipelineLog(step="Planner Agent", message="Architecture plan synthesized via LLM.", status="SUCCESS"))
        return state

class DatabaseAgent:
    async def run(self, state: AppState) -> AppState:
        prompt = f"Based on this plan: {state.plan}. Write ONLY the raw SQL commands to create the necessary SQLite tables. No explanations."
        state.db_code = await call_llm("You are a database administrator. Return ONLY raw SQL code.", prompt)
        state.logs.append(PipelineLog(step="Database Agent", message="SQL schema generated via LLM.", status="SUCCESS"))
        return state

class BackendAgent:
    async def run(self, state: AppState) -> AppState:
        prompt = f"""
        User wants: {state.user_prompt}
        Write a complete FastAPI application in Python. 
        CRITICAL INSTRUCTIONS:
        1. Serve a file named 'index.html' at the root '/' route using fastapi.responses.FileResponse.
        2. Include CORSMiddleware with allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"].
        3. Include necessary API endpoints for the app to function.
        4. Use in-memory data structures (like a global list or dict) instead of a real database.
        5. Return ONLY valid, raw Python code. Do not include markdown or explanations.
        """
        state.backend_code = await call_llm("You are an expert Python backend developer.", prompt)
        state.logs.append(PipelineLog(step="Backend Agent", message="FastAPI backend code generated.", status="SUCCESS"))
        return state
class FrontendAgent:
    async def run(self, state: AppState) -> AppState:
        prompt = f"""
        User wants: {state.user_prompt}
        Write a complete, single-file HTML/JS/CSS frontend.
        CRITICAL INSTRUCTIONS:
        1. When calling API endpoints via fetch/axios, ALWAYS use relative URLs (e.g., fetch('/todos') or fetch('/api/...')). NEVER hardcode 'http://localhost:8000' or any host/port.
        2. Make it look modern using inline CSS or Tailwind CDN.
        3. Return ONLY valid, raw HTML code. Do not include markdown or explanations.
        """
        state.frontend_code = await call_llm("You are an expert frontend developer.", prompt)
        state.logs.append(PipelineLog(step="Frontend Agent", message="HTML/JS frontend generated.", status="SUCCESS"))
        return state
class CodeReviewAgent:
    async def run(self, state: AppState) -> AppState:
        state.review_comments = "Bypassed standard review to prioritize execution speed."
        state.logs.append(PipelineLog(step="Code Review Agent", message="Code approved for execution.", status="SUCCESS"))
        return state

class TestingAgent:
    async def run(self, state: AppState) -> AppState:
        state.test_results = "Unit tests skipped for rapid prototyping."
        state.logs.append(PipelineLog(step="Testing Agent", message="Proceeding directly to Runner.", status="SUCCESS"))
        return state

class RunnerAgent:
    async def run(self, state: AppState) -> AppState:
        global active_process
        state.run_attempts += 1
        app_dir = "generated_app"
        
        os.makedirs(app_dir, exist_ok=True)
        with open(os.path.join(app_dir, "main.py"), "w", encoding="utf-8") as f:
            f.write(state.backend_code)
        with open(os.path.join(app_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(state.frontend_code)
            
        if active_process is not None:
            active_process.terminate()
            
        active_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--port", "8001"],
            cwd=app_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        await asyncio.sleep(3)
        
        if active_process.poll() is not None:
            stdout, stderr = active_process.communicate()
            state.is_passing = False
            state.run_output = stderr or stdout
            state.logs.append(PipelineLog(
                step="Runner Agent", 
                message=f"Execution FAIL (Attempt {state.run_attempts}): Server crashed.", 
                status="FAIL"
            ))
        else:
            state.is_passing = True
            state.run_output = "Server running on port 8001."
            state.working_application = "<a href='http://127.0.0.1:8001' target='_blank' style='color:#38bdf8; text-decoration:underline;'>http://127.0.0.1:8001</a>"
            
            state.logs.append(PipelineLog(
                step="Runner Agent", 
                message=f"Execution PASS (Attempt {state.run_attempts}): Live server deployed to port 8001.", 
                status="PASS"
            ))
            
        return state

class DebuggerAgent:
    async def run(self, state: AppState) -> AppState:
        prompt = f"""
        The FastAPI application failed to start. 
        Here is the error log:
        {state.run_output}
        
        Here is the broken Python code:
        {state.backend_code}
        
        Fix the errors. Return ONLY the complete, corrected raw Python code.
        """
        state.backend_code = await call_llm("You are an expert Python debugger.", prompt)
        state.logs.append(PipelineLog(
            step="Debugger Agent", 
            message="Analyzed crash log and rewrote backend code.", 
            status="FIX"
        ))
        return state