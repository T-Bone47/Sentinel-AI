import httpx
import asyncio

async def run():
    async with httpx.AsyncClient() as client:
        res = await client.get("https://generativelanguage.googleapis.com/v1beta/models?key=dummy_key")
        print([m["name"] for m in res.json().get("models", [])])

asyncio.run(run())
