import logging
import os
import requests
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiohttp import web

# --- CONFIGURATION ---
API_TOKEN = os.getenv('TELEGRAM_TOKEN')
NUMVERIFY_KEY = os.getenv('NUMVERIFY_KEY')
PORT = int(os.getenv('PORT', 8080))

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def get_phone_metadata(phone_number):
    if not NUMVERIFY_KEY:
        return "⚠️ Error: API Key is missing."

    # --- TRY APILAYER METHOD (Newer) ---
    # Most new accounts come from APILayer.com and need this specific format
    url = f"https://api.apilayer.com/number_verification/validate?number={phone_number}"
    headers = {"apikey": NUMVERIFY_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # If APILayer fails (e.g., using old legacy key), try the old URL
        if "error" in data or "message" in data:
             # Fallback to Legacy Method (http://apilayer.net)
             legacy_url = f"http://apilayer.net/api/validate?access_key={NUMVERIFY_KEY}&number={phone_number}"
             response = requests.get(legacy_url)
             data = response.json()

        # Check if valid
        if data.get('valid') is True:
            return (
                f"✅ **Valid Number**\n"
                f"🏳️ **Country:** {data.get('country_name')} ({data.get('country_code')})\n"
                f"📍 **Location:** {data.get('location')}\n"
                f"🏢 **Carrier:** {data.get('carrier')}\n"
                f"📞 **Line Type:** {data.get('line_type')}"
            )
        elif data.get('valid') is False:
             return f"❌ This number is invalid (according to the database)."
        else:
            # This prints the ACTUAL error from the server so we can debug
            return f"⚠️ API Error Details: {data}"

    except Exception as e:
        return f"⚠️ System Error: {str(e)}"

# --- COMMANDS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello! Send me a phone number (e.g., +14155552671).")

@dp.message()
async def check_number(message: types.Message):
    phone = message.text.strip()
    if len(phone) > 7:  # Basic length check
        await message.answer("Checking... ⏳")
        result = get_phone_metadata(phone)
        await message.answer(result, parse_mode="Markdown")
    else:
        await message.answer("Please send a valid international number (e.g., +1...)")

# --- SERVER ---
async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
