import os
import telebot
from gtts import gTTS
from deep_translator import GoogleTranslator
import io

# Environment theke token nibe (Railway/GitHub safe)
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    print("❌ BOT_TOKEN environment variable set koro!")
    exit(1)

bot = telebot.TeleBot(TOKEN)

# User er selected language store korbo
user_language = {}

# Language config
LANGUAGES = {
    "🇯🇵 Japanese (Female)": {"lang": "ja", "tld": "com", "gender": "female", "translate_to": "ja"},
    "🇯🇵 Japanese (Male)":   {"lang": "ja", "tld": "com.au", "gender": "male", "translate_to": "ja"},
    "🇧🇩 Bangla (BD)":       {"lang": "bn", "tld": "com", "gender": None, "translate_to": "bn"},
    "🇮🇳 Bangla (India)":    {"lang": "bn", "tld": "co.in", "gender": None, "translate_to": "bn"},
    "🇬🇧 English":           {"lang": "en", "tld": "com", "gender": None, "translate_to": "en"},
    "🇮🇳 Hindi":             {"lang": "hi", "tld": "com", "gender": None, "translate_to": "hi"},
    "🇵🇰 Urdu":              {"lang": "ur", "tld": "com", "gender": None, "translate_to": "ur"},
}

def build_language_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [telebot.types.KeyboardButton(name) for name in LANGUAGES.keys()]
    markup.add(*buttons)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = build_language_keyboard()
    bot.reply_to(
        message,
        "🎙️ *Text-to-Speech Bot*\n\nFirst select a language below, then send any text!\n\n"
        "✅ Your text will be auto-translated and spoken in the selected language.",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.message_handler(commands=['lang'])
def change_language(message):
    markup = build_language_keyboard()
    bot.reply_to(message, "Choose a language:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in LANGUAGES)
def set_language(message):
    user_language[message.from_user.id] = message.text
    lang_name = message.text
    bot.reply_to(
        message,
        f"✅ Language set to *{lang_name}*\n\nNow send any text and I'll speak it in that language! 🎧",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: True)
def text_to_speech(message):
    if message.text.startswith('/'):
        return

    user_text = message.text.strip()
    if not user_text:
        bot.reply_to(message, "Kichu likho bhai 😅")
        return

    uid = message.from_user.id

    # Default: Bangla BD (original behavior)
    selected = user_language.get(uid, "🇧🇩 Bangla (BD)")
    config = LANGUAGES[selected]

    lang_code   = config["lang"]
    tld         = config["tld"]
    translate_to = config["translate_to"]

    # Auto-translate text to target language
    try:
        translated_text = GoogleTranslator(source='auto', target=translate_to).translate(user_text)
    except Exception as e:
        print(f"⚠️ Translation failed: {e}")
        translated_text = user_text  # fallback: original text use korbo

    # gTTS diye audio banao
    try:
        tts = gTTS(text=translated_text, lang=lang_code, tld=tld, slow=False)
    except Exception as e:
        bot.reply_to(message, f"❌ TTS error: {e}")
        return

    mp3_fp = io.BytesIO()
    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)

    gender_label = f" ({config['gender'].capitalize()})" if config["gender"] else ""
    caption = f"𝘾𝙧𝙚𝙖𝙩𝙚𝙙 𝘽𝙮 | 𝙎𝙖𝙖𝙁𝙚 🖤\n🔊 {selected}{gender_label}"

    bot.send_audio(
        chat_id=message.chat.id,
        audio=mp3_fp,
        caption=caption,
        reply_to_message_id=message.message_id,
        filename="voice.mp3"
    )

    print(f"✅ {message.from_user.username or uid} | Lang: {selected} | Text: {user_text[:30]}")

print("🤖 Bot starting... Railway te online!")
bot.infinity_polling()
