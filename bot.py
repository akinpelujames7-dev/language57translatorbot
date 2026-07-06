import os
import logging
import sys
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token with better error handling
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN environment variable is not set!")
    logger.error("Please add it in Railway: Settings -> Variables -> Add Variable")
    logger.error("Variable name: TELEGRAM_BOT_TOKEN")
    logger.error("Value: Your bot token from @BotFather")
    sys.exit(1)

logger.info("✅ Bot token found!")

# Store user data
user_data = {}

# Supported languages
LANGUAGES = {
    'en': {'name': 'English', 'flag': '🇬🇧'},
    'es': {'name': 'Spanish', 'flag': '🇪🇸'},
    'fr': {'name': 'French', 'flag': '🇫🇷'},
    'de': {'name': 'German', 'flag': '🇩🇪'},
    'it': {'name': 'Italian', 'flag': '🇮🇹'},
    'pt': {'name': 'Portuguese', 'flag': '🇵🇹'},
    'ru': {'name': 'Russian', 'flag': '🇷🇺'},
    'zh-cn': {'name': 'Chinese', 'flag': '🇨🇳'},
    'ja': {'name': 'Japanese', 'flag': '🇯🇵'},
    'ar': {'name': 'Arabic', 'flag': '🇸🇦'},
    'hi': {'name': 'Hindi', 'flag': '🇮🇳'},
    'ko': {'name': 'Korean', 'flag': '🇰🇷'},
    'nl': {'name': 'Dutch', 'flag': '🇳🇱'},
    'pl': {'name': 'Polish', 'flag': '🇵🇱'},
    'tr': {'name': 'Turkish', 'flag': '🇹🇷'},
    'vi': {'name': 'Vietnamese', 'flag': '🇻🇳'},
    'th': {'name': 'Thai', 'flag': '🇹🇭'},
    'id': {'name': 'Indonesian', 'flag': '🇮🇩'},
}

async def translate_text(text: str, target_lang: str) -> tuple:
    """Translate using LibreTranslate API."""
    try:
        url = "https://libretranslate.com/translate"
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            payload = {
                "q": text,
                "source": "auto",
                "target": target_lang,
                "format": "text"
            }
            
            response = await client.post(url, json=payload)
            data = response.json()
            
            if 'translatedText' in data:
                return data['translatedText'], 'libretranslate'
            else:
                raise Exception("No translation returned")
                
    except Exception as e:
        logger.error(f"LibreTranslate error: {e}")
        
        # Fallback to MyMemory
        try:
            import urllib.parse
            encoded = urllib.parse.quote(text)
            url = f"https://api.mymemory.translated.net/get?q={encoded}&langpair=en|{target_lang}"
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
                data = response.json()
                
                if 'responseData' in data and 'translatedText' in data['responseData']:
                    return data['responseData']['translatedText'], 'mymemory'
        except Exception as e2:
            logger.error(f"MyMemory error: {e2}")
        
        raise Exception("All translation services failed")

