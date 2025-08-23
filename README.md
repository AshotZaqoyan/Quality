# 📘 Quality Deployment Guide

This guide explains how to run the Quality Discord AI moderation bot persistently across different systems, and how to deploy it reliably on a Linux server. This bot uses OpenAI API for content moderation and requires proper environment configuration.

---

## 🧪 Local Development (Testing)

### ✅ Mac/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

### ✅ Windows (CMD):

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### ⚠️ Note:

- Make sure your `.env` file is present and filled with valid credentials.
- Keep the terminal open during testing — the bot will shut down if closed.

---

## 🚀 Production Deployment (Linux Server)

### Recommended Tool: `systemd`

> Best for permanent background service on any Linux distribution (Ubuntu, Debian, Arch, etc.)

### 1. Create a virtual environment:

```bash
cd /path/to/quality-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Create a systemd service:

```bash
sudo nano /etc/systemd/system/quality.service
```

Paste this:

```ini
[Unit]
Description=Quality Discord AI Moderation Bot
After=network.target

[Service]
User=your_username
WorkingDirectory=/path/to/quality-bot
ExecStart=/path/to/quality-bot/venv/bin/python3 main.py
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

> Replace `your_username` and `path/to/quality-bot` accordingly.

### 3. Enable and start the service:

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable quality
sudo systemctl start quality
```

### 4. View logs:

```bash
journalctl -u quality -f
```

### ✅ Benefits of systemd

- Bot runs **even after logout or reboot**
- Automatically restarts on crash
- Clean logging via `journalctl`

---

## 🛑 To Stop the Bot (systemd)

```bash
sudo systemctl stop quality
```

## ♻️ To Restart the Bot (systemd)

```bash
sudo systemctl restart quality
```

---

## 📋 Environment Variables Required

Make sure your `.env` file contains:

```env
# Discord Bot Configuration
DISCORD_TOKEN=your_discord_token_here
CHANNEL_ID=your_channel_id_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
ASSISTANT_ID=your_assistant_id_here

# Database Configuration
DB_FILE=moderation_logs.db

# Webhook Configuration (Optional)
WEBHOOK_URL=your_webhook_url_here

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=discord_moderator.log
```

---

## 🔧 Bot Commands

### Admin Slash Commands (Only visible to Administrators):

- `/stats [user] [days]` - Show user moderation statistics (private response)
- `/logs [limit]` - Show recent moderation logs (private response)

### Features:

- **Automatic Message Analysis** - Uses OpenAI to analyze messages
- **DM Notifications** - Sends feedback to users via DM
- **Message Deletion** - Removes inappropriate messages
- **Database Logging** - Tracks all moderation activities (1 month retention)
- **Webhook Logging** - Optional Discord webhook notifications
- **Private Admin Commands** - Slash commands only visible to administrators

---

✅ Deployment complete — Quality is now running like a service!