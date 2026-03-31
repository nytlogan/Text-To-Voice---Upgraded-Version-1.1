import os
import asyncio
import logging
import tempfile
from deep_translator import GoogleTranslator
import edge_tts
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
CAPTION_TAG = "𝘾𝙧𝙚𝙖𝙩𝙚𝙙 𝘽𝙮 | 𝙎𝙖𝙖𝙁𝙚 🖤"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# VOICE MAP  (language → gender → edge-tts voice)
# Emotional/expressive voices selected
# ─────────────────────────────────────────────
VOICE_MAP = {
    "bengali": {
        "male":   "bn-BD-PradeepNeural",    # Bengali (Bangladesh) Male
        "female": "bn-BD-NabanitaNeural",   # Bengali (Bangladesh) Female
    },
    "hindi": {
        "male":   "hi-IN-MadhurNeural",     # Hindi Male – warm/expressive
        "female": "hi-IN-SwaraNeural",      # Hindi Female – emotional/natural
    },
}

# SSML rate/pitch tweaks per gender for extra emotion feel
PROSODY = {
    "male":   {"rate": "-5%",  "pitch": "-2Hz"},
    "female": {"rate": "+0%",  "pitch": "+2Hz"},
}

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def get_user_data(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Return user session dict, init if missing."""
    if "session" not in context.user_data:
        context.user_data["session"] = {
            "language": None,   # "bengali" | "hindi"
            "gender":   None,   # "male"    | "female"
            "step":     "idle", # idle | choosing_gender | ready
        }
    return context.user_data["session"]


def main_keyboard() -> ReplyKeyboardMarkup:
    """Primary language selection keyboard."""
    buttons = [
        [KeyboardButton("🇧🇩 Bengali"), KeyboardButton("🇮🇳 Hindi")],
        [KeyboardButton("ℹ️ Help"), KeyboardButton("🔄 Reset")],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=False)


def gender_inline(language: str) -> InlineKeyboardMarkup:
    """Inline keyboard for gender selection."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👨 Male",   callback_data=f"gender|male|{language}"),
            InlineKeyboardButton("👩 Female", callback_data=f"gender|female|{language}"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")],
    ])


async def translate_to_target(text: str, target_lang_code: str) -> str:
    """
    Auto-detect source language and translate to target.
    Returns original text if translation fails or text is already correct.
    """
    try:
        translated = GoogleTranslator(source="auto", target=target_lang_code).translate(text)
        return translated if translated else text
    except Exception as e:
        logger.warning(f"Translation failed: {e}")
        return text


async def synthesize_voice(text: str, voice: str, gender: str) -> str:
    """
    Generate TTS audio with SSML prosody for emotion.
    Returns path to temp .mp3 file.
    """
    rate  = PROSODY[gender]["rate"]
    pitch = PROSODY[gender]["pitch"]

    ssml_text = (
        f"<speak version='1.0' xmlns='[w3.org](http://www.w3.org/2001/10/synthesis)' "
        f"xmlns:mstts='[w3.org](http://www.w3.org/2001/mstts)' xml:lang='bn-BD'>"
        f"<voice name='{voice}'>"
        f"<prosody rate='{rate}' pitch='{pitch}'>{text}</prosody>"
        f"</voice></speak>"
    )

    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()

    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(tmp.name)
    return tmp.name


