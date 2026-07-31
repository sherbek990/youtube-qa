from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from database.db import add_user, get_setting, get_users_count
from keyboards.main_kb import main_menu_kb
from utils.helpers import is_admin

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await add_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    welcome_text = await get_setting(
        "welcome_text",
        "🎌 <b>Anime Botga Xush Kelibsiz!</b>\n\nEng yaxshi anime seriallarini tomosha qiling."
    )

    await message.answer(welcome_text, reply_markup=main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "ℹ️ <b>Yordam</b>\n\n"
        "🎬 Animalar — barcha anime ro'yxatini ko'rish\n"
        "🔍 Qidirish — anime nomi bo'yicha qidirish\n"
        "⚙️ Sozlamalar — shaxsiy sozlamalar\n"
    )
    if is_admin(message.from_user.id):
        text += "\n👑 /admin — Admin panelga kirish"
    await message.answer(text)


@router.message(Command("admin"))
async def cmd_admin_shortcut(message: Message):
    if not is_admin(message.from_user.id):
        return
    from keyboards.main_kb import admin_main_kb
    await message.answer("👑 <b>Admin Panel</b>", reply_markup=admin_main_kb())


@router.message(F.text == "📊 Statistika")
async def user_stats(message: Message):
    count = await get_users_count()
    await message.answer(f"📊 Botda jami <b>{count}</b> ta foydalanuvchi bor.")
