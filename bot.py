import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from googletrans import Translator
from dotenv import load_dotenv
import requests
import json

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Optional, for AI translations

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize translator
translator = Translator()

# Store user's last message
user_last_message = {}

# Language mapping
LANGUAGES = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'zh-cn': 'Chinese (Simplified)',
    'ja': 'Japanese',
    'ar': 'Arabic',
    'hi': 'Hindi',
    'ko': 'Korean',
    'nl': 'Dutch',
    'pl': 'Polish',
    'tr': 'Turkish'
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message with language selection buttons."""
    user = update.effective_user
    welcome_text = f"""
👋 *Hello {user.first_name}!*

I'm *Language57 Translator Bot* - your multilingual translation assistant!

📝 *How to use me:*
1. Send me any text message
2. Choose a language from the buttons below
3. I'll translate it instantly!

💡 *Supported Features:*
• 15+ Languages
• Quick translation buttons
• Command shortcuts: /en, /es, /fr, etc.
• AI-powered translations (with Gemini API)

*Just send me a message and pick a language!* 🌐
    """
    
    # Create keyboard with language buttons (2 per row)
    keyboard = []
    row = []
    for code, name in LANGUAGES.items():
        row.append(InlineKeyboardButton(name, callback_data=f'translate_{code}'))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Add special buttons
    keyboard.append([
        InlineKeyboardButton("🔄 Auto-Detect", callback_data='auto_detect'),
        InlineKeyboardButton("ℹ️ Help", callback_data='help')
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message."""
    help_text = """
🤖 *Language57 Translator Bot Help*

*Basic Usage:*
1. Send me any text message
2. Click a language button to translate
3. Or use commands like /en, /es, /fr

*Commands:*
/start - Start the bot
/help - Show this help
/en - Translate to English
/es - Translate to Spanish
/fr - Translate to French
/de - Translate to German
/it - Translate to Italian
/pt - Translate to Portuguese
/ru - Translate to Russian
/zh - Translate to Chinese
/ja - Translate to Japanese
/ar - Translate to Arabic
/hi - Translate to Hindi
/ko - Translate to Korean

*Tips:*
• You can also use inline mode: @language57translatorbot [text]
• Multiple messages are supported - just send new text!
• Try clicking the auto-detect button for smart translations

*Enjoy translating!* 🌍
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Store the user's last message and suggest translation."""
    user_id = update.effective_user.id
    text = update.message.text
    
    if not text:
        await update.message.reply_text("Please send a text message to translate.")
        return
    
    # Store the message
    user_last_message[user_id] = text
    
    # Create quick translation buttons
    keyboard = [
        [
            InlineKeyboardButton("🇬🇧 English", callback_data='translate_en'),
            InlineKeyboardButton("🇪🇸 Spanish", callback_data='translate_es'),
            InlineKeyboardButton("🇫🇷 French", callback_data='translate_fr')
        ],
        [
            InlineKeyboardButton("🇩🇪 German", callback_data='translate_de'),
            InlineKeyboardButton("🇮🇹 Italian", callback_data='translate_it'),
            InlineKeyboardButton("🇵🇹 Portuguese", callback_data='translate_pt')
        ],
        [
            InlineKeyboardButton("🇷🇺 Russian", callback_data='translate_ru'),
            InlineKeyboardButton("🇨🇳 Chinese", callback_data='translate_zh-cn'),
            InlineKeyboardButton("🇯🇵 Japanese", callback_data='translate_ja')
        ],
        [
            InlineKeyboardButton("🇸🇦 Arabic", callback_data='translate_ar'),
            InlineKeyboardButton("🇮🇳 Hindi", callback_data='translate_hi'),
            InlineKeyboardButton("🇰🇷 Korean", callback_data='translate_ko')
        ],
        [
            InlineKeyboardButton("🌐 More Languages", callback_data='more_languages'),
            InlineKeyboardButton("🔄 Auto-Detect", callback_data='auto_detect')
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Show preview of the text
    preview = text[:50] + "..." if len(text) > 50 else text
    await update.message.reply_text(
        f"📝 *Your text:* {preview}\n\nChoose a language to translate to:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def translate_to(update: Update, context: ContextTypes.DEFAULT_TYPE, target_lang: str) -> None:
    """Translate the user's last message to the target language."""
    user_id = update.effective_user.id
    text = user_last_message.get(user_id)
    
    if not text:
        await update.message.reply_text(
            "❌ No text found! Please send me a message first."
        )
        return
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    try:
        # Try translation with googletrans
        translated = translator.translate(text, dest=target_lang)
        lang_name = LANGUAGES.get(target_lang, target_lang)
        
        response = f"""
✅ *Translation ({lang_name}):*

📝 *Original:* 
{text}

🔄 *Translated:*
{translated.text}

💡 *Detected source language:* {translated.src}
"""
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        
        # Try Gemini API if available
        if GEMINI_API_KEY:
            try:
                gemini_translation = await translate_with_gemini(text, target_lang)
                lang_name = LANGUAGES.get(target_lang, target_lang)
                
                response = f"""
✅ *Translation ({lang_name}) - AI Powered:*

📝 *Original:* 
{text}

🔄 *Translated:*
{gemini_translation}

🤖 *Powered by Google Gemini AI*
"""
                await update.message.reply_text(response, parse_mode='Markdown')
                return
            except Exception as gemini_error:
                logger.error(f"Gemini translation error: {gemini_error}")
        
        await update.message.reply_text(
            "❌ Sorry, translation failed. Please try again later."
        )

async def translate_with_gemini(text: str, target_lang: str) -> str:
    """Translate text using Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"Translate the following text to {LANGUAGES.get(target_lang, target_lang)}. Only return the translation, nothing else:\n\n{text}"
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    data = response.json()
    return data['candidates'][0]['content']['parts'][0]['text']

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == 'help':
        help_text = """
🤖 *Language57 Translator Bot*

• Send me text and click a language button
• Use commands like /en, /es, /fr
• Try auto-detect for smart translation!
• Supports 15+ languages

*Commands:*
/start - Restart bot
/help - Show help
/languages - List all languages
"""
        await query.edit_message_text(help_text, parse_mode='Markdown')
        return
    
    if data == 'more_languages':
        # Show all languages
        lang_list = "\n".join([f"• {name} - `/{code}`" for code, name in LANGUAGES.items()])
        await query.edit_message_text(
            f"🌍 *All Supported Languages:*\n\n{lang_list}\n\nUse `/{code}` to translate instantly!",
            parse_mode='Markdown'
        )
        return
    
    if data == 'auto_detect':
        text = user_last_message.get(user_id)
        if not text:
            await query.edit_message_text("❌ No text found! Please send me a message first.")
            return
        
        try:
            # Detect language
            detection = translator.detect(text)
            lang_name = LANGUAGES.get(detection.lang, detection.lang)
            
            await query.edit_message_text(
                f"🔍 *Language Detection Result:*\n\n"
                f"📝 *Your text:* {text[:100]}...\n"
                f"🌐 *Detected language:* {lang_name}\n"
                f"📊 *Confidence:* {detection.confidence:.2%}\n\n"
                f"💡 Use the buttons above to translate to another language!",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Detection error: {e}")
            await query.edit_message_text("❌ Could not detect the language. Please try again.")
        return
    
    # Handle translation
    if data.startswith('translate_'):
        target_lang = data.replace('translate_', '')
        text = user_last_message.get(user_id)
        
        if not text:
            await query.edit_message_text("❌ No text found! Please send me a message first.")
            return
        
        # Show typing indicator
        await query.message.chat.send_action(action="typing")
        
        try:
            translated = translator.translate(text, dest=target_lang)
            lang_name = LANGUAGES.get(target_lang, target_lang)
            
            response = f"""
✅ *Translation ({lang_name}):*

📝 *Original:* 
{text}

🔄 *Translated:*
{translated.text}

💡 *Detected source:* {translated.src}
"""
            await query.edit_message_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Translation error: {e}")
            await query.edit_message_text("❌ Translation failed. Please try again.")
        return

# Command handlers for quick translation
async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE, target_lang: str) -> None:
    """Handle translation commands like /en, /es, etc."""
    await translate_to(update, context, target_lang)

async def languages_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all supported languages."""
    lang_list = "\n".join([f"• {name} - `/{code}`" for code, name in LANGUAGES.items()])
    await update.message.reply_text(
        f"🌍 *All Supported Languages:*\n\n{lang_list}\n\nUse `/{code}` to translate instantly!",
        parse_mode='Markdown'
    )

def main() -> None:
    """Start the bot."""
    # Validate token
    if not BOT_TOKEN:
        logger.error("No BOT_TOKEN found! Please set TELEGRAM_BOT_TOKEN environment variable.")
        return
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("languages", languages_command))
    
    # Add translation commands for each language
    for code in LANGUAGES.keys():
        application.add_handler(
            CommandHandler(code, lambda update, context, lang=code: translate_command(update, context, lang))
        )
    
    # Register message and callback handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Start the Bot
    logger.info("Language57 Translator Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
