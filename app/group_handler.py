from string import punctuation

from aiogram import F, Router, Bot, types
from aiogram.types import Message
from aiogram.filters import Command

from filters.chat_types import ChatTypeFilter
from common.restricted_words import restricted_words

group_router = Router()
group_router.message.filter(ChatTypeFilter(["group", "supergroup"]))
group_router.edited_message.filter(ChatTypeFilter(["group", "supergroup"]))


@group_router.message(Command('admin'))
async def get_admins(message: Message, bot: Bot):
    chat_id = message.chat.id
    admins_list = await bot.get_chat_administrators(chat_id)

    admins_list = [
        member.user.id
        for member in admins_list
        if member.status == 'creator' or member.status == 'administrator'
    ]

    bot.my_admins_list = admins_list
    if message.from_user.id in admins_list:
        await message.delete()


def clean_text(text: str):
    return text.translate(str.maketrans('', '', punctuation))


@group_router.edited_message()
@group_router.message()
async def cleaner(message: Message):
    if restricted_words.intersection(clean_text(message.text.lower()).split()):
        await message.answer(f'{message.from_user.username}, Соблюдайте порядок в чате')
        await message.delete()
