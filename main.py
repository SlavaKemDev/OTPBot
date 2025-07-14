import asyncio
import logging
import sys
import os
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ChatMemberStatus
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

storage = Storage()

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


@dp.message(Command("otp"))
async def otp(message: Message):
    if message.chat.id != CHAT_ID:
        return
    code, time_remaining = get_code_and_time()
    await message.answer(f"{html.code(code)}\n\nДействует ещё {html.bold(time_remaining)} {pluralize_seconds(time_remaining)}")


def render_login_template(url: str, login: str, password: str, otp_code: str, otp_time) -> str:
    minutes = otp_time // 60
    secs = otp_time % 60
    ms_format = f"{minutes:02}:{secs:02}"
    return (
        f"🔐 <b>Данные для входа</b>\n\n"
        f"🌐 Сайт: <a href=\"{html.quote(url)}\">{html.quote(url)}</a>\n"
        f"👤 Логин: {html.code(html.quote(login))}\n"
        f"🔑 Пароль: {html.code(html.quote(password))}\n"
        f"📲 OTP-код: {html.code(html.quote(otp_code))} ({html.bold(ms_format)})\n\n"
    )


async def update_pinned_message():
    global storage

    pinned_messages = storage.get("pinned_messages", {})
    pinned_message_id = pinned_messages.get(str(CHAT_ID), -1)

    while True:
        code, time_remaining = get_code_and_time()

        message_text = render_login_template(os.environ['URL'], os.environ['LOGIN'], os.environ['PASSWORD'], code, time_remaining)

        if pinned_message_id > 0:
            try:
                await bot.edit_message_text(
                    chat_id=CHAT_ID,
                    message_id=pinned_message_id,
                    text=message_text,
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logging.error(f"Failed to edit pinned message: {e}")
                pinned_message_id = -1
        else:
            try:
                new_message = await bot.send_message(
                    chat_id=CHAT_ID,
                    text=message_text,
                    parse_mode=ParseMode.HTML
                )
                await bot.pin_chat_message(chat_id=CHAT_ID, message_id=new_message.message_id, disable_notification=True)

                pinned_message_id = new_message.message_id
                pinned_messages[str(CHAT_ID)] = pinned_message_id
                storage.set("pinned_messages", pinned_messages)
            except Exception as e:
                logging.error(f"Failed to send message: {e}")

        await asyncio.sleep(3)


async def main() -> None:
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)


    async def run_all():
        await asyncio.gather(
            main(),
            update_pinned_message()
        )


    asyncio.run(run_all())
