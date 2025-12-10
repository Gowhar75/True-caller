import logging
import os
import requests
import asyncio
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiohttp import web

# --- CONFIGURATION ---
API_TOKEN = os.getenv('TELEGRAM_TOKEN')
NUMVERIFY_KEY = os.getenv('NUMVERIFY_KEY') # Still needed for phone numbers
PORT = int(os.getenv('PORT', 8080))

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- FUNCTION 1: PHONE LOOKUP (NumVerify) ---
def get_phone_metadata(phone_number):
    if not NUMVERIFY_KEY:
        return "⚠️ Error: NUMVERIFY_KEY is missing in settings."

    url = f"https://api.apilayer.com/number_verification/validate?number={phone_number}"
    headers = {"apikey": NUMVERIFY_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # Fallback to legacy URL if needed
        if "error" in data or "message" in data:
             legacy_url = f"http://apilayer.net/api/validate?access_key={NUMVERIFY_KEY}&number={phone_number}"
             response = requests.get(legacy_url)
             data = response.json()

        if data.get('valid') is True:
            return (
                f"📱 **PHONE REPORT**\n"
                f"✅ **Valid Number**\n"
                f"🏳️ **Country:** {data.get('country_name')} ({data.get('country_code')})\n"
                f"📍 **Location:** {data.get('location')}\n"
                f"🏢 **Carrier:** {data.get('carrier')}\n"
                f"📞 **Line Type:** {data.get('line_type')}"
            )
        elif data.get('valid') is False:
             return f"❌ This number is invalid."
        else:
            return f"⚠️ API Error: {data}"

    except Exception as e:
        return f"⚠️ System Error: {str(e)}"

# --- FUNCTION 2: IP LOOKUP (IP-API) ---
def get_ip_metadata(ip_address):
    # Free API, no key required for basic usage
    url = f"http://ip-api.com/json/{ip_address}?fields=status,message,country,countryCode,regionName,city,zip,isp,org,as,query"
    
    try:
        response = requests.get(url)
        data = response.json()

        if data.get('status') == 'success':
            return (
                f"💻 **IP ADDRESS REPORT**\n"
                f"🌍 **IP:** `{data.get('query')}`\n"
                f"🏳️ **Country:** {data.get('country')} ({data.get('countryCode')})\n"
                f"🏙️ **City:** {data.get('city')}, {data.get('regionName')}\n"
                f"📮 **Zip Code:** {data.get('zip')}\n"
                f"🏢 **ISP:** {data.get('isp')}\n"
                f"🏢 **Org:** {data.get('org')}"
            )
        else:
            return f"❌ Invalid IP or Private Network ({data.get('message')})"
    except Exception as e:
        return f"⚠️ IP Lookup Error: {str(e)}"

# --- COMMANDS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_msg = (
        "🤖 **Bot is Ready!**\n\n"
        "1️⃣ Send a **Phone Number** (e.g., `+919999999999`) to check Carrier/Location.\n"
        "2️⃣ Send an **IP Address** (e.g., `8.8.8.8`) to check ISP/City."
    )
    await message.answer(welcome_msg, parse_mode="Markdown")

@dp.message()
async def check_input(message: types.Message):
    text = message.text.strip()
    
    # LOGIC: Check if it looks like a phone number or an IP
    # A phone number usually starts with + or has 10-15 digits
    # An IP address usually has dots like 192.168.1.1
    
    if text.startswith("+") or (text.isdigit() and len(text) > 9):
        # ---> It's a PHONE NUMBER
        status_msg = await message.answer("🔍 Detecting Phone Number... ⏳")
        result = await asyncio.to_thread(get_phone_metadata, text)
        await status_msg.edit_text(result, parse_mode="Markdown")
        
    elif re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", text):
        # ---> It's an IP ADDRESS
        status_msg = await message.answer("🌍 Tracking IP Address... ⏳")
        result = await asyncio.to_thread(get_ip_metadata, text)
        await status_msg.edit_text(result, parse_mode="Markdown")
        
    else:
        await message.answer(
            "⚠️ I didn't understand that.\n"
            "- For Phones: Start with + (e.g., +1...)\n"
            "- For IPs: Use dots (e.g., 1.1.1.1)"
        )

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
