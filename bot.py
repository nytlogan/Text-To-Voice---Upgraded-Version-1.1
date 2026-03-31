import os
import asyncio
import logging
import tempfile
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import edge_tts
from deep_translator import GoogleTranslator

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Bot Token ─────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ── Language Config ───────────────────────────────────────────────────────────
# Each language: display name, translator code, male voice, female voice, emotion SSML rate/pitch
LANGUAGES = {
    "🇧🇩 Bengali":   {"code": "bn",  "male": "bn-BD-PradeepNeural",   "female": "bn-BD-NabanitaNeural",   "pitch": "+0Hz",  "rate": "+0%"},
    "🇮🇳 Hindi":     {"code": "hi",  "male": "hi-IN-MadhurNeural",     "female": "hi-IN-SwaraNeural",       "pitch": "+0Hz",  "rate": "+0%"},
    "🇵🇰 Urdu":      {"code": "ur",  "male": "ur-PK-AsadNeural",       "female": "ur-PK-UzmaNeural",        "pitch": "+0Hz",  "rate": "+0%"},
    "🇬🇧 English":   {"code": "en",  "male": "en-US-GuyNeural",        "female": "en-US-JennyNeural",       "pitch": "+0Hz",  "rate": "+0%"},
    "🇯🇵 Japanese":  {"code": "ja",  "male": "ja-JP-KeitaNeural",      "female": "ja-JP-NanamiNeural",      "pitch": "+0Hz",  "rate": "+0%"},
    "🇪🇸 Spanish":   {"code": "es",  "male": "es-ES-AlvaroNeural",     "female": "es-ES-ElviraNeural",      "pitch": "+0Hz",  "rate": "+0%"},
    "🇸🇦 Arabic":    {"code": "ar",  "male": "ar-SA-HamedNeural",      "female": "ar-SA-ZariyahNeural",     "pitch": "+0Hz",  "rate": "+0%"},
    "🇫🇷 French":    {"code": "fr",  "male": "fr-FR-HenriNeural",      "female": "fr-FR-DeniseNeural",      "pitch": "+0Hz",  "rate": "+0%"},
    "🇷🇺 Russian":   {"code": "ru",  "male": "ru-RU-DmitryNeural",     "female": "ru-RU-SvetlanaNeural",    "pitch": "+0Hz",  "rate": "+0%"},
}

# Emotion presets (applied via SSML-style prosody in edge-tts)
# edge-tts supports style via communicate; we add natural variation per gender
MALE_PITCH   = "-2Hz"
MALE_RATE    = "+0%"
FEMALE_PITCH = "+5Hz"
FEMALE_RATE  = "+2%"

CAPTION_TAG = "𝘾𝙧𝙚𝙖𝙩𝙚𝙙 𝘽𝙮 | 𝙎𝙖𝙖𝙁𝙚 🖤"

# ── Keyboard Builders ─────────────────────────────────────────────────────────

