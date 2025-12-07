"""
StreamVault Telegram Bot - With Health Check for Free Hosting

Features:
- Interactive commands (/start, /latest, /movies, /shows, /search, /help)
- AUTO-POSTS new content to channel every 30 minutes
- HTTP health check endpoint to keep free hosting alive
"""
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

import requests
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_ID,
    STREAMVAULT_API_SHOWS,
    STREAMVAULT_API_MOVIES,
    STREAMVAULT_BASE_URL,
    POSTED_CONTENT_FILE,
    CHANNEL_INVITE_LINK,
    WEBSITE_URL,
    PROMOTION_INTERVAL
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Auto-post interval in seconds (30 minutes)
AUTO_POST_INTERVAL = 1800

# Health check port
PORT = int(os.environ.get("PORT", 10000))

# Cache for content
shows_cache = []
movies_cache = []


# ==================== HEALTH CHECK SERVER ====================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'StreamVault Bot is running!')
    
    def log_message(self, format, *args):
        pass  # Suppress logs


def run_health_server():
    """Run HTTP server for health checks."""
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    logger.info(f"🏥 Health check server running on port {PORT}")
    server.serve_forever()


# ==================== HELPER FUNCTIONS ====================

def load_posted_content() -> dict:
    try:
        if Path(POSTED_CONTENT_FILE).exists():
            with open(POSTED_CONTENT_FILE, 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading posted content: {e}")
    return {"shows": [], "movies": []}


def save_posted_content(data: dict):
    with open(POSTED_CONTENT_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def fetch_content(api_url: str) -> list:
    try:
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error fetching from {api_url}: {e}")
        return []


def refresh_cache():
    global shows_cache, movies_cache
    shows_cache = fetch_content(STREAMVAULT_API_SHOWS)
    movies_cache = fetch_content(STREAMVAULT_API_MOVIES)
    logger.info(f"Cache refreshed: {len(shows_cache)} shows, {len(movies_cache)} movies")


def truncate_text(text: str, max_length: int = 200) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length-3].rsplit(' ', 1)[0] + "..."


def format_show_message(show: dict) -> str:
    title = show.get('title', 'Unknown Title')
    year = show.get('year') or show.get('releaseYear', '')
    slug = show.get('slug', '')
    description = show.get('description', 'No description available.')
    imdb_rating = show.get('imdbRating', 'N/A')
    genres = show.get('genres', 'N/A')
    language = show.get('language', 'N/A')
    total_seasons = show.get('totalSeasons', 0)
    cast = show.get('cast', '')
    
    message_parts = [
        f"📺 *{title.upper()}*" + (f" ({year})" if year else ""),
        "",
        f"⭐ {imdb_rating} │ 🎭 {genres}",
        f"🌐 {language}",
        "",
        f"📖 _{truncate_text(description)}_",
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]
    
    if total_seasons and total_seasons > 0:
        message_parts.append(f"📂 *Seasons Available:* {total_seasons}")
        message_parts.append("")
        
        season_links = []
        for s in range(1, int(total_seasons) + 1):
            watch_url = f"{STREAMVAULT_BASE_URL}/watch/{slug}?season={s}&episode=1"
            season_links.append(f"[S{s}]({watch_url})")
        
        for i in range(0, len(season_links), 5):
            row = " │ ".join(season_links[i:i+5])
            message_parts.append(f"▸ {row}")
        
        message_parts.append("")
        message_parts.append("━━━━━━━━━━━━━━━━━━━━━")
    
    if cast:
        cast_truncated = ", ".join(cast.split(", ")[:4])
        if len(cast.split(", ")) > 4:
            cast_truncated += "..."
        message_parts.extend(["", f"🎭 *Cast:* {cast_truncated}"])
    
    watch_url = f"{STREAMVAULT_BASE_URL}/shows/{slug}"
    message_parts.extend([
        "",
        f"🔗 *Watch:* [StreamVault]({watch_url})",
        f"📢 *Join:* {CHANNEL_INVITE_LINK}"
    ])
    
    return "\n".join(message_parts)


def format_movie_message(movie: dict) -> str:
    title = movie.get('title', 'Unknown Title')
    year = movie.get('year', '')
    slug = movie.get('slug', '')
    description = movie.get('description', 'No description available.')
    imdb_rating = movie.get('imdbRating', 'N/A')
    genres = movie.get('genres', 'N/A')
    language = movie.get('language', 'N/A')
    duration = movie.get('duration', '')
    cast = movie.get('cast', '')
    directors = movie.get('directors', '')
    
    message_parts = [
        f"🎬 *{title.upper()}*" + (f" ({year})" if year else ""),
        "",
        f"⭐ {imdb_rating} │ 🎭 {genres}" + (f" │ ⏱ {duration} min" if duration else ""),
        f"🌐 {language}",
        "",
        f"📖 _{truncate_text(description)}_",
        "",
        "━━━━━━━━━━━━━━━━━━━━━",
    ]
    
    if directors:
        message_parts.append(f"🎬 *Director:* {directors}")
    
    if cast:
        cast_truncated = ", ".join(cast.split(", ")[:4])
        if len(cast.split(", ")) > 4:
            cast_truncated += "..."
        message_parts.append(f"🎭 *Cast:* {cast_truncated}")
    
    message_parts.append("━━━━━━━━━━━━━━━━━━━━━")
    
    watch_url = f"{STREAMVAULT_BASE_URL}/movies/{slug}"
    message_parts.extend([
        "",
        f"🔗 *Watch:* [StreamVault]({watch_url})",
        f"📢 *Join:* {CHANNEL_INVITE_LINK}"
    ])
    
    return "\n".join(message_parts)


def format_content_list(items: list, content_type: str, limit: int = 10) -> str:
    if not items:
        return f"No {content_type} available."
    
    emoji = "📺" if content_type == "shows" else "🎬"
    lines = [f"*Latest {content_type.title()}:*", ""]
    
    for i, item in enumerate(items[:limit], 1):
        title = item.get('title', 'Unknown')
        year = item.get('year') or item.get('releaseYear', '')
        rating = item.get('imdbRating', 'N/A')
        slug = item.get('slug', '')
        url = f"{STREAMVAULT_BASE_URL}/{content_type}/{slug}"
        lines.append(f"{emoji} [{title}]({url}) ({year}) ⭐{rating}")
    
    lines.extend(["", f"📢 *Join:* {CHANNEL_INVITE_LINK}"])
    return "\n".join(lines)


# ==================== AUTO-POSTING JOB ====================

async def auto_post_job(context: ContextTypes.DEFAULT_TYPE):
    logger.info("🔄 Running auto-post job...")
    refresh_cache()
    
    posted = load_posted_content()
    posted_count = 0
    max_posts_per_run = 5
    
    for show in shows_cache:
        if posted_count >= max_posts_per_run:
            break
        show_id = show.get('id')
        if show_id in posted.get("shows", []):
            continue
        
        message = format_show_message(show)
        poster_url = show.get('posterUrl')
        
        try:
            if poster_url and poster_url.startswith('http'):
                await context.bot.send_photo(chat_id=TELEGRAM_CHANNEL_ID, photo=poster_url, caption=message, parse_mode=ParseMode.MARKDOWN)
            else:
                await context.bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message, parse_mode=ParseMode.MARKDOWN)
            
            posted["shows"].append(show_id)
            save_posted_content(posted)
            posted_count += 1
            logger.info(f"✅ Auto-posted show: {show.get('title')}")
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Error auto-posting show: {e}")
    
    for movie in movies_cache:
        if posted_count >= max_posts_per_run:
            break
        movie_id = movie.get('id')
        if movie_id in posted.get("movies", []):
            continue
        
        message = format_movie_message(movie)
        poster_url = movie.get('posterUrl')
        
        try:
            if poster_url and poster_url.startswith('http'):
                await context.bot.send_photo(chat_id=TELEGRAM_CHANNEL_ID, photo=poster_url, caption=message, parse_mode=ParseMode.MARKDOWN)
            else:
                await context.bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=message, parse_mode=ParseMode.MARKDOWN)
            
            posted["movies"].append(movie_id)
            save_posted_content(posted)
            posted_count += 1
            logger.info(f"✅ Auto-posted movie: {movie.get('title')}")
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Error auto-posting movie: {e}")
    
    if posted_count > 0:
        logger.info(f"🎉 Auto-posted {posted_count} new items!")
    else:
        logger.info("📭 No new content to post.")


