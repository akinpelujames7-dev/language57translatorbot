# Language57 Translator Bot

A multilingual Telegram translation bot supporting 15+ languages.

## Features
- Translate text to 15+ languages
- Interactive buttons for easy translation
- Quick commands: /en, /es, /fr, etc.
- Auto-detect language
- AI-powered translations (with Gemini API)

## Deployment

### Local Development
1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Create `.env` file with your bot token
6. Run: `python bot.py`

### Railway Deployment
1. Push code to GitHub
2. Connect repository to Railway
3. Add environment variables in Railway dashboard
4. Deploy!

## Environment Variables
- `TELEGRAM_BOT_TOKEN` - Your bot token from @BotFather
- `GEMINI_API_KEY` - (Optional) Google Gemini API key for AI translations

## Commands
- `/start` - Start the bot
- `/help` - Show help
- `/languages` - List all languages
- `/{language_code}` - Quick translation

## License
MIT
