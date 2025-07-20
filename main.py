import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from dotenv import load_dotenv
from pyotp import TOTP
from storage import Storage

load_dotenv()

dp = Dispatcher()
bot = Bot(token=os.environ['BOT_TOKEN'], default=DefaultBotProperties(parse_mode=ParseMode.HTML))

totp = TOTP(os.environ['OTP_SECRET'])
CHAT_ID = int(os.environ['CHAT_ID'])
ADMIN_ID = int(os.environ['ADMIN_ID'])

storage = Storage()

if not storage.has("allowed_user_ids"):
    storage.set("allowed_user_ids", [])


@dp.message(CommandStart())
async def start(message: Message):
    await message.answer("Привет! Через меня можно запросить OTP-код для входа в ChatGPT. Для этого используй команду /otp")


def pluralize_seconds(n: int) -> str:
    if 11 <= n % 100 <= 14:
        return "секунд"
    last_digit = n % 10
    if last_digit == 1:
        return "секунду"
    elif 2 <= last_digit <= 4:
        return "секунды"
    else:
        return "секунд"


def get_code_and_time():
    now = datetime.now(timezone.utc)
    timestamp = int(now.timestamp())

    code = totp.now()
    time_remaining = totp.interval - (timestamp % totp.interval)

    return code, time_remaining


def confirm_user(user_id: int):
    allowed_users: list = storage.get("allowed_user_ids")
    if user_id not in allowed_users:
        allowed_users.append(user_id)
        storage.set("allowed_user_ids", allowed_users)


@dp.message(Command("otp"))
async def otp(message: Message):
    allowed_users: list = storage.get("allowed_user_ids")

    if message.from_user.username:
        user = f"<a href='https://t.me/{message.from_user.username}'>{message.from_user.full_name}</a>"
    else:
        user = message.from_user.full_name

    if message.chat.id != CHAT_ID and message.from_user.id not in allowed_users:
        await bot.send_message(ADMIN_ID, f"❌ {user} запросил код, но получил отказ", disable_web_page_preview=True)
        return

    confirm_user(message.from_user.id)

    code, time_remaining = get_code_and_time()
    await message.answer(f"{html.code(code)}\n\nДействует ещё {html.bold(time_remaining)} {pluralize_seconds(time_remaining)}")
    await bot.send_message(ADMIN_ID, f"🧑‍💻 {user} запросил код", disable_web_page_preview=True)


@dp.message(lambda msg: msg.chat.id == CHAT_ID)
async def update_conversation(message: Message):
    confirm_user(message.from_user.id)


async def main() -> None:
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
