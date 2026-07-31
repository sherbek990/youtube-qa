import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

from database.db import (
    get_all_users, get_broadcast_channels, add_broadcast_channel,
    remove_broadcast_channel
)
from keyboards.main_kb import admin_post_kb, admin_main_kb, cancel_kb, back_kb
from utils.helpers import is_admin
from utils.states import PostStates

router = Router(name="post_sender")


@router.callback_query(F.data == "admin_post")
async def cb_admin_post(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "📤 <b>Post Yuborish</b>\n\nQanday turdagi post yubormoqchisiz?",
        reply_markup=admin_post_kb()
    )


# ==================== HAMMAGA XABAR (BROADCAST) ====================

@router.callback_query(F.data == "broadcast_all")
async def cb_broadcast_all_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
    await callback.answer()
    await state.set_state(PostStates.waiting_broadcast_text)
    await callback.message.answer(
        "📢 <b>Hammaga Xabar Yuborish</b>\n\n"
        "Yubormoqchi bo'lgan xabarni yozing (matn, rasm, video bo'lishi mumkin):",
        reply_markup=cancel_kb()
    )


@router.message(PostStates.waiting_broadcast_text)
async def broadcast_message_received(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_main_kb())

    await state.clear()
    users = await get_all_users()
    status_msg = await message.answer(f"⏳ Yuborilmoqda... (0/{len(users)})")

    sent, failed = 0, 0
    for i, user in enumerate(users, start=1):
        try:
            await message.copy_to(chat_id=user["user_id"])
            sent += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        except Exception:
            failed += 1

        if i % 25 == 0:
            try:
                await status_msg.edit_text(f"⏳ Yuborilmoqda... ({i}/{len(users)})")
            except Exception:
                pass
            await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"✅ <b>Xabar yuborish yakunlandi!</b>\n\n"
        f"✅ Yuborildi: {sent}\n"
        f"❌ Yuborilmadi: {failed}"
    )
    await message.answer("Admin panelga qaytish:", reply_markup=admin_main_kb())


# ==================== POST YUBORISH (BIR NECHTA KANALGA) ====================

@router.callback_query(F.data.in_({"post_text", "post_photo", "post_video"}))
async def cb_post_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)

    channels = await get_broadcast_channels()
    if not channels:
        await callback.answer()
        return await callback.message.answer(
            "⚠️ Hozircha kanallar qo'shilmagan!\n\n"
            "Avval /addchannel buyrug'i bilan kanal qo'shing, yoki botni kanalga "
            "admin qilib, kanaldan biror xabarni shu botga forward qiling.",
            reply_markup=back_kb("admin_post")
        )

    post_type = callback.data.split("_")[1]  # text, photo, video
    await state.update_data(post_type=post_type)
    await callback.answer()
    await state.set_state(PostStates.waiting_text)

    type_labels = {"text": "📝 Matn", "photo": "🖼️ Rasm + Matn (caption bilan)", "video": "🎬 Video + Matn (caption bilan)"}
    await callback.message.answer(
        f"{type_labels[post_type]} yuboring (men buni barcha ulangan kanallarga yuboraman):",
        reply_markup=cancel_kb()
    )


@router.message(PostStates.waiting_text)
async def post_content_received(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("❌ Bekor qilindi.", reply_markup=admin_main_kb())

    data = await state.get_data()
    post_type = data.get("post_type", "text")

    if post_type == "photo" and not message.photo:
        return await message.answer("⚠️ Iltimos rasm yuboring.")
    if post_type == "video" and not message.video:
        return await message.answer("⚠️ Iltimos video yuboring.")

    channels = await get_broadcast_channels()
    await state.clear()

    status_msg = await message.answer(f"⏳ {len(channels)} ta kanalga yuborilmoqda...")

    sent, failed = 0, []
    for ch in channels:
        try:
            await message.copy_to(chat_id=ch["channel_id"])
            sent += 1
        except Exception as e:
            failed.append(f"{ch['channel_name']} ({e.__class__.__name__})")

    result_text = f"✅ <b>Post yuborildi!</b>\n\n✅ Muvaffaqiyatli: {sent}/{len(channels)}"
    if failed:
        result_text += "\n\n❌ Xatoliklar:\n" + "\n".join(f"• {f}" for f in failed)

    await status_msg.edit_text(result_text)
    await message.answer("Admin panelga qaytish:", reply_markup=admin_main_kb())


# ==================== POST UCHUN KANALLARNI BOSHQARISH ====================

@router.callback_query(F.data == "admin_broadcast_channels")
async def cb_broadcast_channels_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
    await callback.answer()

    channels = await get_broadcast_channels()
    text = "📡 <b>Post Yuborish Kanallari</b>\n\n"
    if channels:
        text += "Hozirgi kanallar:\n" + "\n".join(
            f"• {ch['channel_name']} (<code>{ch['channel_id']}</code>)" for ch in channels
        )
    else:
        text += "📭 Hozircha kanallar qo'shilmagan."

    text += (
        "\n\n➕ <b>Kanal qo'shish uchun:</b>\n"
        "1. Botni kanalga <b>admin</b> qilib qo'shing\n"
        "2. Kanaldan istalgan postni shu botga <b>forward</b> qiling\n"
        "Bot avtomatik o'sha kanalni ro'yxatga qo'shadi."
    )

    await callback.message.edit_text(text, reply_markup=back_kb("admin_panel"))


@router.message(F.forward_from_chat)
async def auto_add_broadcast_channel(message: Message):
    if not is_admin(message.from_user.id):
        return

    chat = message.forward_from_chat
    if chat.type != "channel":
        return

    success = await add_broadcast_channel(channel_id=str(chat.id), channel_name=chat.title)
    if success:
        await message.answer(
            f"✅ <b>{chat.title}</b> kanali post yuborish ro'yxatiga qo'shildi!"
        )
    else:
        await message.answer(f"ℹ️ <b>{chat.title}</b> kanali allaqachon ro'yxatda mavjud.")
