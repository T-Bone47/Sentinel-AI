import httpx
import asyncio

async def run():
    async with httpx.AsyncClient() as c:
        res = await c.post("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", headers={"Authorization": "Bearer dummy_key", "Content-Type": "application/json"}, json={"model": "gemini-3.5-flash", "messages": [{"role": "user", "content": "Say hi"}], "max_tokens": 100})
        print(res.json())

asyncio.run(run())
