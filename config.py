"""Configuration settings for the StreamVault Telegram Bot."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@streamvaultt")

# StreamVault Configuration
STREAMVAULT_BASE_URL = os.getenv("STREAMVAULT_BASE_URL", "https://streamvault.live")
STREAMVAULT_API_SHOWS = f"{STREAMVAULT_BASE_URL}/api/shows"
STREAMVAULT_API_MOVIES = f"{STREAMVAULT_BASE_URL}/api/movies"

# File paths
POSTED_CONTENT_FILE = "posted_content.json"

# Promotion Settings
CHANNEL_INVITE_LINK = os.getenv("CHANNEL_INVITE_LINK", "https://t.me/streamvaultt")
WEBSITE_URL = os.getenv("WEBSITE_URL", "https://streamvault.live")
PROMOTION_INTERVAL = int(os.getenv("PROMOTION_INTERVAL", "10"))  # Post promotion every N content posts
