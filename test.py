import logging
import openai
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ContentType
from config import settings

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.bot_token)
dp = Dispatcher()

openai.api_key = settings.openai_api_key

async def convert_voice_to_text(file_path: str) -> str:
    with open(file_path, "rb") as audio_file:
        response = openai.Audio.transcribe("whisper-1", audio_file)
    return response["text"]

@dp.message(CommandStart())
async def whatsupp_bro(message: types.Message):
    await message.reply("Салам че, погнали пиздеть")

@dp.message(F.voice)
async def handle_voice_message(message: types.Message):
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    file_name = f"audio_{file_id}.ogg"
    
    await bot.download_file(file_path, file_name)
    text = await convert_voice_to_text(file_name)
    await message.reply(text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
