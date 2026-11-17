import asyncio
from app.services.llm_service import LLMService

async def test():
    svc = LLMService()
    print("LLM Configured:", svc.is_configured)
    
    result = await svc.explain(
        deterministic_result={"answer": "The trust score is 85.", "supporting_data": [], "related_entities": [], "recommendations": []},
        question="What is the trust score?"
    )
    print("LLM Response:")
    print(result)

if __name__ == "__main__":
    asyncio.run(test())
