import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ContentType
from config import settings
import openai
import asyncio
import os
from openai import AsyncOpenAI
from aiogram.types import FSInputFile

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.bot_token)
dp = Dispatcher()

DIRECTORY = "voices"
if not os.path.exists(DIRECTORY):
    os.makedirs(DIRECTORY)

os.environ['OPENAI_API_KEY'] = settings.openai_api_key
openai.api_key = settings.openai_api_key
client = AsyncOpenAI()

tools_list = [{
    "type": "function",
    "function": {

        "name": "save_value",
        "description": "Вызывается, если в сообщении найдена ключевая ценность, принимает str с этой ценностью",
        "parameters": {
            "type": "object",
            "properties": {
                "value": {
                    "type": "string",
                    "description": "key value of user"
                }
            },
            "required": ["value"]
        }
    }
}]

async def convert_voice_to_text(local_path: str) -> str:
    with open(local_path, "rb") as audio_file:
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return response.text

async def save_value(value: str):
    await print("В СЕЙВ ВАЛЮ ЗАХОДИТ")

@dp.message(CommandStart())
async def whatsupp_bro(message: types.Message):
    global assistant
    assistant = await client.beta.assistants.create(
        name="helpful assistant",
        instructions = "Ты ассистент-собеседник. Твоя задача - выявлять ключевые ценности или цели пользователя. Если в сообщения пользователя есть ключевая ценность или его цель, вызывай function save_value и передавай в неё str c ценностью пользователя",
        tools=tools_list,
        model="gpt-4o",
    )

    global thread
    thread = await client.beta.threads.create()
    await message.reply("Бот запущен")

@dp.message(F.voice)
async def handle_voice_message(message: types.Message):
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    local_path = f"{DIRECTORY}/voice_message.mp3"
    await bot.download_file(file_path, local_path)
    text = await convert_voice_to_text(local_path)

    mess = await client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=text
    )

    run = await client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )      

    print(run.status)

    if run.status == "completed":
        messages = await client.beta.threads.messages.list(thread_id=thread.id)
        async for messagee in messages:
            if messagee.content[0].type == "text":
                response = messagee.content[0].text.value
                break
    elif run.status == "requires_action":
        print("Вошло в requires_action")
        messages = await client.beta.threads.messages.list(thread_id=thread.id)
        async for messagee in messages:
            if messagee.content[0].type == "text":
                response = messagee.content[0].text.value
                break
        #ну и дальше типо извлечение ценности, проверка ее на адекватность

        
    speech_file_path = f"{DIRECTORY}/speech.mp3"
    with openai.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="alloy",
        input=response,
    ) as response_speech:
        response_speech.stream_to_file(speech_file_path)

    voice = FSInputFile(speech_file_path)
    await bot.send_voice(message.chat.id, voice)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())