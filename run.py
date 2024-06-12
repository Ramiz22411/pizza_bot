import asyncio
import logging
from os import getenv
from dotenv import load_dotenv, find_dotenv

from aiogram.fsm.strategy import FSMStrategy
from aiogram.types import BotCommandScopeAllPrivateChats
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode

# from common.bot_commands import private

from app.handlers import router
from app.group_handler import group_router
from app.admin_private import admin_router

from database.engin import create_db, drop_db, session_maker
from middlewares.db import DatabaseSession

load_dotenv(find_dotenv())


# ALLOWED_UPDATES = ['message', 'edited_message']


async def on_startup(bot):
    # await drop_db()

    await create_db()


async def on_shutdown(bot):
    print('Bot shutdown')


async def main():
    bot = Bot(token=getenv('TOKEN'), parse_mode=ParseMode.HTML, )
    bot.my_admins_list = []
    dp = Dispatcher()

    dp.update.middleware(DatabaseSession(session_pool=session_maker))

    dp.include_router(router)
    dp.include_router(group_router)
    dp.include_router(admin_router)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    await bot.delete_webhook(drop_pending_updates=True)
    # await bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())
    # await bot.set_my_commands(commands=private, scope=BotCommandScopeAllPrivateChats())
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.error('Bot stopped')
