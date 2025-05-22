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
        
        if not self.channel_access_token or self.channel_access_token == "YOUR_LINE_CHANNEL_ACCESS_TOKEN":
            logger.warning("未設置Line Channel Access Token")
        
        self.line_bot_api = LineBotApi(self.channel_access_token) if self.channel_access_token and self.channel_access_token != "YOUR_LINE_CHANNEL_ACCESS_TOKEN" else None
    
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
        message_parts = [f"📰 今日金融保險新聞摘要 ({len(news_items)}則)\n\n"]
        
        for i, item in enumerate(news_items, 1):
            # 清理標題，移除亂碼
            title = item['title']
            if title:
                title = ''.join(char for char in title if ord(char) < 65536)
                title = title.replace('\n', ' ').replace('\r', ' ').strip()
            
            # 添加新聞項目，格式：編號 + 關鍵詞 + 標題 + 摘要 + 來源
            news_part = (
                f"{i}. 【{item['keyword']}】\n"
                f"{title}\n"
                f"💬 {item['summary']}\n"
                f"📰 {item['source']}\n"
                f"🔗 {item['url'][:60]}{'...' if len(item['url']) > 60 else ''}\n\n"
            )
            
            # 檢查是否會超過Line的最大長度限制
            if len(''.join(message_parts) + news_part) > self.max_message_length:
                message_parts.append(f"⚠️ 還有 {len(news_items) - i + 1} 則新聞因長度限制未顯示...")
                break
            
            message_parts.append(news_part)
        
        # 添加時間戳
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        message_parts.append(f"\n⏰ 更新時間：{timestamp}")
        
        return ''.join(message_parts)
