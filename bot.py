import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ContentType
from config import settings
import openai
import asyncio
import os
from openai import OpenAI
logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.bot_token)
dp = Dispatcher()
DIRECTORY = "voices"
if not os.path.exists(DIRECTORY):
    os.makedirs(DIRECTORY)


os.environ['OPENAI_API_KEY'] = settings.openai_api_key
openai.api_key = settings.openai_api_key
client = OpenAI()


assistant = client.beta.assistants.create(
    name="helpful assistant",
    instructions = "You are personal assistant",
    tools=[{"type": "code_interpreter"}],
    model="gpt-4o",
)

thread = client.beta.threads.create()

async def convert_voice_to_text(local_path: str) -> str:
    with open(local_path, "rb") as audio_file:
        response = client.audio.transcriptions.create(
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

    response = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=text
    )

    run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id,
    assistant_id=assistant.id,
    )      
    
    if run.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        if messages.data and messages.data[0].content[0].type == "text":
            await bot.send_message(message.chat.id, messages.data[0].content[0].text.value)




async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())