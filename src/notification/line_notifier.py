from typing import Dict, Any, List
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError
from loguru import logger

class LineNotifier:
    """Line通知類"""
    
    def __init__(self, config: Dict[str, Any]):
        self.channel_access_token = config.get('channel_access_token')
        self.max_message_length = config.get('max_message_length', 2000)
        
        if not self.channel_access_token:
            logger.warning("未設置Line Channel Access Token")
        
        self.line_bot_api = LineBotApi(self.channel_access_token) if self.channel_access_token else None
    
    def send_news_summary(self, news_items: List[Dict[str, Any]]) -> bool:
        """使用廣播發送新聞摘要到所有好友"""
        if not self.line_bot_api:
            logger.error("Line配置不完整，無法發送消息")
            return False
        
        if not news_items:
            logger.info("沒有新聞項目可發送")
            return True
        
        try:
            # 按照優先順序拼接消息
            message = self._build_message(news_items)
            
            # 確保消息不超過Line的最大長度限制
            if len(message) > self.max_message_length:
                message = message[:self.max_message_length - 3] + "..."
                logger.warning(f"消息內容超過Line限制，已截斷至{self.max_message_length}字符")
            
            # 使用廣播發送消息給所有好友
            self.line_bot_api.broadcast(TextSendMessage(text=message))
            
            logger.info("成功發送Line廣播通知")
            return True
            
        except LineBotApiError as e:
            logger.error(f"發送Line廣播消息時出錯: {str(e)}")
            return False
    
    def _build_message(self, news_items: List[Dict[str, Any]]) -> str:
        """構建Line消息內容"""
        message_parts = ["📰 今日金融保險新聞摘要\n"]
        
        for item in news_items:
            # 添加新聞項目，格式：標題 + 摘要 + 來源
            news_part = (
                f"【{item['keyword']}】{item['title']}\n"
                f"{item['summary']}\n"
                f"來源: {item['source']} | {item['url'][:50]}...\n\n"
            )
            
            # 檢查是否會超過Line的最大長度限制
            if len(''.join(message_parts) + news_part) > self.max_message_length:
                message_parts.append("更多新聞因長度限制未顯示...")
                break
            
            message_parts.append(news_part)
        
        return ''.join(message_parts)
