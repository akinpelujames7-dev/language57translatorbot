import os
import logging
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

# Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Validate required environment variables
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is required!")

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store user data
user_data = {}

# Supported languages with flags and names
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
    """Translate text using LibreTranslate API."""
    try:
        # LibreTranslate API (free, no key needed)
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
                raise Exception("Translation failed")
                
    except Exception as e:
        logger.error(f"Translation error: {e}")
        
        # Try MyMemory API as fallback
        try:
            import urllib.parse
            encoded_text = urllib.parse.quote(text)
            url = f"https://api.mymemory.translated.net/get?q={encoded_text}&langpair=en|{target_lang}"
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
                data = response.json()
                
                if 'responseData' in data and 'translatedText' in data['responseData']:
                    return data['responseData']['translatedText'], 'mymemory'
        except Exception as e2:
            logger.error(f"MyMemory translation failed: {e2}")
        
        raise Exception("All translation services failed")

async def detect_language(text: str) -> dict:
    """Detect language using LibreTranslate."""
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
            else:
                return {'language': 'en', 'confidence': 50}
                
    except Exception as e:
        logger.error(f"Detection error: {e}")
        return {'language': 'en', 'confidence': 50}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message."""
    user = update.effective_user
    welcome_text = f"""
🌟 *Welcome to Language57 Translator Bot, {user.first_name}!*

I'm your free multilingual translation assistant!

📝 *How to use:*
1. Send me any text message
2. Click a language button below
3. I'll translate it instantly!

🌍 *Supported Languages:* {len(LANGUAGES)}
⚡ *Free & No API Key Required*
🔒 *Your privacy is respected*

