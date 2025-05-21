import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
from typing import List, Dict, Any
from loguru import logger

from .base_crawler import BaseCrawler, NewItem

class RssCrawler(BaseCrawler):
    """RSS 訂閱源爬蟲"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.hours_limit = config.get('hours_limit', 24)  # 預設限制24小時
        self.rss_feeds = config.get('rss_feeds', [
            # 預設的金融相關 RSS 訂閱源
            "https://ec.ltn.com.tw/rss/finance.xml",            # 自由時報財經
            "https://www.chinatimes.com/rss/finance.xml",       # 中國時報財經
            "https://news.cnyes.com/rss/news/cat/tw_stock",     # 鉅亨網台股
            "https://news.cnyes.com/rss/news/cat/tw_macro",     # 鉅亨網台灣總經
            "https://udn.com/rssfeed/news/2/6638?ch=news",      # 聯合報金融要聞
            "https://www.wealth.com.tw/rss/category/4",         # 財訊快報
        ])
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }
    
    def crawl(self) -> List[NewItem]:
        """爬取 RSS 訂閱源的新聞"""
        all_news = []
        
        for feed_url in self.rss_feeds:
            logger.info(f"爬取 RSS 訂閱源: {feed_url}")
            try:
                news_items = self._parse_feed(feed_url)
                all_news.extend(news_items)
                
                # 避免過度請求，增加延遲
                time.sleep(1)
            except Exception as e:
                logger.error(f"爬取 RSS 訂閱源 '{feed_url}' 時出錯: {str(e)}")
        
        # 修改：放寬關鍵詞匹配邏輯，使用部分匹配而不是完全匹配
        filtered_news = []
        for item in all_news:
            for term in self.search_terms:
                # 檢查標題或內容中是否包含關鍵詞（部分匹配）
                if (term in item.title or 
                    (item.content and term in item.content) or 
                    (item.source and term in item.source)):
                    
                    item.keyword = term  # 設置關鍵詞
                    filtered_news.append(item)
                    logger.info(f"符合關鍵詞 '{term}' 的新聞: {item.title[:30]}...")
                    break
        
        logger.info(f"過濾後剩餘 {len(filtered_news)} 條相關新聞")
        
        # 根據優先順序排序
        sorted_news = self.sort_by_priority(filtered_news)
        return sorted_news
    
    def _parse_feed(self, feed_url: str) -> List[NewItem]:
        """解析 RSS 訂閱源"""
        news_items = []
        
        try:
            # 解析 RSS 訂閱源
            feed = feedparser.parse(feed_url)
            
            feed_title = feed.feed.title if hasattr(feed.feed, 'title') else "未知來源"
            
            for entry in feed.entries:
                try:
                    # 獲取標題和連結
                    title = entry.title
                    url = entry.link
                    
                    # 獲取發布時間
                    pub_time = datetime.now()
                    if hasattr(entry, 'published_parsed'):
                        try:
                            pub_time = datetime(*entry.published_parsed[:6])
                        except:
                            pass
                    elif hasattr(entry, 'updated_parsed'):
                        try:
                            pub_time = datetime(*entry.updated_parsed[:6])
                        except:
                            pass
                    
                    # 僅保留時間範圍內的新聞
                    hours_diff = (datetime.now() - pub_time).total_seconds() / 3600
                    logger.debug(f"新聞時間: {pub_time}, 距現在: {hours_diff:.1f} 小時")
                    
                    if hours_diff > self.hours_limit:
                        logger.debug(f"跳過，超出時間限制: {self.hours_limit} 小時")
                        continue
                    
                    # 獲取內容
                    content = ""
                    if hasattr(entry, 'content'):
                        content = entry.content[0].value
                    elif hasattr(entry, 'summary'):
                        content = entry.summary
                    elif hasattr(entry, 'description'):
                        content = entry.description
                    
                    # 如果內容是 HTML，清理為純文本
                    if content and "<" in content:
                        soup = BeautifulSoup(content, 'html.parser')
                        content = soup.get_text()
                    
                    # 如果內容為空，嘗試從原始頁面獲取
                    if not content:
                        content = self._get_article_content(url)
                    
                    # 創建新聞項目 (暫時將關鍵詞設為空，後續會根據內容設置)
                    news_item = NewItem(
                        title=title,
                        content=content,
                        url=url,
                        published_time=pub_time,
                        source=feed_title,
                        keyword=""
                    )
                    
                    news_items.append(news_item)
                    logger.debug(f"成功解析RSS條目: {title[:30]}...")
                    
                except Exception as e:
                    logger.warning(f"解析 RSS 條目時出錯: {str(e)}")
            
        except Exception as e:
            logger.error(f"解析 RSS 訂閱源 '{feed_url}' 時出錯: {str(e)}")
        
        return news_items
    
    def _get_article_content(self, url: str) -> str:
        """獲取文章內容"""
        try:
            # 使用更簡單的方式獲取內容
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # 使用Beautiful Soup解析頁面
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除腳本和樣式標籤
            for script in soup(["script", "style"]):
                script.extract()
            
            # 獲取所有文本
            text = soup.get_text()
            
            # 清理文本
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.warning(f"獲取文章內容時出錯: {str(e)}")
            return "無法獲取文章內容"