def build_language_keyboard() -> InlineKeyboardMarkup:
    """3-column grid of language buttons."""
    lang_list = list(LANGUAGES.keys())
    buttons = []
    row = []
    for i, lang in enumerate(lang_list):
        row.append(InlineKeyboardButton(lang, callback_data=f"lang:{lang}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


def build_gender_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Male / Female buttons after language is chosen."""
    buttons = [
        [
            InlineKeyboardButton("👨 Male",   callback_data=f"gender:{lang}:male"),
            InlineKeyboardButton("👩 Female", callback_data=f"gender:{lang}:female"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back:language")],
    ]
    return InlineKeyboardMarkup(buttons)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_user_first_name(update: Update) -> str:
    user = update.effective_user
    return user.first_name if user and user.first_name else "Friend"


def translate_to_target(text: str, target_lang_code: str) -> str:
    """Translate text to target language. Returns original on failure."""
    try:
        translator = GoogleTranslator(source="auto", target=target_lang_code)
        return translator.translate(text)
    except Exception as e:
        logger.warning(f"Translation failed: {e}")
        return text


async def generate_tts(text: str, voice: str, pitch: str, rate: str) -> str:
    """Generate TTS audio using edge-tts. Returns path to temp .mp3 file."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp_path = tmp.name
    tmp.close()

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        pitch=pitch,
        rate=rate,
    )
    await communicate.save(tmp_path)
    return tmp_path


# ── Handlers ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = get_user_first_name(update)
    welcome_text = (
        f"✨ *Welcome, {name}!* ✨\n\n"
        "আমি একটি *Multilingual TTS Bot* 🎙️\n"
        "তোমার লেখাকে যেকোনো ভাষায় voice-এ রূপান্তর করতে পারি!\n\n"
        "👇 নিচে থেকে তোমার *ভাষা* বেছে নাও:"
    )
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=build_language_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "📖 *How to use this bot:*\n\n"
        "1️⃣ /start — শুরু করো, ভাষা বেছে নাও\n"
        "2️⃣ ভাষা সিলেক্ট করো\n"
        "3️⃣ Male বা Female voice বেছে নাও\n"
        "4️⃣ যা বলতে চাও লিখে পাঠাও (যেকোনো ভাষায়)\n"
        "5️⃣ Bot auto-translate করে voice তৈরি করে দেবে!\n\n"
        "🔄 /reset — নতুন করে শুরু করো\n"
        "ℹ️ /help — এই message দেখাও"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await update.message.reply_text(
        "🔄 Reset done! নতুন করে শুরু করো:",
        reply_markup=build_language_keyboard(),
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data

    # ── Language selected ──
    if data.startswith("lang:"):
        lang = data[len("lang:"):]
        context.user_data["language"] = lang
        lang_code = LANGUAGES[lang]["code"]
        context.user_data["lang_code"] = lang_code

        await query.edit_message_text(
            f"✅ ভাষা বেছেছ: *{lang}*\n\nএখন voice type বেছে নাও 👇",
            parse_mode="Markdown",
            reply_markup=build_gender_keyboard(lang),
        )

    # ── Gender selected ──
    elif data.startswith("gender:"):
        _, lang, gender = data.split(":", 2)
        context.user_data["language"] = lang
        context.user_data["lang_code"] = LANGUAGES[lang]["code"]
        context.user_data["gender"] = gender

        voice_key = LANGUAGES[lang][gender]
        pitch = FEMALE_PITCH if gender == "female" else MALE_PITCH
        rate  = FEMALE_RATE  if gender == "female" else MALE_RATE
        context.user_data["voice"] = voice_key
        context.user_data["pitch"] = pitch
        context.user_data["rate"]  = rate

        gender_emoji = "👩 Female" if gender == "female" else "👨 Male"
        await query.edit_message_text(
            f"🎙️ *{lang}* — *{gender_emoji}* voice সিলেক্ট হয়েছে!\n\n"
            "✍️ এখন তোমার *text* লিখে পাঠাও — যেকোনো ভাষায় লিখলেও চলবে, "
            "আমি auto-translate করে নেবো! 🌐",
            parse_mode="Markdown",
        )

    # ── Back button ──
    elif data.startswith("back:"):
        target = data[len("back:"):]
        if target == "language":
            await query.edit_message_text(
                "👇 ভাষা আবার বেছে নাও:",
                reply_markup=build_language_keyboard(),
            )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_text = update.message.text.strip()

    # ── Check setup ──
    if "voice" not in context.user_data:
        await update.message.reply_text(
            "⚠️ আগে /start করে ভাষা ও voice বেছে নাও!",
            reply_markup=build_language_keyboard(),
        )
        return

    lang      = context.user_data["language"]
    lang_code = context.user_data["lang_code"]
    voice     = context.user_data["voice"]
    pitch     = context.user_data["pitch"]
    rate      = context.user_data["rate"]
    gender    = context.user_data["gender"]

    # ── Translate ──
    processing_msg = await update.message.reply_text("⏳ Processing...")

    translated_text = translate_to_target(user_text, lang_code)
    logger.info(f"Original: {user_text!r} | Translated ({lang_code}): {translated_text!r}")

    # ── Generate TTS ──
    try:
        audio_path = await generate_tts(translated_text, voice, pitch, rate)
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        await processing_msg.edit_text("❌ Voice generate করতে পারিনি। আবার চেষ্টা করো!")
        return

    # ── Send audio ──
    gender_label = "Female 👩" if gender == "female" else "Male 👨"
    caption = (
        f"🌐 *Language:* {lang}\n"
        f"🎙️ *Voice:* {gender_label}\n\n"
        f"{CAPTION_TAG}"
    )

    try:
        with open(audio_path, "rb") as audio_file:
            await update.message.reply_voice(
                voice=audio_file,
                caption=caption,
                parse_mode="Markdown",
            )
    finally:
        os.remove(audio_path)
        await processing_msg.delete()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set!")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("help",   help_command))
    app.add_handler(CommandHandler("reset",  reset_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("🤖 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

