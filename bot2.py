import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from config import settings
import openai
import asyncio
import os
from openai import AsyncOpenAI
from aiogram.types import FSInputFile
import json
from sqlalchemy.future import select
from dbmodels import async_session, init_db, UserValue

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

async def str_to_bool(value: str) -> bool:
    return value.strip().lower() in ('true', '1', 'yes', 'y')

async def convert_voice_to_text(local_path: str) -> str:
    with open(local_path, "rb") as audio_file:
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return response.text

async def save_value(value: str):
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{'role':'user', 'content': f"Проверь, может ли {value} являться ценностью или целью человека. Ответь только 'true' или 'false'"}]
    )
    resultbool = await str_to_bool(str(response.choices[0].message.content))
    if resultbool:
        async with async_session() as session:
            new_value = UserValue(user_id=user_id, value=value)
            session.add(new_value)
            await session.commit()
    
    return value, resultbool


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
    global user_id
    user_id = message.from_user.id

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

    response = "бля чел у тебя не генерит ничего в случае требуются действия"

    if run.status == "completed":
        messages = await client.beta.threads.messages.list(thread_id=thread.id)
        async for messagee in messages:
            if messagee.content[0].type == "text":
                response = messagee.content[0].text.value
                break

    elif run.status == "requires_action":
        required_actions = run.required_action.submit_tool_outputs.model_dump()
        tool_outputs = []

        for action in required_actions["tool_calls"]:
            func_name = action['function']['name']
            arguments = json.loads(action['function']['arguments'])
            
            if func_name == "save_value":
                a, b = await save_value(value=arguments['value'])
                output = a
                tool_outputs.append({
                    "tool_call_id": action['id'],
                    "output": output
                })
            else:
                raise ValueError(f"Unknown function: {func_name}")
            
        run2 = await client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread.id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )

        while run2.status != "completed":
            await asyncio.sleep(1)
            run2 = await client.beta.threads.runs.poll(
                thread_id=thread.id,
                run_id=run2.id
            )

        messages = await client.beta.threads.messages.list(thread_id=thread.id)
        async for messagee in messages:
            if messagee.content[0].type == "text":
                response = messagee.content[0].text.value
                break

        await bot.send_message(message.chat.id, response)
    
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
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())