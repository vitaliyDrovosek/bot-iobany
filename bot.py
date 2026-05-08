import os
import asyncio
import json
import re
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command

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
        print("ОШИБКА: banwords.json не найден")
        return []
    except json.JSONDecodeError:
        print("ОШИБКА: Неверный формат JSON")
        return []

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8638319855:AAEm2XGIRE-6Koo6ULo-_o51zgUCMySYrvM"

FORBIDDEN_WORDS = load_banwords()
deleted_counter = 0

print(f"Загружено {len(FORBIDDEN_WORDS)} запрещенных слов")

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

async def is_admin(message: Message) -> bool:
    """Проверяет, является ли пользователь администратором"""
    if message.chat.type == "private":
        return True
    
    try:
        chat_member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return chat_member.status in ["creator", "administrator"]
    except:
        return False

async def delete_message_later(chat_id: int, message_id: int, delay: int = 60):
    """Удаляет сообщение через указанное количество секунд"""
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except:
        pass

# ========== КОМАНДЫ ==========

@dp.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        f"Бот запущен\n\n"
        f"Что я делаю:\n"
        f"1. Любое текстовое сообщение от не-админов -> удаляю и пишу 'Забыл прикрепить картинку' (сообщение удалится через минуту)\n"
        f"2. Фото или видео с запрещенными словами в подписи от не-админов -> удаляю молча\n"
        f"3. Администраторы полностью игнорируются\n"
        f"4. Команды игнорируются\n\n"
        f"Статистика: /stats\n"
        f"Перезагрузить банворды: /reload (только админы)\n\n"
        f"Загружено {len(FORBIDDEN_WORDS)} запрещенных слов"
    )

@dp.message(Command("stats"))
async def stats_command(message: Message):
    global deleted_counter
    text = f"Статистика\n\nУдалено сообщений: {deleted_counter}\nЗапрещенных слов: {len(FORBIDDEN_WORDS)}\nС {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
    
    if message.chat.type == "private":
        await message.answer(text)
    else:
        await message.answer("Отправляю статистику в личные сообщения")
        await bot.send_message(message.from_user.id, text)

@dp.message(Command("reload"))
async def reload_banwords(message: Message):
    global FORBIDDEN_WORDS
    
    # Только для админов
    if not await is_admin(message):
        await message.answer("Только администраторы могут перезагружать банворды")
        return
    
    new_words = load_banwords()
    if new_words:
        FORBIDDEN_WORDS = new_words
        await message.answer(f"Банворды перезагружены! Загружено {len(FORBIDDEN_WORDS)} слов")
        print(f"Банворды перезагружены админом {message.from_user.first_name}")
    else:
        await message.answer("Не удалось перезагрузить банворды. Проверьте файл banwords.json")

# ========== УДАЛЕНИЕ СООБЩЕНИЙ ==========

@dp.message(F.text)
async def handle_text(message: Message):
    global deleted_counter
    
    # Пропускаем команды
    if message.text.startswith('/'):
        return
    
    # Пропускаем админов
    if await is_admin(message):
        return
    
    # Удаляем сообщение
    await message.delete()
    deleted_counter += 1
    
    # Отправляем ответ и удаляем его через минуту
    msg = await message.answer(f"{message.from_user.first_name}, вы забыли прикрепить картинку")
    asyncio.create_task(delete_message_later(msg.chat.id, msg.message_id, 60))
    
    print(f"Удален текст от {message.from_user.first_name} | Всего: {deleted_counter}")

@dp.message(F.photo & F.caption)
async def handle_photo_with_caption(message: Message):
    global deleted_counter
    
    # Пропускаем команды
    if message.caption.startswith('/'):
        return
    
    # Пропускаем админов
    if await is_admin(message):
        return
    
    # Проверяем наличие запрещенных слов
    if contains_forbidden(message.caption):
        await message.delete()
        deleted_counter += 1
        print(f"Удалено фото с плохой подписью от {message.from_user.first_name} | Всего: {deleted_counter}")

@dp.message(F.photo & ~F.caption)
async def handle_photo_without_caption(message: Message):
    # Фото без подписи - ничего не делаем
    pass

@dp.message((F.video | F.document | F.audio | F.voice) & F.caption)
async def handle_media_with_caption(message: Message):
    global deleted_counter
    
    # Пропускаем команды
    if message.caption.startswith('/'):
        return
    
    # Пропускаем админов
    if await is_admin(message):
        return
    
    # Проверяем наличие запрещенных слов
    if contains_forbidden(message.caption):
        await message.delete()
        deleted_counter += 1
        print(f"Удален медиафайл с плохой подписью от {message.from_user.first_name} | Всего: {deleted_counter}")

# ========== ЗАПУСК ==========
async def main():
    print("Бот запущен")
    print(f"Загружено {len(FORBIDDEN_WORDS)} запрещенных слов")
    print("Команды: /start, /stats, /reload")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())