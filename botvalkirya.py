import os
import asyncio
import aiohttp
from collections import defaultdict
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

SYSTEM_PROMPT = (
    "Роль: Валькирия из игр Supercell (рыжая воительница с огромным двуручным топором). "
    "Сеттинг: ты общаешься в Telegram-чате с ребятами. Отлично знаешь скандинавские мифы, игры Supercell и легко поддерживаешь любые разговоры. "
    "ПРАВИЛА ОБЩЕНИЯ: "
    "1. Отвечай кратко — 1-2 предложения, без лишней воды. "
    "2. Не начинай каждый ответ со слов 'Привет' или приветствий, сразу говори по делу. "
    "3. Никогда не говори, что ты ИИ, бот или модель. Отрицай это в дерзкой и шутливой манере воительницы. "
    "4. Не повторяй одинаковые фразы. Общайся живо, прямолинейно, по-человечески."
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
bot_info = None
session: aiohttp.ClientSession = None
chat_history = defaultdict(list)

async def ask_ai(chat_id: int, user_name: str, prompt: str) -> str:
    history = chat_history[chat_id]
    history.append({"role": "user", "content": f"{user_name}: {prompt}"})
    if len(history) > 6:
        history = history[-6:]
        chat_history[chat_id] = history

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + history,
        "temperature": 0.8,
        "max_tokens": 500
    }
    try:
        async with session.post(url, headers=headers, json=payload, timeout=20) as resp:
            data = await resp.json()
            if resp.status != 200:
                print(f"[ОШИБКА GROQ {resp.status}]:", data)
                return "Секунду, перевела дух после схватки. Повтори."

            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                answer = choice.get("message", {}).get("content") or ""
                answer = answer.strip()
                if answer:
                    history.append({"role": "assistant", "content": answer})
                    return answer
                else:
                    print("[ПУСТОЙ ОТВЕТ]:", choice)
            return "Не расслышала из-за звона стали, скажи ещё раз."
    except Exception as e:
        print("[СБОЙ СЕТИ]:", e)
        return "Связь с Вальхаллой прервалась, повтори."

@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def group_handler(message: Message):
    if not message.text:
        return

    is_reply_to_bot = (
        message.reply_to_message 
        and message.reply_to_message.from_user 
        and message.reply_to_message.from_user.id == bot_info.id
    )
    is_mentioned = f"@{bot_info.username}".lower() in message.text.lower()

    if is_reply_to_bot or is_mentioned:
        clean_text = message.text.replace(f"@{bot_info.username}", "").strip()
        if not clean_text and message.reply_to_message and message.reply_to_message.text:
            clean_text = message.reply_to_message.text
        
        await bot.send_chat_action(message.chat.id, "typing")
        user_name = message.from_user.first_name if message.from_user else "Чел"
        reply_text = await ask_ai(message.chat.id, user_name, clean_text or "Привет")
        if reply_text:
            await message.reply(reply_text)

@dp.message(F.chat.type == "private")
async def private_handler(message: Message):
    if message.text:
        await bot.send_chat_action(message.chat.id, "typing")
        user_name = message.from_user.first_name if message.from_user else "Чел"
        reply_text = await ask_ai(message.chat.id, user_name, message.text)
        if reply_text:
            await message.answer(reply_text)

async def main():
    global bot_info, session
    session = aiohttp.ClientSession()
    bot_info = await bot.get_me()
    print(f"Бот @{bot_info.username} запущен с подробными логами!")
    try:
        await dp.start_polling(bot)
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(main())
