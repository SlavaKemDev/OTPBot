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

load_dotenv()

dp = Dispatcher()
bot = Bot(token=os.environ['BOT_TOKEN'], default=DefaultBotProperties(parse_mode=ParseMode.HTML))

totp = TOTP(os.environ['OTP_SECRET'])
CHAT_ID = int(os.environ['CHAT_ID'])


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


@dp.message(Command("otp"))
async def otp(message: Message):
    if message.chat.id != CHAT_ID:
        return

    now = datetime.now(timezone.utc)
    timestamp = int(now.timestamp())

    code = totp.now()
    time_remaining = totp.interval - (timestamp % totp.interval)

    await message.answer(f"<code>{html.quote(code)}</code>\n\nДействует ещё {html.bold(time_remaining)} {pluralize_seconds(time_remaining)}")


async def main() -> None:
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
