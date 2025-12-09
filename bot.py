import logging
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command

# --- CONFIGURATION ---
API_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
NUMVERIFY_KEY = 'YOUR_NUMVERIFY_API_KEY'

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def get_phone_metadata(phone_number):
    """
    Queries Numverify for legitimate carrier and line type data.
    Does NOT retrieve personal names.
    """
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
                # Note: 'line_type' is useful for spotting spammers (often 'voip')
            )
        else:
            return "❌ Invalid number or API limit reached."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello! Send me a phone number (with country code, e.g., +15550199) to check its carrier and location.")

@dp.message()
async def check_number(message: types.Message):
    phone_number = message.text.strip()
    
    # Basic validation to ensure it looks like a number
    if phone_number.startswith("+") and phone_number[1:].isdigit():
        await message.answer("Checking database... ⏳")
        result = get_phone_metadata(phone_number)
        await message.answer(result, parse_mode="Markdown")
    else:
        await message.answer("Please send the number in International Format (e.g., +14155552671).")

if __name__ == '__main__':
    import asyncio
    asyncio.run(dp.start_polling(bot))
