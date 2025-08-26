import aiohttp
import json
import asyncio
from typing import Optional, Tuple, Dict
from utils.logger import setup_logger
from config.settings import OPENAI_API_KEY, ASSISTANT_ID

logger = setup_logger(__name__)

class OpenAIService:
    """OpenAI API service"""
    
    def __init__(self):
        self.api_key = OPENAI_API_KEY
        self.assistant_id = ASSISTANT_ID
        self.base_url = "https://api.openai.com/v1"
    
    async def analyze_message(self, message_content: str) -> Tuple[Optional[Dict], float]:
        """OpenAI Assistant-ին նամակ ուղարկել և պատասխանը ստանալ"""
        start_time = asyncio.get_event_loop().time()
        
        async with aiohttp.ClientSession() as session:
            try:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "OpenAI-Beta": "assistants=v2"
                }
                
                payload = {
                    "assistant_id": self.assistant_id,
                    "thread": {
                        "messages": [
                            {
                                "role": "user",
                                "content": message_content
                            }
                        ]
                    },
                    "temperature": 0.4,
                    "top_p": 0.8
                }
                
                logger.info(f"Sending request to OpenAI for content: {message_content[:100]}...")
                
                # Create run
                async with session.post(
                    f"{self.base_url}/threads/runs",
                    headers=headers,
                    json=payload
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"OpenAI API Error: {resp.status} - {error_text}")
                        return None, 0
                    
                    run_data = await resp.json()
                    thread_id = run_data["thread_id"]
                    run_id = run_data["id"]
                    logger.info(f"Created run {run_id} in thread {thread_id}")
                
                # Wait for completion
                result = await self._wait_for_completion(session, headers, thread_id, run_id)
                processing_time = asyncio.get_event_loop().time() - start_time
                
                if result:
                    logger.info(f"OpenAI response received in {processing_time:.2f}s")
                    return result, processing_time
                else:
                    return None, processing_time
                    
            except Exception as e:
                logger.error(f"OpenAI API unexpected error: {e}")
                return None, 0
    
    async def _wait_for_completion(self, session: aiohttp.ClientSession, headers: Dict, 
                                  thread_id: str, run_id: str, max_polls: int = 30) -> Optional[Dict]:
        """Run-ի ավարտը սպասել"""
        poll_count = 0
        
        while poll_count < max_polls:
            poll_count += 1
            
            async with session.get(
                f"{self.base_url}/threads/{thread_id}/runs/{run_id}",
                headers=headers
            ) as resp:
                run_status = await resp.json()
                status = run_status["status"]
                
                logger.debug(f"Run status check #{poll_count}: {status}")
                
                if status == "completed":
                    return await self._get_assistant_response(session, headers, thread_id)
                elif status == "failed":
                    logger.error(f"OpenAI run failed: {run_status}")
                    return None
                
                await asyncio.sleep(2)
        
        logger.error("OpenAI run timeout after maximum polls")
        return None
    
    async def _get_assistant_response(self, session: aiohttp.ClientSession, 
                                    headers: Dict, thread_id: str) -> Optional[Dict]:
        """Assistant-ի պատասխանը ստանալ"""
        async with session.get(
            f"{self.base_url}/threads/{thread_id}/messages",
            headers=headers
        ) as resp:
            messages = await resp.json()
            
            for message in messages["data"]:
                if message["role"] == "assistant":
                    content = message["content"][0]["text"]["value"]
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                        return None
        
        return None