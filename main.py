import os
import asyncio

from dotenv import load_dotenv

from modules import start_bot, load_ruz_fa_api


load_dotenv("essentials/.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
PERSISTENCE_FILE_PATH = os.getenv("PERSISTENCE_FILE_PATH")

load_ruz_fa_api()


async def main():
    await start_bot(BOT_TOKEN, PERSISTENCE_FILE_PATH)

    stop_event = asyncio.Event()
    await stop_event.wait()

if __name__ == "__main__":
    asyncio.run(main())
