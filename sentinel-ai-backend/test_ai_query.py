import asyncio
from app.services.grc_engine.understanding_service import understand
from app.services.llm_service import LLMService

async def run_test():
    llm = LLMService()
    
    question = "Which vendors have contracts expiring soon?"
    print(f"Testing Question: {question}")
    
    plan = await understand(question, llm=llm)
    
    if plan is None:
        print("Error: understand() returned None (failed to generate or validate JSON)")
    else:
        print("Generated Plan:")
        print(plan.model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(run_test())
