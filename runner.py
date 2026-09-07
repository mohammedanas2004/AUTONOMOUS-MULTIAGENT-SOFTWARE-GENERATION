import asyncio
import sys
from orchestrator import Orchestrator
async def main():
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Build a simple task manager app"
    print(f"Running pipeline for: '{prompt}'...\n")
    orchestrator = Orchestrator()
    result = await orchestrator.execute(prompt)
    for log in result.logs:
        print(f"[{log.status}] {log.step}: {log.message}")
    print("\nPipeline finished. Check the generated_app directory.")
if __name__ == "__main__":
    asyncio.run(main())