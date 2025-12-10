import logging
import os
import requests
import asyncio
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiohttp import web
from truecallerpy import search_phonenumber

# --- CONFIGURATION ---
API_TOKEN = os.getenv('TELEGRAM_TOKEN')
NUMVERIFY_KEY = os.getenv('NUMVERIFY_KEY')
# You must run 'truecallerpy login' in terminal to get this ID
TRUECALLER_ID = os.getenv('TRUECALLER_ID') 
PORT = int(os.getenv('PORT', 8080))

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def get_phone_metadata(phone_number):
    """
    Fetches technical data (Carrier, Location, Country) from NumVerify.
    Returns: dictionary of data OR None if error.
    """
    if not NUMVERIFY_KEY:
        return None

    url = f"https://api.apilayer.com/number_verification/validate?number={phone_number}"
    headers = {"apikey": NUMVERIFY_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # Fallback for legacy API layer if needed
        if "error" in data or "message" in data:
             legacy_url = f"http://apilayer.net/api/validate?access_key={NUMVERIFY_KEY}&number={phone_number}"
             response = requests.get(legacy_url)
             data = response.json()

        return data
    except Exception as e:
        logging.error(f"NumVerify Error: {e}")
        return None

async def get_caller_name(phone_number, country_code):
    """
    Fetches the Person/Business Name using TrueCaller.
    """
    if not TRUECALLER_ID:
        return "⚠️ (TrueCaller ID missing in Config)"

    try:
        # TrueCaller requires the number without the leading '+' usually, 
        # but the library handles it best if we just pass the ID and Country code.
        # Running in a thread because truecallerpy is synchronous
        id_str = str(TRUECALLER_ID)
        
        # Clean phone number for TrueCaller (remove +)
        clean_phone = phone_number.replace("+", "")
        
        # search_phonenumber returns a JSON result
        result = await asyncio.to_thread(
            search_phonenumber, 
            clean_phone, 
            country_code, 
            id_str
        )
        
        # Parse the result
        if result and "data" in result and len(result["data"]) > 0:
            user_data = result["data"][0]
            name = user_data.get("name", "Unknown")
            # Check if there is a verified badge or spam score
            spam_score = user_data.get("spam_score", 0)
            spam_warning = "🚨 (Spam)" if spam_score and spam_score > 10 else ""
            return f"{name} {spam_warning}"
            
        return "Unknown (Not found on TrueCaller)"
        
    except Exception as e:
        logging.error(f"TrueCaller Error: {e}")
        return "Error fetching name"

# --- COMMANDS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello! Send me a phone number (e.g., +14155552671).")

@dp.message()
async def check_number(message: types.Message):
    phone = message.text.strip()
    
    if len(phone) > 7:
        status_msg = await message.answer("Checking Database... ⏳")
        
        # 1. Get Technical Metadata (NumVerify)
        nv_data = await asyncio.to_thread(get_phone_metadata, phone)
        
        if not nv_data:
            await status_msg.edit_text("❌ Error connecting to Verification API.")
            return

        if nv_data.get('valid') is True:
            country_code = nv_data.get('country_code', 'IN') # Default to IN if missing
            
            # 2. Get Name (TrueCaller) - Needs country code from step 1 for best results
            await status_msg.edit_text("Found carrier... fetching name... 🔍")
            caller_name = await get_caller_name(phone, country_code)
            
            # 3. Formulate Response
            response_text = (
                f"👤 **Name:** {caller_name}\n"
                f"✅ **Valid Number**\n"
                f"🏳️ **Country:** {nv_data.get('country_name')} ({nv_data.get('country_code')})\n"
                f"📍 **Location:** {nv_data.get('location')}\n"
                f"🏢 **Carrier:** {nv_data.get('carrier')}\n"
                f"📞 **Line Type:** {nv_data.get('line_type')}"
            )
            await status_msg.edit_text(response_text, parse_mode="Markdown")
            
        elif nv_data.get('valid') is False:
             await status_msg.edit_text("❌ This number is invalid (according to NumVerify).")
        else:
            await status_msg.edit_text(f"⚠️ API Error: {nv_data}")
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
