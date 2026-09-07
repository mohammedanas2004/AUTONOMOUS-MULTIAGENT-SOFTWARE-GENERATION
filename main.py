from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from models import PromptRequest, AppState
from orchestrator import Orchestrator
from database import db

app = FastAPI(title="Multi-Agent Pipeline Engine")
orchestrator = Orchestrator()

@app.on_event("startup")
async def startup_db_client():
    await db.command("ping")

@app.get("/api/health")
async def health_check():
    return {"message": "Connected to local MongoDB Compass"}

@app.get("/", response_class=HTMLResponse)
async def serve_browser_ui():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Multi-Agent Orchestrator</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; background: #121212; color: #e0e0e0; }
            .container { max-width: 900px; margin: auto; }
            input[type=text] { width: 75%; padding: 12px; border-radius: 6px; border: 1px solid #333; background: #1e1e1e; color: #fff; }
            button { padding: 12px 20px; border-radius: 6px; border: none; background: #3b82f6; color: #fff; font-weight: bold; cursor: pointer; }
            button:hover { background: #2563eb; }
            .terminal { background: #18181b; border: 1px solid #27272a; padding: 20px; border-radius: 8px; margin-top: 20px; font-family: monospace; white-space: pre-wrap; font-size: 13px; }
            .badge-SUCCESS { color: #4ade80; }
            .badge-FAIL { color: #f87171; }
            .badge-FIX { color: #facc15; }
            .badge-PASS { color: #38bdf8; }
            .code-panel { background: #09090b; border: 1px solid #27272a; padding: 15px; border-radius: 6px; margin-top: 15px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Multi-Agent System Console</h2>
            <div>
                <input id="promptInput" type="text" placeholder="Enter user prompt (e.g., 'Build an order management API')..."/>
                <button onclick="runPipeline()">Run Pipeline</button>
            </div>
            
            <div id="logs" class="terminal" style="display:none;"></div>
            
            <div id="result" class="terminal" style="display:none;">
                <h3>Working Application Delivered to Browser</h3>
                <div id="appContainer" class="code-panel"></div>
            </div>
        </div>

        <script>
            async function runPipeline() {
                const prompt = document.getElementById('promptInput').value || 'Build a simple web app';
                const logBox = document.getElementById('logs');
                const resultBox = document.getElementById('result');
                const appContainer = document.getElementById('appContainer');

                logBox.style.display = 'block';
                resultBox.style.display = 'none';
                logBox.innerHTML = 'Sending prompt to Orchestrator...\\n';

                const response = await fetch('/api/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt })
                });

                const data = await response.json();
                
                logBox.innerHTML = '';
                data.logs.forEach(log => {
                    logBox.innerHTML += `[<span class="badge-${log.status}">${log.status}</span>] <strong>${log.step}</strong>: ${log.message}\\n`;
                });

                resultBox.style.display = 'block';
                appContainer.innerHTML = `
                    <p><strong>DB Schema:</strong></p><pre>${data.db_code}</pre>
                    <p><strong>Backend Endpoint:</strong></p><pre>${data.backend_code}</pre>
                    <p><strong>Frontend UI:</strong></p><pre>${data.frontend_code}</pre>
                    <p><strong>Live App State:</strong> ${data.working_application}</p>
                `;
            }
        </script>
    </body>
    </html>
    """

@app.post("/api/run", response_model=AppState)
async def run_pipeline(request: PromptRequest):
    result_state = await orchestrator.execute(request.prompt)
    return result_state