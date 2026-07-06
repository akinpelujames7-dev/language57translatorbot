import os
import logging
import asyncio
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
import requests
import json
import httpx

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Optional

# Validate required environment variables
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is required! Set it in .env file or Railway variables.")

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
    'zh-cn': {'name': 'Chinese (Simplified)', 'flag': '🇨🇳'},
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

# Translation function using LibreTranslate API (free, no API key needed)
async def translate_text(text: str, target_lang: str) -> tuple:
    """Translate text using LibreTranslate API (free, no API key)."""
    try:
        # Use LibreTranslate free API
        url = "https://libretranslate.com/translate"
        
        # Detect source language
        detect_url = "https://libretranslate.com/detect"
        detect_payload = {"q": text}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Detect language
            detect_response = await client.post(detect_url, json=detect_payload)
            detect_data = detect_response.json()
            source_lang = detect_data[0]['language'] if detect_data else 'en'
            
            # Translate
            payload = {
                "q": text,
                "source": source_lang,
                "target": target_lang,
                "format": "text"
            }
            
            response = await client.post(url, json=payload)
            data = response.json()
            
            if 'translatedText' in data:
                return data['translatedText'], source_lang, 'libretranslate'
            else:
                raise Exception("Translation failed")
                
    except Exception as e:
        logger.warning(f"LibreTranslate failed: {e}")
        
        # Try Gemini API as fallback if available
        if GEMINI_API_KEY:
            try:
                gemini_text = await translate_with_gemini(text, target_lang)
                return gemini_text, 'unknown', 'gemini'
            except Exception as gemini_error:
                logger.error(f"Gemini translation failed: {gemini_error}")
        
        # Try MyMemory API as last resort
        try:
            url = f"https://api.mymemory.translated.net/get?q={text}&langpair=en|{target_lang}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                data = response.json()
                if 'responseData' in data and 'translatedText' in data['responseData']:
                    return data['responseData']['translatedText'], 'en', 'mymemory'
        except Exception as e:
            logger.error(f"MyMemory translation failed: {e}")
        
        raise Exception("All translation services failed")

async def translate_with_gemini(text: str, target_lang: str) -> str:
    """Translate using Google Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""Translate the following text to {LANGUAGES[target_lang]['name']}. 
Return only the translated text, nothing else.
Do not add any explanations or quotes.

Text: {text}

Translation:"""
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 500
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if 'candidates' in data and len(data['candidates']) > 0:
                return data['candidates'][0]['content']['parts'][0]['text'].strip()
            else:
                raise Exception("No translation generated")
    except Exception as e:
        logger.error(f"Gemini API request failed: {e}")
        raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message with language selection."""
    user = update.effective_user
    welcome_text = f"""
🌟 *Welcome to Language57 Translator Bot, {user.first_name}!*

I'm your multilingual translation assistant. Here's how to use me:

📝 *How it works:*
1. Send me any text message
2. Click a language button below
3. I'll translate it instantly!

🎯 *Features:*
• {len(LANGUAGES)} Languages supported
• Quick translation buttons
• Auto-detect source language
• Command shortcuts
• Free translation API

🚀 *Quick Commands:*
/help - Show all commands
/languages - List all languages
/en - Translate to English
/es - Translate to Spanish
/fr - Translate to French

