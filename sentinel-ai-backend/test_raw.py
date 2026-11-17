import asyncio
from app.services.llm_service import LLMService

async def run_test():
    llm = LLMService()
    res = await llm.complete_structured("You are a bot. Return JSON.", "hi", max_tokens=900)
    print("RAW:")
    print(res)

if __name__ == "__main__":
    asyncio.run(run_test())
