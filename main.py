import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import aiohttp
from bs4 import BeautifulSoup

# Configuration
TELEGRAM_BOT_TOKEN = "8096659923:AAHxofi8SZ6RXH25WcWjdkfthe7Ze35RPhQ"  # Replace with your bot token
TELEGRAM_CHAT_ID = "7845216034"  # Replace with your chat ID
WEBSITE_URL = "https://shop.royalchallengers.com/ticket"  # URL to monitor
CHECK_INTERVAL = 60  # Check every 1 minute

# Store the previous status
previous_status = None

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def fetch_website_content():
    """Fetch the HTML content of the website."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(WEBSITE_URL, timeout=10) as response:
                return await response.text() if response.status == 200 else None
    except Exception as e:
        logger.error(f"Error fetching website: {e}")
        return None

def extract_ticket_status(html_content):
    """Extracts the ticket availability status from the HTML."""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        button = soup.find("button", class_="chakra-button css-19lydhp")
        return button.text.strip() if button else "No button found"
    except Exception as e:
        logger.error(f"Error parsing website content: {e}")
        return None

def extract_full_container(html_content):
    """Extracts the full ticket container content."""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        container = soup.find("div", class_="chakra-container")
        return container.get_text(separator="\n").strip() if container else "No container found."
    except Exception as e:
        logger.error(f"Error extracting container: {e}")
        return "Error extracting container."

async def send_telegram_notification(message: str, application):
    """Sends a notification message to a Telegram chat."""
    try:
        await application.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f"Telegram notification sent: {message}")
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")

async def check_command(update: Update, context: CallbackContext):
    """Handles the /check command."""
    await update.message.reply_text("✅ Bot is running and monitoring the website!")

async def scrap_command(update: Update, context: CallbackContext):
    """Handles the /scrap command."""
    content = await fetch_website_content()
    if content:
        scraped_data = extract_full_container(content)
        await update.message.reply_text(f"📜 Scraped Container Content:\n\n{scraped_data}")
    else:
        await update.message.reply_text("❌ Error: Failed to fetch website content.")

async def monitor_website(application):
    """Monitors the website for changes."""
    global previous_status
    logger.info("Starting website change monitor...")
    while True:
        content = await fetch_website_content()
        if content:
            current_status = extract_ticket_status(content)
            if current_status is None:
                logger.info("Could not detect ticket status. Retrying...")
            elif previous_status is None:
                previous_status = current_status
                logger.info(f"Initial status detected: {previous_status}")
            elif current_status != previous_status:
                logger.info(f"🚨 Ticket status changed! New status: {current_status}")
                await send_telegram_notification(
                    f"🚨 Ticket status changed!\n\nNew status: {current_status}\nURL: {WEBSITE_URL}",
                    application
                )
                previous_status = current_status
            else:
                logger.info(f"No changes detected. Current status: {current_status}")
        await asyncio.sleep(CHECK_INTERVAL)

async def start_bot():
    """Main bot startup function."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    try:
        # Register handlers
        application.add_handler(CommandHandler("check", check_command))
        application.add_handler(CommandHandler("scrap", scrap_command))

        # Initialize and start
        await application.initialize()
        await application.start()
        
        # Start monitoring task
        monitoring_task = asyncio.create_task(monitor_website(application))
        
        logger.info("✅ Bot started. Use /check to verify it's running.")
        
        # Keep the application running
        await application.updater.idle()
        
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        # Proper cleanup
        if monitoring_task and not monitoring_task.done():
            monitoring_task.cancel()
        if application.running:
            await application.stop()
            await application.shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")