*Send me a message and let's translate!* 🌐
    """
    
    # Create keyboard with languages (3 per row)
    keyboard = []
    row = []
    for code, lang in LANGUAGES.items():
        button_text = f"{lang['flag']} {lang['name']}"
        row.append(InlineKeyboardButton(button_text, callback_data=f"translate_{code}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Add utility buttons
    keyboard.append([
        InlineKeyboardButton("🔄 Auto-Detect", callback_data="auto_detect"),
        InlineKeyboardButton("❓ Help", callback_data="help"),
        InlineKeyboardButton("📊 Stats", callback_data="stats")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    logger.info(f"User {user.id} started the bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send detailed help message."""
    help_text = """
🤖 *Language57 Translator Bot Help*

*📝 Basic Usage:*
1. Send any text message
2. Click a language button to translate
3. Get instant translation!

*⌨️ Quick Commands:*
"""
    # Add language commands (first 10 to avoid message too long)
    count = 0
    for code, lang in LANGUAGES.items():
        if count < 10:
            help_text += f"/{code} - Translate to {lang['name']}\n"
            count += 1
    help_text += f"... and {len(LANGUAGES) - 10} more languages! Use /languages to see all.\n\n"
    
    help_text += """
*💡 Tips:*
• Use auto-detect to identify languages
• Multiple messages supported
• Your privacy is respected - no data stored

*Need help? Contact support*
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all supported languages."""
    lang_list = ""
    for code, lang in LANGUAGES.items():
        lang_list += f"{lang['flag']} {lang['name']} - `/{code}`\n"
    
    await update.message.reply_text(
        f"🌍 *Supported Languages ({len(LANGUAGES)}):*\n\n{lang_list}\n\nUse `/{code}` for quick translation!",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Store message and show translation options."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if not text:
        await update.message.reply_text("⚠️ Please send a text message to translate.")
        return
    
    # Store the message
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['last_text'] = text
    user_data[user_id]['last_update'] = datetime.now().isoformat()
    
    # Create quick translation buttons (most common languages)
    quick_languages = ['en', 'es', 'fr', 'de', 'zh-cn', 'ja', 'ar', 'ru', 'pt', 'it']
    keyboard = []
    row = []
    for code in quick_languages:
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
        InlineKeyboardButton("🌐 All Languages", callback_data="all_languages")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Show preview
    preview = text[:100] + "..." if len(text) > 100 else text
    await update.message.reply_text(
        f"📝 *Your text:*\n{preview}\n\n"
        f"🔢 *Word count:* {len(text.split())}\n"
        f"📏 *Character count:* {len(text)}\n\n"
        f"👇 *Choose a language to translate to:*",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_translation(update: Update, context: ContextTypes.DEFAULT_TYPE, target_lang: str) -> None:
    """Show translation to user."""
    user_id = update.effective_user.id
    text = user_data.get(user_id, {}).get('last_text')
    
    if not text:
        await update.message.reply_text("❌ No text found! Please send me a message first.")
        return
    
    # Send typing indicator
    await update.message.chat.send_action(action="typing")
    
    try:
        translated_text, source_lang, service = await translate_text(text, target_lang)
        lang_name = LANGUAGES[target_lang]['name']
        
        # Format response
        response = f"""
✅ *Translation to {lang_name}*

📝 *Original:* 
`{text}`

🔄 *Translated:* 
`{translated_text}`

📊 *Details:*
• Service: {service.upper()}
• Words: {len(translated_text.split())}
• Characters: {len(translated_text)}
        """
        
        await update.message.reply_text(response, parse_mode='Markdown')
        logger.info(f"Translated for user {user_id}: {target_lang}")
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await update.message.reply_text(
            "❌ *Translation Failed*\n\n"
            "I couldn't translate your text. Please try:\n"
            "• Sending shorter text\n"
            "• Using different language\n"
            "• Trying again later\n\n"
            "If the problem persists, contact support.",
            parse_mode='Markdown'
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all button presses."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    # Handle different button actions
    if data == 'help':
        await query.edit_message_text(
            "📖 *Help Center*\n\n"
            "Send me text and choose a language!\n"
            "Use /help for all commands.",
            parse_mode='Markdown'
        )
        return
    
    elif data == 'stats':
        user_text = user_data.get(user_id, {}).get('last_text')
        if user_text:
            stats = f"""
📊 *Your Stats*

• Last text: {user_text[:50]}...
• Words: {len(user_text.split())}
• Characters: {len(user_text)}
• Languages available: {len(LANGUAGES)}
            """
        else:
            stats = "📊 No translation history yet. Send me some text!"
        await query.edit_message_text(stats, parse_mode='Markdown')
        return
    
    elif data == 'auto_detect':
        text = user_data.get(user_id, {}).get('last_text')
        if not text:
            await query.edit_message_text("❌ No text to detect! Send me a message first.")
            return
        
        try:
            # Use LibreTranslate detect
            url = "https://libretranslate.com/detect"
            payload = {"q": text}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                data = response.json()
                
                if data and len(data) > 0:
                    detected_lang = data[0]['language']
                    confidence = data[0].get('confidence', 95)
                    lang_name = LANGUAGES.get(detected_lang, {}).get('name', detected_lang)
                    
                    await query.edit_message_text(
                        f"🔍 *Language Detection Results*\n\n"
                        f"📝 *Text:*\n`{text[:200]}`\n\n"
                        f"🌐 *Detected Language:* {lang_name}\n"
                        f"📊 *Confidence:* {confidence:.1f}%\n"
                        f"🔢 *Words:* {len(text.split())}\n\n"
                        f"💡 Click a language button above to translate!",
                        parse_mode='Markdown'
                    )
                else:
                    await query.edit_message_text("❌ Could not detect language. Please try again.")
        except Exception as e:
            logger.error(f"Detection error: {e}")
            await query.edit_message_text("❌ Could not detect language. Please try again.")
        return
    
    elif data == 'all_languages':
        # Show all languages
        lang_list = ""
        for code, lang in LANGUAGES.items():
            lang_list += f"{lang['flag']} `/{code}` "
        await query.edit_message_text(
            f"🌍 *All {len(LANGUAGES)} Languages*\n\n"
            f"{lang_list}\n\n"
            f"Use `/{code}` for quick translation!",
            parse_mode='Markdown'
        )
        return
    
    # Handle translation
    elif data.startswith('translate_'):
        target_lang = data.replace('translate_', '')
        text = user_data.get(user_id, {}).get('last_text')
        
        if not text:
            await query.edit_message_text("❌ No text to translate! Send me a message first.")
            return
        
        # Send typing indicator
        await query.message.chat.send_action(action="typing")
        
        try:
            translated_text, source_lang, service = await translate_text(text, target_lang)
            lang_name = LANGUAGES[target_lang]['name']
            
            response = f"""
✅ *Translation to {lang_name}*

📝 *Original:* 
`{text[:300]}`{'...' if len(text) > 300 else ''}

🔄 *Translated:* 
`{translated_text[:300]}`{'...' if len(translated_text) > 300 else ''}

📊 *Service:* {service.upper()}
            """
            
            await query.edit_message_text(response, parse_mode='Markdown')
            logger.info(f"Button translation for user {user_id}: {target_lang}")
            
        except Exception as e:
            logger.error(f"Translation error: {e}")
            await query.edit_message_text(
                "❌ Translation failed. Please try again or use a different language.",
                parse_mode='Markdown'
            )

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE, target_lang: str) -> None:
    """Handle translation commands (/en, /es, etc.)."""
    user_id = update.effective_user.id
    text = user_data.get(user_id, {}).get('last_text')
    
    if not text:
        # Check if text is in command arguments
        if context.args:
            text = ' '.join(context.args)
            user_data[user_id] = {'last_text': text}
        else:
            await update.message.reply_text(
                "📝 Please send me a text message first, or use:\n"
                f"`/{target_lang} [text to translate]`",
                parse_mode='Markdown'
            )
            return
    
    await show_translation(update, context, target_lang)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred. Please try again later.\n"
            "If the problem persists, contact support."
        )

def main() -> None:
    """Start the bot."""
    logger.info("🚀 Starting Language57 Translator Bot...")
    logger.info(f"📊 Languages supported: {len(LANGUAGES)}")
    logger.info(f"🤖 Bot username: @language57translatorbot")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("languages", languages_command))
    
    # Add translation command handlers for each language
    for code in LANGUAGES.keys():
        application.add_handler(
            CommandHandler(
                code,
                lambda update, context, lang=code: translate_command(update, context, lang)
            )
        )
    
    # Add message and callback handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot with polling
    logger.info("✅ Bot is ready and polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
