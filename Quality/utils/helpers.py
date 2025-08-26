import discord
import aiohttp
import io
from typing import List
from utils.logger import setup_logger

logger = setup_logger(__name__)

class MessageHelper:
    """Message handling utilities"""
    
    @staticmethod
    async def send_dm_with_feedback(user: discord.User, feedback_text: str, 
                                  original_content: str, original_attachments: List[discord.Attachment]):
        """Օգտատիրոջը DM ուղարկել feedback-ով"""
        try:
            # Red embed with feedback
            embed = discord.Embed(
                title="⚠️ Հաղորդագրությունը չի համապատասխանում ալիքի կանոններին",
                description=feedback_text,
                color=0xFF0000
            )
            
            # Download all attachments
            files = []
            for attachment in original_attachments:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(attachment.url) as resp:
                            if resp.status == 200:
                                data = await resp.read()
                                file = discord.File(
                                    fp=io.BytesIO(data),
                                    filename=attachment.filename
                                )
                                files.append(file)
                                logger.debug(f"Attachment downloaded: {attachment.filename}")
                except Exception as e:
                    logger.error(f"Error downloading attachment {attachment.filename}: {e}")
            
            # Send everything in one message
            await user.send(
                content=original_content or "",
                embed=embed,
                files=files if files else None
            )
            
            logger.info(f"DM sent successfully to {user.name} ({len(files)} attachments)")
            return True
            
        except discord.Forbidden:
            logger.warning(f"Cannot send DM to {user.name} (DMs disabled)")
            return False
        except Exception as e:
            logger.error(f"Error sending DM to {user.name}: {e}")
            return False

class WebhookLogger:
    """Webhook logging utilities"""
    
    @staticmethod
    async def send_log(webhook_url: str, message_id: str, channel_id: str, 
                      username: str, status: str, feedback: str = None, content: str = None):
        """Webhook-ով log ուղարկել"""
        if not webhook_url:
            return
            
        try:
            status_config = {
                "approve": {"emoji": "✅", "color": 0x00ff00, "title": "Հաստատված"},
                "reject": {"emoji": "❌", "color": 0xff0000, "title": "Մերժված"},
                "needs_edit": {"emoji": "⚠️", "color": 0xffaa00, "title": "Խմբագրման կարիք"},
                "error": {"emoji": "🔴", "color": 0x800080, "title": "Սխալ"}
            }
            
            config = status_config.get(status, {"emoji": "❓", "color": 0x808080, "title": "Անհայտ"})
            
            embed = {
                "title": f"{config['emoji']} {config['title']}",
                "color": config["color"],
                "fields": [
                    {
                        "name": "👤 Օգտատեր",
                        "value": username,
                        "inline": True
                    },
                    {
                        "name": "📍 Message ID",
                        "value": f"`{message_id}`",
                        "inline": True
                    },
                ],
                "timestamp": discord.utils.utcnow().isoformat()
            }
            
            # Add feedback if provided
            if feedback:
                if len(feedback) <= 1024:
                    embed["fields"].append({
                        "name": "💬 AI Feedback",
                        "value": feedback,
                        "inline": False
                    })
                else:
                    # Split long feedback
                    chunks = [feedback[i:i+1000] for i in range(0, len(feedback), 1000)]
                    for i, chunk in enumerate(chunks[:3]):
                        name = f"💬 AI Feedback {'(շարունակություն)' if i > 0 else ''}"
                        embed["fields"].append({
                            "name": name,
                            "value": chunk,
                            "inline": False
                        })
            
            payload = {
                "content": content,
                "embeds": [embed],
                "username": "Moderation Bot",
                "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as resp:
                    if resp.status == 204:
                        logger.debug(f"Webhook log sent successfully for message {message_id}")
                    else:
                        error_text = await resp.text()
                        logger.error(f"Webhook failed: {resp.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"Error sending webhook log: {e}")