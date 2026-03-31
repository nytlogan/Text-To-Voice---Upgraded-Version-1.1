import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from gtts import gTTS

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

user_voice_choice = {}  # store male/female per user


# ----------- KEYBOARDS -----------
def main_lang_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Bangla"))
    return kb

def gender_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("Male"), KeyboardButton("Female"))
    return kb


# ----------- START COMMAND -----------
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer(
        "স্বাগতম! নীচের অপশন থেকে বেছে নিন।",
        reply_markup=main_lang_keyboard()
    )


# ----------- LANGUAGE SELECT -----------
@dp.message_handler(lambda msg: msg.text == "Bangla")
async def choose_gender(message: types.Message):
    await message.answer("কোন ভয়েস চান?", reply_markup=gender_keyboard())


# ----------- GENDER SELECT -----------
@dp.message_handler(lambda msg: msg.text in ["Male", "Female"])
async def gender_selected(message: types.Message):
    user_voice_choice[message.from_user.id] = message.text
    await message.answer("আপনার স্ক্রিপ্ট লিখে পাঠান…")


# ----------- TEXT TO SPEECH -----------
@dp.message_handler()
async def text_to_speech(message: types.Message):
    uid = message.from_user.id

    if uid not in user_voice_choice:
        await message.answer("আগে Male/Female সিলেক্ট করুন!")
        return

    text = message.text
    gender = user_voice_choice[uid]

    filename = f"voice_{uid}.mp3"

    # gTTS supports only one Bangla voice — trick:
    # Male = lower pitch (slow)
    # Female = normal pitch (fast)
    speed = True if gender == "Female" else False

    tts = gTTS(text=text, lang="bn", slow=speed)
    tts.save(filename)

    with open(filename, "rb") as audio:
        await message.answer_audio(audio)

    os.remove(filename)


# ----------- MAIN -----------
if __name__ == "__main__":
    asyncio.run(dp.start_polling())
    
