import asyncio
import json
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from config import TOKEN

# ========== ЗАГРУЗКА БАНВОРДОВ ИЗ JSON ==========
def load_banwords():
    try:
        with open("banwords.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            all_words = []
            for category in data.values():
                all_words.extend(category)
            all_words = [word.lower() for word in all_words]
            return all_words
    except FileNotFoundError:
        print("ERROR: banwords.json not found")
        return []
    except json.JSONDecodeError:
        print("ERROR: Invalid JSON format")
        return []

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = TOKEN
FORBIDDEN_WORDS = load_banwords()
deleted_counter = 0

print(f"Loaded {len(FORBIDDEN_WORDS)} forbidden words")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def contains_forbidden(text: str) -> bool:
    if not text:
        return False
    
    text_lower = text.lower()
    text_clean = re.sub(r'[^\w\sа-яё0-9@]', '', text_lower, flags=re.IGNORECASE)
    
    for word in FORBIDDEN_WORDS:
        if word in text_clean or word in text_lower:
            return True
    return False

# ========== СНАЧАЛА КОМАНДЫ ==========

# 1. Команда /start
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        f"Bot started\n\n"
        f"What I do:\n"
        f"1. ANY text message (except commands) -> delete and reply 'You forgot to attach an image'\n"
        f"2. Photo with forbidden words in caption -> delete (silent)\n"
        f"3. Commands are IGNORED\n\n"
        f"Statistics: /stats\n"
        f"Reload banwords: /reload (admins only)\n\n"
        f"Loaded {len(FORBIDDEN_WORDS)} forbidden words"
    )

# 2. Команда /stats
@dp.message(Command("stats"))
async def stats_command(message: Message):
    global deleted_counter
    text = f"Statistics\n\nDeleted messages: {deleted_counter}\nForbidden words: {len(FORBIDDEN_WORDS)}\nSince: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
    
    if message.chat.type == "private":
        await message.answer(text)
    else:
        await message.answer("Sending statistics to private chat...")
        await bot.send_message(message.from_user.id, text)

# 3. Команда /reload (только для админов)
@dp.message(Command("reload"))
async def reload_banwords(message: Message):
    global FORBIDDEN_WORDS
    
    if message.chat.type == "private":
        await message.answer("This command works only in groups")
        return
    
    try:
        chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if chat_member.status not in ["creator", "administrator"]:
            await message.answer("Only administrators can reload banwords")
            return
    except:
        await message.answer("Failed to check user permissions")
        return
    
    new_words = load_banwords()
    if new_words:
        FORBIDDEN_WORDS = new_words
        await message.answer(f"Banwords reloaded! Loaded {len(FORBIDDEN_WORDS)} words")
        print(f"Banwords reloaded by {message.from_user.first_name}")
    else:
        await message.answer("Failed to reload banwords. Check banwords.json file")

# ========== ПОТОМ ВСЁ ОСТАЛЬНОЕ ==========

# 4. ЛЮБЫЕ текстовые сообщения (не команды) -> удаляем и пишем
@dp.message(F.text)
async def handle_text(message: Message):
    global deleted_counter
    
    # Пропускаем, если это команда (начинается с /)
    if message.text.startswith('/'):
        return
    
    await message.delete()
    deleted_counter += 1
    await message.answer("Вы забыли прикрепить картинку")
    print(f"Deleted text from {message.from_user.first_name} | Total: {deleted_counter}")

# 5. Фото с подписью
@dp.message(F.photo & F.caption)
async def handle_photo_with_caption(message: Message):
    global deleted_counter
    
    if message.caption.startswith('/'):
        return
    
    if contains_forbidden(message.caption):
        await message.delete()
        deleted_counter += 1
        print(f"Deleted photo with bad caption from {message.from_user.first_name} | Total: {deleted_counter}")

# 6. Фото без подписи - ничего не делаем
@dp.message(F.photo & ~F.caption)
async def handle_photo_without_caption(message: Message):
    pass

# 7. Видео, документы с подписью
@dp.message((F.video | F.document | F.audio | F.voice) & F.caption)
async def handle_media_with_caption(message: Message):
    global deleted_counter
    
    if message.caption.startswith('/'):
        return
    
    if contains_forbidden(message.caption):
        await message.delete()
        deleted_counter += 1
        print(f"Deleted media with bad caption from {message.from_user.first_name} | Total: {deleted_counter}")

# ========== ЗАПУСК ==========
async def main():
    print("Bot started")
    print(f"Loaded {len(FORBIDDEN_WORDS)} forbidden words")
    print("Commands /start, /stats, /reload work")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())