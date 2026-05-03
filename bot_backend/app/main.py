import asyncio
from .db import init_db
from .telegram_bot import run_bot


async def main() -> None:
    await init_db()
    await run_bot()


if __name__ == '__main__':
    asyncio.run(main())
