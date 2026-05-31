from __future__ import annotations

import logging

from aiogram import Router, types
from aiogram.filters import Command

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def handle_start(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    text = (
        "📚 <b>ExamBot — шпаргалки для ОГЭ и ЕГЭ</b>\n\n"
        "Отправь /shpora <b>тема</b> и я сгенерирую краткую шпаргалку.\n\n"
        "<b>Примеры:</b>\n"
        "• /shpora квадратные уравнения\n"
        "• /shpora падежи в русском языке\n"
        "• /shpora теорема Пифагора\n"
        "• /shpora 1 закон Ньютона\n\n"
        "📊 <b>5 шпаргалок в день — бесплатно</b>\n"
        "💎 /subscribe — снять лимит"
    )
    await message.answer(text)


@router.message(Command("subscribe"))
async def handle_subscribe(message: types.Message) -> None:
    text = (
        "💎 <b>ExamBot Premium</b>\n\n"
        "— Безлимитные шпаргалки\n"
        "— Приоритетная генерация\n"
        "— (в будущем) своя база знаний\n\n"
        "💰 <b>50⭐ Telegram Stars / месяц</b>\n\n"
        "📩 Для покупки напиши администратору:"
    )
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="📩 Написать администратору",
                    url="https://t.me/born3life",
                ),
            ],
        ],
    )
    await message.answer(text, reply_markup=kb)
