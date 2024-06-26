import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ContentType
from config import settings
import openai
import asyncio
import os

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.bot_token)
dp = Dispatcher()
DIRECTORY = "voices"
if not os.path.exists(DIRECTORY):
    os.makedirs(DIRECTORY)

openai.api_key = settings.openai_api_key

async def convert_voice_to_text(local_path: str) -> str:
    with open(local_path, "rb") as audio_file:
        response = openai.Audio.transcribe(
            model="whisper-1",
            file=audio_file
        )
    return response.text


@dp.message(CommandStart())
async def whatsupp_bro(message: types.Message):
    await message.reply("Салам че")

@dp.message(F.voice)
async def handle_voice_message(message: types.Message):
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    local_path = f"{DIRECTORY}/voice_message.mp3"
    await bot.download_file(file_path, local_path)
    text = await convert_voice_to_text(local_path)
    await message.reply(text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())