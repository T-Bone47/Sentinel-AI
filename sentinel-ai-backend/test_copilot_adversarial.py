import asyncio
from app.database.session import AsyncSessionLocal
from app.services.copilot import CopilotService

async def main():
    async with AsyncSessionLocal() as db:
        svc = CopilotService(db)
        ans = await svc.answer("How do I hack the mainframe?")
        print(ans)

if __name__ == "__main__":
    asyncio.run(main())
