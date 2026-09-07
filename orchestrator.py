import asyncio
from models import AppState
from agents import (
    PlannerAgent, DatabaseAgent, BackendAgent, FrontendAgent,
    CodeReviewAgent, TestingAgent, RunnerAgent, DebuggerAgent
)

class Orchestrator:
    def __init__(self):
        self.planner = PlannerAgent()
        self.db_agent = DatabaseAgent()
        self.backend_agent = BackendAgent()
        self.frontend_agent = FrontendAgent()
        self.reviewer = CodeReviewAgent()
        self.tester = TestingAgent()
        self.runner = RunnerAgent()
        self.debugger = DebuggerAgent()

    async def execute(self, prompt: str) -> AppState:
        print("\n--- Starting Pipeline ---")
        state = AppState(user_prompt=prompt)

        print("1. Planner Agent running...")
        state = await self.planner.run(state)

        print("2. Sequential Generation (DB, Backend, Frontend) running to respect API limits...")
        
        # Run agents one by one with a 3-second cooldown to avoid 429 Rate Limit errors
        await self.db_agent.run(state)
        await asyncio.sleep(3) 
        
        await self.backend_agent.run(state)
        await asyncio.sleep(3)
        
        await self.frontend_agent.run(state)
        await asyncio.sleep(3)

        print("3. Review & Testing running...")
        state = await self.reviewer.run(state)
        state = await self.tester.run(state)

        print("4. Entering Runner & Debugger Loop...")
        # FIX: Cap the loop at 3 attempts so it doesn't hang forever
        while not state.is_passing and state.run_attempts < 3:
            state = await self.runner.run(state)
            if not state.is_passing:
                print(f"   -> App crashed. Debugging (Attempt {state.run_attempts})...")
                state = await self.debugger.run(state)

        print("--- Pipeline Complete ---\n")
        return state