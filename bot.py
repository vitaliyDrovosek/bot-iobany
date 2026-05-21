import os
import asyncio
import json
import re
from collections import Counter
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message


BOT_TOKEN = "8605851489:AAGFXGDVNAknWiIg_NP0ZGT3JtfHOM9sdrA"


class ModerationBot:

    def __init__(self, token: str):

        self.bot = Bot(token=token)
        self.dp = Dispatcher()

        self.deleted_counter = 0
        self.word_stats = Counter()

        self.forbidden_words = self.load_banwords()

        print(f"Загружено {len(self.forbidden_words)} банвордов")

        self.register_handlers()

    # ==========================================
    # ЗАГРУЗКА БАНВОРДОВ
    # ==========================================
    def load_banwords(self):

        try:

            with open(
                "banwords.json",
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            all_words = []

            for category in data.values():
                all_words.extend(category)

            return [
                word.lower()
                for word in all_words
            ]

        except FileNotFoundError:

            print("banwords.json не найден")
            return []

        except json.JSONDecodeError:

            print("Ошибка JSON")
            return []

    # ==========================================
    # ПОИСК БАНВОРДОВ
    # ==========================================
    def contains_forbidden(self, text: str):

        if not text:
            return []

        text_lower = text.lower()

        text_clean = re.sub(
            r"[^\w\sа-яё0-9@]",
            " ",
            text_lower,
            flags=re.IGNORECASE
        )

        words_in_text = text_clean.split()

        found_words = []

        for word in self.forbidden_words:

            if word in words_in_text:

                if word not in found_words:
                    found_words.append(word)

        return found_words

    # ==========================================
    # СТАТИСТИКА СЛОВ
    # ==========================================
    def add_word_stats(self, words):

        for word in words:
            self.word_stats[word] += 1

    # ==========================================
    # ПРОВЕРКА АДМИНА
    # ==========================================
    async def is_admin(self, message: Message):

        if message.chat.type == "private":
            return True

        try:

            member = await self.bot.get_chat_member(
                message.chat.id,
                message.from_user.id
            )

            return member.status in [
                "creator",
                "administrator"
            ]

        except:
            return False

    # ==========================================
    # УДАЛЕНИЕ СООБЩЕНИЯ ПОЗЖЕ
    # ==========================================
    async def delete_message_later(
        self,
        chat_id: int,
        message_id: int,
        delay: int = 60
    ):

        await asyncio.sleep(delay)

        try:

            await self.bot.delete_message(
                chat_id,
                message_id
            )

        except:
            pass

    # ==========================================
    # /START
    # ==========================================
    async def start_command(self, message: Message):

        await message.answer(
            "Привет.\n\n"
            "Я бот модерации чата.\n\n"

            "<b>Что умею:</b>\n"
            "• удаляю текстовые сообщения\n"
            "• проверяю подписи к медиа\n"
            "• удаляю сообщения с банвордами\n"
            "• собирает статистику\n\n"

            "<b>Команды:</b>\n"
            "/stats — статистика\n"
            "/reload — перезагрузка banwords.json\n\n"

            f"Загружено банвордов: "
            f"{len(self.forbidden_words)}",

            parse_mode="HTML"
        )

    # ==========================================
    # /STATS
    # ==========================================
    async def stats_command(self, message: Message):

        top_words = self.word_stats.most_common(15)

        if top_words:

            words_text = "\n".join(
                [
                    f"• {word} — {count}"
                    for word, count in top_words
                ]
            )

        else:

            words_text = "Нет данных"

        text = (
            f"Статистика бота\n\n"

            f"Удалено сообщений: "
            f"{self.deleted_counter}\n\n"

            f"Топ банвордов:\n"
            f"{words_text}\n\n"

            f"Всего банвордов: "
            f"{len(self.forbidden_words)}\n\n"

            f"{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )

        if message.chat.type == "private":

            await message.answer(text)

        else:

            await message.answer(
                "Статистика отправлена в ЛС"
            )

            await self.bot.send_message(
                message.from_user.id,
                text
            )

    # ==========================================
    # /RELOAD
    # ==========================================
    async def reload_command(self, message: Message):

        if not await self.is_admin(message):

            await message.answer(
                "Только для админов"
            )

            return

        new_words = self.load_banwords()

        if new_words:

            self.forbidden_words = new_words

            await message.answer(
                f"Банворды обновлены\n"
                f"Загружено: "
                f"{len(self.forbidden_words)}"
            )

            print(
                f"Банворды обновил "
                f"{message.from_user.first_name}"
            )

        else:

            await message.answer(
                "Ошибка загрузки banwords.json"
            )

    # ==========================================
    # ОБРАБОТКА ТЕКСТА
    # ==========================================
    async def handle_text(self, message: Message):

        if message.text.startswith("/"):
            return

        if await self.is_admin(message):
            return

        bad_words = self.contains_forbidden(
            message.text
        )

        await message.delete()

        self.deleted_counter += 1

        # Добавляем в статистику,
        # но не показываем пользователю
        if bad_words:
            self.add_word_stats(bad_words)

        warn = await message.answer(
            f"{message.from_user.first_name}, "
            f"вы забыли прикрепить картинку"
        )

        asyncio.create_task(
            self.delete_message_later(
                warn.chat.id,
                warn.message_id
            )
        )

        print(
            f"Удален текст от "
            f"{message.from_user.first_name}"
        )

    # ==========================================
    # ОБРАБОТКА ФОТО
    # ==========================================
    async def handle_photo(self, message: Message):

        if not message.caption:
            return

        if message.caption.startswith("/"):
            return

        if await self.is_admin(message):
            return

        bad_words = self.contains_forbidden(
            message.caption
        )

        if not bad_words:
            return

        await message.delete()

        self.deleted_counter += 1

        self.add_word_stats(bad_words)

        warn = await message.answer(
            f"{message.from_user.first_name}, "
            f"сообщение удалено\n\n"

            f"Причина:\n"
            f"{', '.join(bad_words)}"
        )

        asyncio.create_task(
            self.delete_message_later(
                warn.chat.id,
                warn.message_id
            )
        )

        print(
            f"Удалено фото от "
            f"{message.from_user.first_name} | "
            f"Слова: {', '.join(bad_words)}"
        )

    # ==========================================
    # ОБРАБОТКА МЕДИА
    # ==========================================
    async def handle_media(self, message: Message):

        if not message.caption:
            return

        if message.caption.startswith("/"):
            return

        if await self.is_admin(message):
            return

        bad_words = self.contains_forbidden(
            message.caption
        )

        if not bad_words:
            return

        await message.delete()

        self.deleted_counter += 1

        self.add_word_stats(bad_words)

        warn = await message.answer(
            f"{message.from_user.first_name}, "
            f"сообщение удалено\n\n"

            f"Причина:\n"
            f"{', '.join(bad_words)}"
        )

        asyncio.create_task(
            self.delete_message_later(
                warn.chat.id,
                warn.message_id
            )
        )

        print(
            f"Удален медиафайл от "
            f"{message.from_user.first_name} | "
            f"Слова: {', '.join(bad_words)}"
        )

    # ==========================================
    # РЕГИСТРАЦИЯ ХЕНДЛЕРОВ
    # ==========================================
    def register_handlers(self):

        self.dp.message.register(
            self.start_command,
            Command("start")
        )

        self.dp.message.register(
            self.stats_command,
            Command("stats")
        )

        self.dp.message.register(
            self.reload_command,
            Command("reload")
        )

        self.dp.message.register(
            self.handle_text,
            F.text
        )

        self.dp.message.register(
            self.handle_photo,
            F.photo
        )

        self.dp.message.register(
            self.handle_media,
            (
                F.video
                | F.document
                | F.audio
                | F.voice
            )
        )

    # ==========================================
    # ЗАПУСК
    # ==========================================
    async def run(self):

        print("Бот запущен")

        await self.dp.start_polling(self.bot)


# ==========================================
# MAIN
# ==========================================
async def main():

    bot = ModerationBot(BOT_TOKEN)

    await bot.run()


if __name__ == "__main__":

    asyncio.run(main())