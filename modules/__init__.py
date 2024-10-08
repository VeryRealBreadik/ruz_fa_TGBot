from .bot.bot import Bot
from .ruz_fa_api.ruz_fa_api import RuzFaAPI


def load_ruz_fa_api():
    global ruz_fa_api

    ruz_fa_api = RuzFaAPI()

async def start_bot(bot_token, persistence_file_path):
    global ruz_fa_api

    bot = Bot(bot_token=bot_token, persistence_file_path=persistence_file_path, ruz_fa_api=ruz_fa_api)
    await bot.run()
