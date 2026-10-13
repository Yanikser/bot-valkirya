import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from groq import Groq

# Получаем ключи из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

# Словарь для хранения истории сообщений каждого пользователя отдельно
user_history = {}

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.chat.id
    # Очищаем историю при команде /start
    user_history[user_id] = [
        {"role": "system", "content": "Ты — Валькирия, воительница из скандинавских мифов. Отвечай с харизмой и характером воительницы."}
    ]
    await message.answer("Валхалла приветствует тебя, воин! Я Валькирия. Готова к разговору!")

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.chat.id
    text = message.text

    # Если пользователь пишет впервые, создаем для него контекст
    if user_id not in user_history:
        user_history[user_id] = [
            {"role": "system", "content": "Ты — Валькирия, воительница из скандинавских мифов. Отвечай с харизмой и характером воительницы."}
        ]

    # Сохраняем сообщение пользователя в его личную историю
    user_history[user_id].append({"role": "user", "content": text})

    # Ограничиваем историю последними 10 сообщениями, чтобы не перегружать память
    if len(user_history[user_id]) > 10:
        user_history[user_id] = [user_history[user_id][0]] + user_history[user_id][-9:]

    try:
        # Отправляем весь накопленный диалог в Groq
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=user_history[user_id]
        )
        
        reply_text = response.choices[0].message.content
        
        # Сохраняем ответ бота в историю
        user_history[user_id].append({"role": "assistant", "content": reply_text})
        
        await message.answer(reply_text)

    except Exception as e:
        print(f"Ошибка Groq API: {e}")
        await message.answer("Один из ворон Одина перехватил мое послание. Повтори еще раз!")

async def main():
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