async def detect_language(text: str) -> dict:
    """Detect language."""
    try:
        url = "https://libretranslate.com/detect"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {"q": text}
            response = await client.post(url, json=payload)
            data = response.json()
            
            if data and len(data) > 0:
                return {
                    'language': data[0]['language'],
                    'confidence': data[0].get('confidence', 95)
                }
    except Exception as e:
        logger.error(f"Detection error: {e}")
    
    return {'language': 'en', 'confidence': 50}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command."""
    user = update.effective_user
    
    # Create language keyboard
    keyboard = []
    row = []
    for code, lang in list(LANGUAGES.items())[:12]:
        row.append(InlineKeyboardButton(
            f"{lang['flag']} {lang['name']}",
            callback_data=f"translate_{code}"
        ))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("🌐 More", callback_data="more_languages"),
        InlineKeyboardButton("🔍 Detect", callback_data="auto_detect"),
        InlineKeyboardButton("❓ Help", callback_data="help")
    ])
    
    await update.message.reply_text(
        f"🌟 *Welcome {user.first_name}!*\n\n"
        f"Send me text and choose a language to translate!\n"
        f"🌍 {len(LANGUAGES)} languages supported\n\n"
        f"*Commands:* /help /languages",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Help command."""
    await update.message.reply_text(
        "🤖 *Language57 Translator Bot*\n\n"
        "1️⃣ Send any text\n"
        "2️⃣ Click a language button\n"
        "3️⃣ Get translation!\n\n"
        "*Commands:*\n"
        "/start - Restart\n"
        "/help - This help\n"
        "/languages - All languages\n"
        "/en - Translate to English\n"
        "/es - Translate to Spanish\n"
        "/fr - Translate to French",
        parse_mode='Markdown'
    )

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all languages."""
    text = "🌍 *All Languages:*\n\n"
    for code, lang in LANGUAGES.items():
        text += f"{lang['flag']} `/{code}` "
    await update.message.reply_text(text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if not text:
        return
    
    # Store text
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['last_text'] = text
    
    # Quick translation buttons
    quick = ['en', 'es', 'fr', 'de', 'zh-cn', 'ja', 'ar', 'ru']
    keyboard = []
    row = []
    for code in quick:
        lang = LANGUAGES[code]
        row.append(InlineKeyboardButton(
            f"{lang['flag']}",
            callback_data=f"translate_{code}"
        ))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("🌐 All Languages", callback_data="more_languages"),
        InlineKeyboardButton("🔍 Detect", callback_data="auto_detect")
    ])
    
    preview = text[:100] + "..." if len(text) > 100 else text
    await update.message.reply_text(
        f"📝 *Text:* {preview}\n\n"
        f"📊 Words: {len(text.split())} | Characters: {len(text)}\n\n"
        f"👇 *Choose language:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def show_translation(update: Update, context: ContextTypes.DEFAULT_TYPE, target_lang: str) -> None:
    """Show translation."""
    user_id = update.effective_user.id
    text = user_data.get(user_id, {}).get('last_text')
    
    if not text:
        await update.message.reply_text("❌ No text! Send a message first.")
        return
    
    await update.message.chat.send_action(action="typing")
    
    try:
        translated, service = await translate_text(text, target_lang)
        lang_name = LANGUAGES[target_lang]['name']
        
        await update.message.reply_text(
            f"✅ *{lang_name}*\n\n"
            f"📝 {translated}\n\n"
            f"⚡ {service.upper()}",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text("❌ Translation failed. Try again.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == 'help':
        await query.edit_message_text(
            "📖 Send text → Choose language → Get translation!",
            parse_mode='Markdown'
        )
        return
    
    elif data == 'more_languages':
        keyboard = []
        row = []
        for code, lang in LANGUAGES.items():
            row.append(InlineKeyboardButton(
                lang['flag'],
                callback_data=f"translate_{code}"
            ))
            if len(row) == 6:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
        
        await query.edit_message_text(
            "🌍 *Select language:*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return
    
    elif data == 'back':
        text = user_data.get(user_id, {}).get('last_text')
        if text:
            await handle_message(update, context)
        else:
            await start(update, context)
        return
    
    elif data == 'auto_detect':
        text = user_data.get(user_id, {}).get('last_text')
        if not text:
            await query.edit_message_text("❌ No text to detect!")
            return
        
        result = await detect_language(text)
        lang_name = LANGUAGES.get(result['language'], {}).get('name', result['language'])
        
        await query.edit_message_text(
            f"🔍 *Detected:* {lang_name}\n"
            f"📊 Confidence: {result['confidence']:.1f}%\n\n"
            f"💡 Click a flag to translate!",
            parse_mode='Markdown'
        )
        return
    
    elif data.startswith('translate_'):
        target = data.replace('translate_', '')
        text = user_data.get(user_id, {}).get('last_text')
        
        if not text:
            await query.edit_message_text("❌ No text!")
            return
        
        await query.message.chat.send_action(action="typing")
        
        try:
            translated, service = await translate_text(text, target)
            lang_name = LANGUAGES[target]['name']
            
            await query.edit_message_text(
                f"✅ *{lang_name}*\n\n"
                f"📝 {translated[:500]}\n\n"
                f"⚡ {service.upper()}",
                parse_mode='Markdown'
            )
        except Exception as e:
            await query.edit_message_text("❌ Translation failed.")

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE, target: str) -> None:
    """Handle /en, /es commands."""
    user_id = update.effective_user.id
    
    if context.args:
        text = ' '.join(context.args)
        user_data[user_id] = {'last_text': text}
    else:
        text = user_data.get(user_id, {}).get('last_text')
    
    if not text:
        await update.message.reply_text(
            f"📝 Use: `/{target} [text to translate]`",
            parse_mode='Markdown'
        )
        return
    
    await show_translation(update, context, target)

def main():
    """Main function."""
    logger.info("🚀 Starting bot...")
    
    # Create app
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("languages", languages_command))
    
    for code in LANGUAGES.keys():
        app.add_handler(
            CommandHandler(
                code,
                lambda u, c, lang=code: translate_command(u, c, lang)
            )
        )
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Start
    logger.info("✅ Bot is running! Waiting for messages...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
