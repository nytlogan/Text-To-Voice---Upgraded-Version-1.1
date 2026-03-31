import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

import edge_tts

# -------------------------------------------------------------
# BASIC CONFIGURATION
# -------------------------------------------------------------
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# -------------------------------------------------------------
# USER PREFERENCES STORAGE (RAM-based dictionary)
# For production you can replace with SQLite or PostgreSQL.
# -------------------------------------------------------------
user_preferences = {}  
# Structure:
# user_preferences[user_id] = {
#     "language": "en-US",
#     "gender": "Female",
#     "voice": "en-US-AriaNeural"
# }

# -------------------------------------------------------------
# SUPPORTED LANGUAGES AND VOICES (Edge TTS)
# -------------------------------------------------------------
voice_map = {
    "English": {
        "Female": "en-US-AriaNeural",
        "Male": "en-US-GuyNeural"
    },
    "Bengali": {
        "Female": "bn-BD-NabanitaNeural",
        "Male": "bn-BD-PradeepNeural"
    }
}

# Map human language → language code
language_short = {
    "English": "en-US",
    "Bengali": "bn-BD"
}

# -------------------------------------------------------------
# INLINE KEYBOARDS
# -------------------------------------------------------------
def lang_keyboard():
    kb = InlineKeyboardMarkup()
    for lang in voice_map.keys():
        kb.add(InlineKeyboardButton(text=lang, callback_data=f"set_lang|{lang}"))
    return kb

def gender_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Male", callback_data="set_gender|Male"))
    kb.add(InlineKeyboardButton("Female", callback_data="set_gender|Female"))
    return kb

# -------------------------------------------------------------
# /start COMMAND
# -------------------------------------------------------------
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_id = message.from_user.id

    if user_id not in user_preferences:
        user_preferences[user_id] = {"language": None, "gender": None, "voice": None}

    await message.answer(
        "Welcome! 👋\n\nBefore using Text‑to‑Speech, please choose your **language**:",
        reply_markup=lang_keyboard()
    )

# -------------------------------------------------------------
# CALLBACK HANDLER: SET LANGUAGE
# -------------------------------------------------------------
@dp.callback_query_handler(lambda c: c.data.startswith("set_lang"))
async def callback_set_language(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    _, lang = callback.data.split("|")

    user_preferences[user_id]["language"] = language_short[lang]

    await callback.message.edit_text(
        f"Language set to: {lang}\n\nNow choose **voice gender**:",
        reply_markup=gender_keyboard()
    )

# -------------------------------------------------------------
# CALLBACK HANDLER: SET GENDER
# -------------------------------------------------------------
@dp.callback_query_handler(lambda c: c.data.startswith("set_gender"))
async def callback_set_gender(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    _, gender = callback.data.split("|")

    user_preferences[user_id]["gender"] = gender

    # Determine voice based on saved language + gender
    lang_full = None
    for name, code in language_short.items():
        if code == user_preferences[user_id]["language"]:
            lang_full = name

    selected_voice = voice_map[lang_full][gender]
    user_preferences[user_id]["voice"] = selected_voice

    await callback.message.edit_text(
        f"✔ Gender set: {gender}\n"
        f"✔ Voice: {selected_voice}\n\n"
        "You're all set! 🎧\nSend me any text and I will convert it to speech."
    )

# -------------------------------------------------------------
# TEXT MESSAGE HANDLER → TTS RESPONSE
# -------------------------------------------------------------
@dp.message_handler()
async def tts_handler(message: types.Message):
    user_id = message.from_user.id

    # Ensure preferences selected
    if user_id not in user_preferences or user_preferences[user_id]["voice"] is None:
        return await message.answer(
            "You must set language and voice first.\nUse /start to begin."
        )

    text = message.text.strip()

    # Basic error handling
    if len(text) < 2:
        return await message.answer("Text is too short.")
    if len(text) > 500:
        return await message.answer("Text is too long. Max 500 characters.")

    voice = user_preferences[user_id]["voice"]

    # Filename for temporary audio
    output_file = f"tts_{user_id}.mp3"

    # ---------------------------------------------------------
    # EXECUTE EDGE TTS
    # ---------------------------------------------------------
    tts = edge_tts.Communicate(text, voice)

    try:
        await tts.save(output_file)
    except Exception as e:
        return await message.answer("❌ Error generating audio.")

    # ---------------------------------------------------------
    # SEND VOICE NOTE
    # ---------------------------------------------------------
    with open(output_file, "rb") as audio:
        await bot.send_voice(message.chat.id, audio)

    # Remove temp file
    try:
        os.remove(output_file)
    except:
        pass

# -------------------------------------------------------------
# START BOT
# -------------------------------------------------------------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
        
