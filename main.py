import os
import telebot
from gtts import gTTS
import io

# Environment theke token nibe (Railway/GitHub safe)
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    print("❌ BOT_TOKEN environment variable set koro!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Please Write Your Script.")

@bot.message_handler(func=lambda m: True)
def text_to_speech(message):
    if message.text.startswith('/'):
        return
    
    user_text = message.text.strip()
    if not user_text:
        bot.reply_to(message, "Kichu likho bhai 😅")
        return

    # Bangla voice best (BD er jonno) → 'bn'. English chaiলে 'en' koro
    tts = gTTS(text=user_text, lang='bn', slow=False)

    # Memory te MP3 banai (kono file save hoy na)
    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)

    bot.send_audio(
        chat_id=message.chat.id,
        audio=mp3_fp,
        caption="𝘾𝙧𝙚𝙖𝙩𝙚𝙙 𝘽𝙮 | 𝙎𝙖𝙖𝙁𝙚 🖤",
        reply_to_message_id=message.message_id,
        filename="voice.mp3"
    )

    print(f"✅ {message.from_user.username or message.from_user.id} er voice ready")

print("🤖 Bot starting... Railway te online!")
bot.infinity_polling()
