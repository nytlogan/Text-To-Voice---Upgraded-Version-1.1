import os
import telebot
from gtts import gTTS
from deep_translator import GoogleTranslator
import io
import time

# Initialize
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    print("❌ BOT_TOKEN environment variable not set!")
    exit(1)

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# User language preferences
user_language = {}

# Supported languages (safe TLDs only)
LANGUAGES = {
    "🇯🇵 Japanese (Female)": {"lang": "ja", "tld": "com", "gender": "female", "translate_to": "ja"},
    "🇯🇵 Japanese (Male)":   {"lang": "ja", "tld": "com", "gender": "male", "translate_to": "ja"},
    "🇧🇩 Bangla (BD)":       {"lang": "bn", "tld": "com", "gender": None, "translate_to": "bn"},
    "🇮🇳 Bangla (India)":    {"lang": "bn", "tld": "com", "gender": None, "translate_to": "bn"},
    "🇬🇧 English":           {"lang": "en", "tld": "com", "gender": None, "translate_to": "en"},
    "🇮🇳 Hindi":             {"lang": "hi", "tld": "com", "gender": None, "translate_to": "hi"},
    "🇵🇰 Urdu":              {"lang": "ur", "tld": "com", "gender": None, "translate_to": "ur"},
}

# --- Helpers ---

def build_language_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [telebot.types.KeyboardButton(name) for name in LANGUAGES]
    markup.add(*buttons)
    return markup

def safe_translate(text: str, target: str, timeout: int = 5) -> str:
    """Attempts translation with timeout and fallback."""
    start_time = time.time()
    try:
        result = GoogleTranslator(source='auto', target=target).translate(text)
        if not result:
            raise ValueError("Empty translation result.")
        duration = time.time() - start_time
        print(f"🌐 Translation success → {target} ({duration:.2f}s)")
        return result
    except Exception as e:
        duration = time.time() - start_time
        print(f"⚠️ Translation failed after {duration:.2f}s: {e}")
        print("➡️ Using original text as fallback.")
        return text  # fallback

def generate_tts(text: str, lang: str, tld: str, retry: int = 1):
    """Generates TTS audio, retries once if fails."""
    for attempt in range(retry + 1):
        try:
            tts = gTTS(text=text, lang=lang, tld=tld, slow=False)
            mp3_fp = io.BytesIO()
            tts.write_to_fp(mp3_fp)
            mp3_fp.seek(0)
            print(f"🔊 gTTS succeeded (attempt {attempt + 1}) | Lang={lang}")
            return mp3_fp
        except Exception as e:
            print(f"⚠️ gTTS failed (attempt {attempt + 1}): {e}")
            if attempt < retry:
                print("🔁 Retrying gTTS...")
                time.sleep(1)
            else:
                print("❌ All gTTS attempts failed.")
                return None

# --- Handlers ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = build_language_keyboard()
    bot.reply_to(
        message,
        "🎙️ *Text-to-Speech Bot*\n\n"
        "First select a language below, then send any text!\n\n"
        "✅ Your text will be auto-translated and spoken in the selected language.",
        reply_markup=markup
    )

@bot.message_handler(commands=['lang'])
def change_language(message):
    markup = build_language_keyboard()
    bot.reply_to(message, "🌍 Choose a language:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in LANGUAGES)
def set_language(message):
    user_language[message.from_user.id] = message.text
    bot.reply_to(
        message,
        f"✅ Language set to *{message.text}*\n\n"
        "Now send any text and I’ll speak it in that language! 🎧"
    )

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    if message.text.startswith("/"):
        return

    uid = message.from_user.id
    user_text = message.text.strip()

    if not user_text:
        bot.reply_to(message, "Please type something 😅")
        return

    # Default language
    selected_name = user_language.get(uid, "🇧🇩 Bangla (BD)")
    config = LANGUAGES[selected_name]

    lang_code = config["lang"]
    tld = config["tld"]
    translate_to = config["translate_to"]

    print(f"\n📝 User: {message.from_user.username or uid} | Text: {user_text[:40]}")
    print(f"➡️ Selected Language: {selected_name}")

    translated_text = safe_translate(user_text, translate_to)
    mp3_fp = generate_tts(translated_text, lang_code, tld, retry=1)

    if not mp3_fp:
        bot.reply_to(message, "❌ Sorry, failed to generate audio.")
        return

    voice_caption = f"🎧 {selected_name}\n𝘾𝙧𝙚𝙖𝙩𝙚𝙙 𝘽𝙮 | 𝙎𝙖𝙖𝙁𝙚 🖤"
    try:
        bot.send_voice(
            chat_id=message.chat.id,
            voice=mp3_fp,
            caption=voice_caption,
            reply_to_message_id=message.message_id
        )
        print(f"✅ Voice sent successfully!")
    except Exception as e:
        print(f"❌ Failed to send voice: {e}")
        bot.reply_to(message, "⚠️ Error sending voice message.")

# Run polling
print("🤖 Bot online and listening (Railway-ready)...")
bot.infinity_polling(skip_pending=True, timeout=20)
