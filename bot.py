import logging
import os
import requests
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiohttp import web

# --- CONFIGURATION FROM ENVIRONMENT VARIABLES ---
# We use os.getenv to read secrets from Render's settings
API_TOKEN = os.getenv('TELEGRAM_TOKEN')
NUMVERIFY_KEY = os.getenv('NUMVERIFY_KEY')
PORT = int(os.getenv('PORT', 8080)) # Render provides a PORT automatically

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- HELPER FUNCTIONS ---
def get_phone_metadata(phone_number):
    if not NUMVERIFY_KEY:
        return "⚠️ Error: Numverify API Key is missing in settings."
        
    url = f"http://apilayer.net/api/validate?access_key={NUMVERIFY_KEY}&number={phone_number}"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get('valid'):
            return (
                f"✅ **Valid Number**\n"
                f"🏳️ **Country:** {data.get('country_name')} ({data.get('country_code')})\n"
                f"📍 **Location:** {data.get('location')}\n"
                f"🏢 **Carrier:** {data.get('carrier')}\n"
                f"📞 **Line Type:** {data.get('line_type')}"
            )
        else:
            return "❌ Invalid number or API limit reached."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# --- BOT COMMANDS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello! Send me a phone number (e.g., +15550199) to check its carrier.")

@dp.message()
async def check_number(message: types.Message):
    phone_number = message.text.strip()
    if phone_number.startswith("+") and phone_number[1:].isdigit():
        await message.answer("Checking database... ⏳")
        result = get_phone_metadata(phone_number)
        await message.answer(result, parse_mode="Markdown")
    else:
        await message.answer("Please send the number in International Format (e.g., +14155552671).")

# --- DUMMY WEB SERVER FOR RENDER ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

# --- MAIN ENTRY POINT ---
async def main():
    # Start the dummy web server so Render thinks we are a website
    await start_web_server()
    # Start the bot polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