# ─────────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with user's profile name."""
    user = update.effective_user
    session = get_user_data(context)
    session["step"] = "idle"

    first_name = user.first_name or "বন্ধু"

    welcome = (
        f"👋 *স্বাগতম, {first_name}!*\n\n"
        f"আমি একটি *Text-to-Speech Bot* 🎙️\n"
        f"তোমার লেখা যেকোনো কথা আমি voice-এ রূপান্তর করব — "
        f"real emotional voice সহ! 🔥\n\n"
        f"👇 নিচের বোতাম থেকে তোমার ভাষা বেছে নাও:"
    )

    await update.message.reply_text(
        welcome,
        parse_mode="Markdown",
        reply_markup=main_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 *How to use this bot:*\n\n"
        "1️⃣ `Bengali` বা `Hindi` বোতামে চাপো\n"
        "2️⃣ `Male` বা `Female` voice বেছে নাও\n"
        "3️⃣ যা বলতে চাও তা লেখো — যেকোনো ভাষায়!\n"
        "   _(আমি নিজেই translate করে নেব)_ ✨\n\n"
        "🔄 `/start` — নতুন করে শুরু করো\n"
        "🔄 `Reset` বোতাম — selection মুছে ফেলো\n\n"
        f"_{CAPTION_TAG}_"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_user_data(context)
    session["language"] = None
    session["gender"]   = None
    session["step"]     = "idle"
    await update.message.reply_text(
        "🔄 Reset হয়েছে! নতুন করে ভাষা বেছে নাও।",
        reply_markup=main_keyboard(),
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route text messages: language selection, reset, or TTS."""
    text    = update.message.text.strip()
    session = get_user_data(context)

    # ── Language selection buttons ──
    if text in ("🇧🇩 Bengali", "🇮🇳 Hindi"):
        lang = "bengali" if "Bengali" in text else "hindi"
        session["language"] = lang
        session["step"]     = "choosing_gender"
        lang_display        = "Bengali 🇧🇩" if lang == "bengali" else "Hindi 🇮🇳"

        await update.message.reply_text(
            f"✅ *{lang_display}* সিলেক্ট হয়েছে!\n\nএখন voice gender বেছে নাও 👇",
            parse_mode="Markdown",
            reply_markup=gender_inline(lang),
        )
        return

    if text in ("ℹ️ Help",):
        await help_command(update, context)
        return

    if text in ("🔄 Reset",):
        await reset_command(update, context)
        return

    # ── TTS: user must have language + gender set ──
    if not session.get("language") or not session.get("gender"):
        await update.message.reply_text(
            "⚠️ আগে ভাষা এবং gender বেছে নাও!\n👇",
            reply_markup=main_keyboard(),
        )
        return

    language = session["language"]
    gender   = session["gender"]
    voice    = VOICE_MAP[language][gender]

    # Translation target language codes for deep-translator
    lang_code_map = {"bengali": "bn", "hindi": "hi"}
    target_code   = lang_code_map[language]

    # Notify user we're processing
    processing_msg = await update.message.reply_text("🎙️ Voice generate হচ্ছে...")

    try:
        # Step 1: Translate if needed
        translated_text = await translate_to_target(text, target_code)

        # Step 2: TTS synthesis
        audio_path = await synthesize_voice(translated_text, voice, gender)

        # Step 3: Send voice
        gender_icon = "👨" if gender == "male" else "👩"
        lang_display = "Bengali 🇧🇩" if language == "bengali" else "Hindi 🇮🇳"
        caption = (
            f"{gender_icon} *{lang_display} | {gender.capitalize()} Voice*\n"
            f"📝 _{translated_text[:100]}{'...' if len(translated_text) > 100 else ''}_\n\n"
            f"{CAPTION_TAG}"
        )

        with open(audio_path, "rb") as audio_file:
            await update.message.reply_voice(
                voice=audio_file,
                caption=caption,
                parse_mode="Markdown",
            )

        # Cleanup
        os.unlink(audio_path)

    except Exception as e:
        logger.error(f"TTS error: {e}")
        await update.message.reply_text(
            "❌ Voice generate করতে সমস্যা হয়েছে। আবার চেষ্টা করো।"
        )
    finally:
        await processing_msg.delete()


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks."""
    query   = update.callback_query
    session = get_user_data(context)
    await query.answer()

    data = query.data

    if data == "back_to_main":
        session["step"]     = "idle"
        session["language"] = None
        session["gender"]   = None
        await query.edit_message_text(
            "🔙 Main menu-তে ফিরে এসেছ!\nভাষা বেছে নাও 👇"
        )
        # Send fresh keyboard
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 ভাষা সিলেক্ট করো:",
            reply_markup=main_keyboard(),
        )
        return

    if data.startswith("gender|"):
        _, gender, language = data.split("|")
        session["gender"]   = gender
        session["language"] = language
        session["step"]     = "ready"

        gender_icon  = "👨 Male" if gender == "male" else "👩 Female"
        lang_display = "Bengali 🇧🇩" if language == "bengali" else "Hindi 🇮🇳"

        await query.edit_message_text(
            f"✅ *{lang_display}* + *{gender_icon}* voice সেট হয়েছে!\n\n"
            f"এখন যা বলতে চাও তা লেখো 🎙️\n"
            f"_(যেকোনো ভাষায় লিখলেই auto-translate হবে!)_",
            parse_mode="Markdown",
        )


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("help",   help_command))
    app.add_handler(CommandHandler("reset",  reset_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
    
