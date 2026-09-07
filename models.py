from pydantic import BaseModel
from typing import Optional, List, Dict

class PromptRequest(BaseModel):
    prompt: str

class PipelineLog(BaseModel):
    step: str
    message: str
    status: str

class AppState(BaseModel):
    user_prompt: str
    plan: Optional[Dict[str, str]] = None
    db_code: str = ""
    backend_code: str = ""
    frontend_code: str = ""
    review_comments: str = ""
    test_results: str = ""
    run_output: str = ""
    is_passing: bool = False
    run_attempts: int = 0
    logs: List[PipelineLog] = []
    working_application: str = ""