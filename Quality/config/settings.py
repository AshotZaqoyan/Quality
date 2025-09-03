import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', 0))

# OpenAI Configuration  
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ASSISTANT_ID = os.getenv('ASSISTANT_ID')

# Database Configuration
DB_FILE = os.getenv('DB_FILE', 'moderation_logs.db')

# Webhook Configuration
WEBHOOK_URL = os.getenv('WEBHOOK_URL')

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'discord_moderator.log')

# Validation
required_vars = [
    ('DISCORD_TOKEN', DISCORD_TOKEN),
    ('CHANNEL_ID', CHANNEL_ID),
    ('OPENAI_API_KEY', OPENAI_API_KEY),
    ('ASSISTANT_ID', ASSISTANT_ID)
]

missing_vars = [var_name for var_name, var_value in required_vars if not var_value]

if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")