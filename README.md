# StreamVault Telegram Bot

Automatically posts movies and TV shows from StreamVault.live to Telegram.

## Features
- 🤖 Interactive commands (/start, /latest, /movies, /shows, /search, /random)
- ⏰ Auto-posts new content every 30 minutes
- 📺 Modern formatting with season links
- 📢 Channel promotion

## Setup

1. Create a `.env` file:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=@streamvaultt
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run:
```bash
python telegram_bot.py
```

## Deploy to Render (Free Hosting)

1. Push code to GitHub
2. Go to [render.com](https://render.com) and connect your GitHub
3. Create a new **Background Worker**
4. Add environment variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`
5. Deploy!

## Bot Commands
- `/start` - Welcome message
- `/latest` - Latest content
- `/movies` - Browse movies
- `/shows` - Browse TV shows
- `/search <query>` - Search
- `/random` - Random recommendation
- `/post` - Manually trigger posting
