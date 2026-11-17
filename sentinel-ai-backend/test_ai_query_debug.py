import asyncio
from app.services.grc_engine.understanding_service import _build_system_prompt, _strip_fences
from app.services.llm_service import LLMService

async def run_test():
    llm = LLMService()
    question = "Which vendors have contracts expiring soon?"
    user_message = f"QUESTION: {question}"
    
    print("Calling LLM...")
    raw = await llm.complete_structured(_build_system_prompt(), user_message, max_tokens=900)
    print("RAW OUTPUT:")
    print(raw)
    
    print("\nSTRIPPED OUTPUT:")
    print(_strip_fences(raw or ""))

if __name__ == "__main__":
    asyncio.run(run_test())
