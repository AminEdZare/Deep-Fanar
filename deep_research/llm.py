import asyncio, os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from tavily import TavilyClient

load_dotenv()
FANAR_API_KEY = os.getenv("FANAR_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

tavily_client = TavilyClient(TAVILY_API_KEY)

fanar_client = AsyncOpenAI(
    base_url="https://api.fanar.qa/v1",
    api_key=FANAR_API_KEY,
)

MODEL = "Fanar"
MAX_CONCURRENT = 10              # keep ≤ your “concurrent requests” quota
sem = asyncio.Semaphore(MAX_CONCURRENT)

async def ask(system_prompt: str, user_prompt: str) -> str:
    async with sem:              # blocks when too many in‑flight calls
        resp = await fanar_client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}],
        )
    return resp.choices[0].message.content