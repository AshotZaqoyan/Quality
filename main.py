import discord
from discord.ext import commands
from utils.logger import setup_logger
from config.settings import DISCORD_TOKEN, CHANNEL_ID, WEBHOOK_URL
from database.db_manager import DatabaseManager
from services.openai_service import OpenAIService
from utils.helpers import MessageHelper, WebhookLogger

# Setup
logger = setup_logger(__name__)
db = DatabaseManager()
openai_service = OpenAIService()
message_helper = MessageHelper()
webhook_logger = WebhookLogger()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logger.info(f'{bot.user} բոտը պատրաստ է!')
    logger.info(f'Հետևում է ալիքին: {CHANNEL_ID}')
    
    # Cleanup old logs (1 month)
    db.cleanup_old_logs(30)
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} slash command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    # Skip bot messages
    if message.author.bot:
        return
    
    # Only work in specified channel
    if message.channel.id != CHANNEL_ID:
        return
    
    # Process commands first
    await bot.process_commands(message)
    
    # Collect attachment URLs
    attachment_urls = [att.url for att in message.attachments]
    
    logger.info(f"New message from {message.author.name} (ID: {message.author.id}): {message.content[:100]}...")
    
    # Send to OpenAI
    result, processing_time = await openai_service.analyze_message(message.content)
    
    if result is None:
        logger.error("OpenAI API error - logging as failed processing")
        db.log_message_event(
            str(message.id), str(message.author.id), message.author.name,
            str(message.channel.id), str(message.guild.id),
            message.content, attachment_urls,
            ai_status="error", action_taken="none", processing_time=processing_time
        )
        return
    
    status = result.get("status")
    feedback = result.get("feedback", "")
    
    logger.info(f"OpenAI result for message {message.id}: {status}")
    
    # Handle non-approved messages
    # Handle non-approved messages
    if status != "approve":
        logger.warning(f"Message {message.id} rejected/needs_edit: {status}")
        
        # Send DM
        dm_sent = await message_helper.send_dm_with_feedback(
            message.author, feedback, message.content, message.attachments
        )
        
        # Log actions
        action_taken = f"DM:{'sent' if dm_sent else 'failed'}"
        
        # Send webhook log
        await webhook_logger.send_log(
            WEBHOOK_URL, str(message.id), str(message.channel.id),
            message.author.name, status, feedback, message.content
        )
        
        db.log_message_event(
            str(message.id), str(message.author.id), message.author.name,
            str(message.channel.id), str(message.guild.id),
            message.content, attachment_urls,
            ai_status=status, ai_feedback=feedback,
            action_taken=action_taken, processing_time=processing_time
        )

    else:
        logger.info(f"Message {message.id} approved")
        
        # Send webhook log
        await webhook_logger.send_log(
            WEBHOOK_URL, str(message.id), str(message.channel.id),
            message.author.name, status
        )
        
        db.log_message_event(
            str(message.id), str(message.author.id), message.author.name,
            str(message.channel.id), str(message.guild.id),
            message.content, attachment_urls,
            ai_status=status, ai_feedback=feedback,
            action_taken="approved", processing_time=processing_time
        )

# Admin commands - slash commands only for admins
@bot.tree.command(name="stats", description="Օգտատիրոջ մոդերացիայի վիճակագրությունը")
@discord.app_commands.describe(
    user="Օգտատերը (ընտրովի)",
    days="Օրերի քանակը (ենթադրությամբ 30)"
)
async def user_stats(interaction: discord.Interaction, user: discord.Member = None, days: int = 30):
    """Օգտատիրոջ վիճակագրությունը ցույց տալ - միայն ադմիններին"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Միայն ադմինները կարող են օգտագործել այս հրամանը:", ephemeral=True)
        return
    
    if user is None:
        user = interaction.user
    
    stats = db.get_user_stats(str(user.id), days)
    
    embed = discord.Embed(
        title=f"📊 {user.display_name}-ի վիճակագրություն",
        description=f"Վերջին {days} օրվա ընթացքում",
        color=0x00ff00
    )
    
    embed.add_field(name="📝 Ընդհանուր նամակներ", value=stats['total'], inline=True)
    embed.add_field(name="✅ Հաստատված", value=stats['approved'], inline=True)
    embed.add_field(name="❌ Մերժված", value=stats['rejected'], inline=True)
    embed.add_field(name="⚠️ Խմբագրման կարիք", value=stats['needs_edit'], inline=True)
    
    if stats['total'] > 0:
        approval_rate = (stats['approved'] / stats['total']) * 100
        embed.add_field(name="📈 Հաստատման տոկոս", value=f"{approval_rate:.1f}%", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="logs", description="Վերջին մոդերացիայի գրառումները")
@discord.app_commands.describe(limit="Գրառումների քանակը (ենթադրությամբ 10)")
async def recent_logs(interaction: discord.Interaction, limit: int = 10):
    """Վերջին logs-երը ցույց տալ - միայն ադմիններին"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Միայն ադմինները կարող են օգտագործել այս հրամանը:", ephemeral=True)
        return
    
    if limit > 25:  # Discord embed limit
        limit = 25
    
    logs = db.get_recent_logs(limit)
    
    if not logs:
        await interaction.response.send_message("📋 Logs չկան", ephemeral=True)
        return
    
    embed = discord.Embed(title="📋 Վերջին գործողություններ", color=0x0099ff)
    
    for username, status, timestamp, content in logs:
        status_emoji = {"approve": "✅", "reject": "❌", "needs_edit": "⚠️", "error": "🔴"}.get(status, "❓")
        embed.add_field(
            name=f"{status_emoji} {username}",
            value=f"{timestamp}\n{content}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Error handling for slash commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Դուք չունեք բավարար իրավունքներ այս հրամանը կատարելու համար:", ephemeral=True)
    else:
        logger.error(f"Slash command error: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ Հրամանի կատարման ժամանակ սխալ տեղի ունեցավ:", ephemeral=True)

# Error handling for regular commands (if any remain)
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Դուք չունեք բավարար իրավունքներ այս հրամանը կատարելու համար:")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("❌ Հրամանի կատարման ժամանակ սխալ տեղի ունեցավ:")

if __name__ == "__main__":
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Bot startup error: {e}")