# ==================== COMMAND HANDLERS ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = f"""
🎬 *Welcome to StreamVault Bot!*

Your gateway to free movies & TV shows.

━━━━━━━━━━━━━━━━━━━━━

*Commands:*
/latest - Latest movies & shows
/movies - Browse movies
/shows - Browse TV shows  
/search <query> - Search content
/random - Random recommendation
/help - Get help

━━━━━━━━━━━━━━━━━━━━━

🤖 *Auto-updates every 30 mins!*

🌐 *Website:* {WEBSITE_URL}
📢 *Channel:* {CHANNEL_INVITE_LINK}
"""
    await update.message.reply_text(welcome_message.strip(), parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_message = f"""
📖 *StreamVault Bot Help*

━━━━━━━━━━━━━━━━━━━━━

*Commands:*
/start - Welcome message
/latest - Show latest content
/movies - Browse recent movies
/shows - Browse TV shows
/search <query> - Search content
/random - Random recommendation

━━━━━━━━━━━━━━━━━━━━━

📢 *Channel:* {CHANNEL_INVITE_LINK}
🌐 *Website:* {WEBSITE_URL}
"""
    await update.message.reply_text(help_message.strip(), parse_mode=ParseMode.MARKDOWN)


async def latest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not shows_cache or not movies_cache:
        refresh_cache()
    
    latest_shows = shows_cache[:5] if shows_cache else []
    latest_movies = movies_cache[:5] if movies_cache else []
    
    message_parts = ["🆕 *Latest on StreamVault*", "", "━━━━━━━━━━━━━━━━━━━━━", "", "*📺 TV Shows:*"]
    
    for show in latest_shows:
        title = show.get('title', 'Unknown')
        slug = show.get('slug', '')
        rating = show.get('imdbRating', 'N/A')
        url = f"{STREAMVAULT_BASE_URL}/shows/{slug}"
        message_parts.append(f"▸ [{title}]({url}) ⭐{rating}")
    
    message_parts.extend(["", "*🎬 Movies:*"])
    
    for movie in latest_movies:
        title = movie.get('title', 'Unknown')
        slug = movie.get('slug', '')
        rating = movie.get('imdbRating', 'N/A')
        url = f"{STREAMVAULT_BASE_URL}/movies/{slug}"
        message_parts.append(f"▸ [{title}]({url}) ⭐{rating}")
    
    message_parts.extend(["", "━━━━━━━━━━━━━━━━━━━━━", f"📢 *Join:* {CHANNEL_INVITE_LINK}"])
    await update.message.reply_text("\n".join(message_parts), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def movies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not movies_cache:
        refresh_cache()
    message = format_content_list(movies_cache, "movies", limit=10)
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def shows_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not shows_cache:
        refresh_cache()
    message = format_content_list(shows_cache, "shows", limit=10)
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please provide a search query.\n\nExample: `/search Breaking Bad`", parse_mode=ParseMode.MARKDOWN)
        return
    
    query = " ".join(context.args).lower()
    
    if not shows_cache or not movies_cache:
        refresh_cache()
    
    matching_shows = [s for s in shows_cache if query in s.get('title', '').lower()]
    matching_movies = [m for m in movies_cache if query in m.get('title', '').lower()]
    
    if not matching_shows and not matching_movies:
        await update.message.reply_text(f"❌ No results found for: *{query}*", parse_mode=ParseMode.MARKDOWN)
        return
    
    message_parts = [f"🔍 *Results for:* _{query}_", "", "━━━━━━━━━━━━━━━━━━━━━"]
    
    if matching_shows:
        message_parts.extend(["", "*📺 TV Shows:*"])
        for show in matching_shows[:5]:
            title = show.get('title', 'Unknown')
            slug = show.get('slug', '')
            rating = show.get('imdbRating', 'N/A')
            url = f"{STREAMVAULT_BASE_URL}/shows/{slug}"
            message_parts.append(f"▸ [{title}]({url}) ⭐{rating}")
    
    if matching_movies:
        message_parts.extend(["", "*🎬 Movies:*"])
        for movie in matching_movies[:5]:
            title = movie.get('title', 'Unknown')
            slug = movie.get('slug', '')
            rating = movie.get('imdbRating', 'N/A')
            url = f"{STREAMVAULT_BASE_URL}/movies/{slug}"
            message_parts.append(f"▸ [{title}]({url}) ⭐{rating}")
    
    message_parts.extend(["", f"📢 *Join:* {CHANNEL_INVITE_LINK}"])
    await update.message.reply_text("\n".join(message_parts), parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not shows_cache or not movies_cache:
        refresh_cache()
    
    all_content = [(s, 'show') for s in shows_cache] + [(m, 'movie') for m in movies_cache]
    
    if not all_content:
        await update.message.reply_text("❌ No content available.")
        return
    
    item, content_type = random.choice(all_content)
    message = format_show_message(item) if content_type == 'show' else format_movie_message(item)
    poster = item.get('posterUrl')
    
    try:
        if poster and poster.startswith('http'):
            await update.message.reply_photo(photo=poster, caption=message, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)


async def post_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📤 Triggering content post to channel...")
    await auto_post_job(context)
    await update.message.reply_text("✅ Done!")


def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    # Start health check server in background thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    
    # Refresh cache on startup
    refresh_cache()
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("latest", latest_command))
    application.add_handler(CommandHandler("movies", movies_command))
    application.add_handler(CommandHandler("shows", shows_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("random", random_command))
    application.add_handler(CommandHandler("post", post_command))
    
    # Add job queue for auto-posting every 30 minutes
    job_queue = application.job_queue
    job_queue.run_repeating(auto_post_job, interval=AUTO_POST_INTERVAL, first=10)
    
    logger.info("🚀 StreamVault Bot started with AUTO-POSTING and HEALTH CHECK!")
    logger.info(f"📢 Channel: {TELEGRAM_CHANNEL_ID}")
    logger.info(f"🏥 Health check: http://localhost:{PORT}")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