*Send me a message to start!* 🚀
    """
    
    # Create language keyboard (3 per row)
    keyboard = []
    row = []
    for code, lang in list(LANGUAGES.items())[:12]:  # Show first 12 languages
        button_text = f"{lang['flag']} {lang['name']}"
        row.append(InlineKeyboardButton(button_text, callback_data=f"translate_{code}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Add more languages button and utilities
    keyboard.append([
        InlineKeyboardButton("🌐 More Languages", callback_data="more_languages"),
        InlineKeyboardButton("🔍 Auto-Detect", callback_data="auto_detect"),
        InlineKeyboardButton("❓ Help", callback_data="help")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    logger.info(f"User {user.id} started the bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message."""
    help_text = """
🤖 *Language57 Translator Bot Help*

*📝 How to use:*
1. Send any text message
2. Click a language button to translate
3. Get instant translation!

*⌨️ Quick Commands:*
• /start - Restart the bot
• /help - Show this help
• /languages - List all languages
• /en - Translate to English
• /es - Translate to Spanish
• /fr - Translate to French

*💡 Tips:*
• Your text is not stored permanently
• Works with any language
• Free to use!

*Enjoy translating!* 🌍
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all languages."""
    lang_list = ""
    for code, lang in LANGUAGES.items():
        lang_list += f"{lang['flag']} {lang['name']} - `/{code}`\n"
    
    await update.message.reply_text(
        f"🌍 *All {len(LANGUAGES)} Languages:*\n\n{lang_list}",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Store message and show translation options."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if not text:
        await update.message.reply_text("⚠️ Please send a text message.")
        return
    
    # Store the message
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['last_text'] = text
    user_data[user_id]['last_update'] = datetime.now().isoformat()
    
    # Create quick translation buttons (most common)
    quick_langs = ['en', 'es', 'fr', 'de', 'zh-cn', 'ja', 'ar', 'ru', 'pt', 'it']
    keyboard = []
    row = []
    for code in quick_langs:
        lang = LANGUAGES[code]
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
        InlineKeyboardButton("🔍 Auto-Detect", callback_data="auto_detect"),
        InlineKeyboardButton("🌐 All Languages", callback_data="more_languages")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Show preview
    preview = text[:100] + "..." if len(text) > 100 else text
    await update.message.reply_text(
        f"📝 *Your text:*\n{preview}\n\n"
        f"📊 *Words:* {len(text.split())} | *Characters:* {len(text)}\n\n"
        f"👇 *Choose a language:*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_translation(update: Update, context: ContextTypes.DEFAULT_TYPE, target_lang: str) -> None:
    """Show translation."""
    user_id = update.effective_user.id
    text = user_data.get(user_id, {}).get('last_text')
    
    if not text:
        await update.message.reply_text("❌ No text found! Send a message first.")
        return
    
    # Send typing indicator
    await update.message.chat.send_action(action="typing")
    
    try:
        translated_text, service = await translate_text(text, target_lang)
        lang_name = LANGUAGES[target_lang]['name']
        
        response = f"""
✅ *Translation to {lang_name}*

📝 *Original:* 
`{text}`

🔄 *Translated:* 
`{translated_text}`

📊 *Service:* {service.upper()}
        """
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"Translated for user {user_id}: {target_lang}")
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await update.message.reply_text(
            "❌ *Translation Failed*\n\n"
            "Could not translate. Please try:\n"
            "• Sending shorter text\n"
            "• Trying again later",
            parse_mode='Markdown'
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == 'help':
        await query.edit_message_text(
            "📖 *Help*\n\nSend text → Choose language → Get translation!\nUse /help for all commands.",
            parse_mode='Markdown'
        )
        return
    
    elif data == 'more_languages':
        # Show all languages as buttons
        keyboard = []
        row = []
        for code, lang in LANGUAGES.items():
            row.append(InlineKeyboardButton(
                f"{lang['flag']}",
                callback_data=f"translate_{code}"
            ))
            if len(row) == 6:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🌍 *Select a language:*\n(Click a flag to translate)",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    elif data == 'back':
        # Go back to main menu
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
        
        try:
            result = await detect_language(text)
            lang_name = LANGUAGES.get(result['language'], {}).get('name', result['language'])
            
            await query.edit_message_text(
                f"🔍 *Language Detection*\n\n"
                f"📝 Text: `{text[:100]}`\n"
                f"🌐 Language: {lang_name}\n"
                f"📊 Confidence: {result['confidence']:.1f}%\n\n"
                f"💡 Click a language button to translate!",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Detection error: {e}")
            await query.edit_message_text("❌ Could not detect language.")
        return
    
    elif data.startswith('translate_'):
        target_lang = data.replace('translate_', '')
        text = user_data.get(user_id, {}).get('last_text')
        
        if not text:
            await query.edit_message_text("❌ No text to translate!")
            return
        
        await query.message.chat.send_action(action="typing")
        
        try:
            translated_text, service = await translate_text(text, target_lang)
            lang_name = LANGUAGES[target_lang]['name']
            
            response = f"""
✅ *Translation to {lang_name}*

📝 *Original:* 
`{text[:200]}`

🔄 *Translated:* 
`{translated_text[:200]}`

📊 *Service:* {service.upper()}
            """
            
            await query.edit_message_text(response, parse_mode='Markdown')
            logger.info(f"Button translation: {target_lang}")
            
        except Exception as e:
            logger.error(f"Translation error: {e}")
            await query.edit_message_text("❌ Translation failed. Try again.")

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE, target_lang: str) -> None:
    """Handle translation commands."""
    user_id = update.effective_user.id
    
    # Check if text is in command
    if context.args:
        text = ' '.join(context.args)
        user_data[user_id] = {'last_text': text}
    else:
        text = user_data.get(user_id, {}).get('last_text')
    
    if not text:
        await update.message.reply_text(
            f"📝 Send text first or use: `/{target_lang} [text]`",
            parse_mode='Markdown'
        )
        return
    
    await show_translation(update, context, target_lang)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Error: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred. Please try again."
        )

def main() -> None:
    """Start the bot."""
    logger.info("🚀 Starting Language57 Translator Bot...")
    logger.info(f"📊 Languages: {len(LANGUAGES)}")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("languages", languages_command))
    
    # Add translation commands
    for code in LANGUAGES.keys():
        application.add_handler(
            CommandHandler(
                code,
                lambda update, context, lang=code: translate_command(update, context, lang)
            )
        )
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    
    # Start
    logger.info("✅ Bot is ready!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
