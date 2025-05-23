import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
from typing import List, Dict, Any
from loguru import logger

from .base_crawler import BaseCrawler, NewItem

class RssCrawler(BaseCrawler):
    """優化後的RSS訂閱源爬蟲 - 專注保險新聞"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.hours_limit = config.get('hours_limit', 24)
        
        # RSS訂閱源
        self.rss_feeds = config.get('rss_feeds', [
            # 主流財經媒體
            "https://ec.ltn.com.tw/rss/finance.xml",            # 自由時報財經
            "https://www.chinatimes.com/rss/finance.xml",       # 中國時報財經
            "https://news.cnyes.com/rss/news/cat/tw_stock",     # 鉅亨網台股
            "https://news.cnyes.com/rss/news/cat/tw_macro",     # 鉅亨網台灣總經
            "https://udn.com/rssfeed/news/2/6638?ch=news",      # 聯合報金融要聞
            "https://money.udn.com/rssfeed/news/1001/5590/12017?ch=money",  # 經濟日報財經
            "https://ctee.com.tw/feed",                         # 工商時報
            "https://www.wealth.com.tw/rss/category/4",         # 財訊快報
        ])
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        # 保險關鍵詞（按優先級排序）
        self.primary_keywords = [
            # 公司名稱（最高優先級）
            "新光人壽", "新光金控", "新光金", "台新人壽", "台新金控", "台新金",
            
            # 具體險種（高優先級）
            "健康險", "醫療險", "癌症險", "重大疾病險", "實支實付",
            "投資型保險", "投資型", "變額保險", "利變壽險", "利率變動型",
            "意外險", "傷害險", "年金險", "儲蓄險", "終身壽險"
        ]
        
        self.secondary_keywords = [
            # 保險業務詞彙
            "保險", "壽險", "理賠", "給付", "保單", "保費", "承保", "核保",
            "要保人", "被保險人", "受益人", "保險金額", "保障額度",
            "保險業", "保險公司", "保險法", "保險監理"
        ]
        
        # 排除關鍵詞
        self.exclude_keywords = [
            "股價", "股票", "配息", "除權", "除息", "股東會",
            "ETF", "基金", "債券", "匯率", "央行", "升息", "降息"
        ]
    
    def crawl(self) -> List[NewItem]:
        """爬取RSS訂閱源的新聞"""
        all_news = []
        
        for feed_url in self.rss_feeds:
            logger.info(f"📡 正在爬取RSS: {feed_url}")
            try:
                news_items = self._parse_feed(feed_url)
                all_news.extend(news_items)
                
                # 避免過度請求
                time.sleep(2)
            except Exception as e:
                logger.error(f"❌ 爬取RSS '{feed_url}' 時出錯: {str(e)}")
        
        # 進階篩選邏輯
        filtered_news = []
        logger.info(f"🔍 開始篩選 {len(all_news)} 條新聞...")
        
        for item in all_news:
            title_content = (item.title + " " + (item.content or "")).lower()
            
            # 檢查排除關鍵詞
            contains_exclude = any(exclude_word in title_content for exclude_word in self.exclude_keywords)
            if contains_exclude:
                logger.debug(f"❌ 排除新聞（包含排除關鍵詞）: {item.title[:30]}...")
                continue
            
            matched_keyword = None
            priority_score = 0
            
            # 檢查主要關鍵詞（最高優先級）
            for keyword in self.primary_keywords:
                if keyword in item.title or (item.content and keyword in item.content):
                    matched_keyword = keyword
                    priority_score = 10
                    break
            
            # 檢查次要關鍵詞
            if not matched_keyword:
                for keyword in self.secondary_keywords:
                    if keyword in item.title or (item.content and keyword in item.content):
                        matched_keyword = keyword
                        priority_score = 5
                        break
            
            # 檢查原始搜尋關鍵詞
            if not matched_keyword:
                for term in self.search_terms:
                    if term in item.title or (item.content and term in item.content):
                        matched_keyword = term
                        priority_score = 1
                        break
            
            if matched_keyword:
                item.keyword = matched_keyword
                item.priority_score = priority_score
                filtered_news.append(item)
                logger.info(f"✅ 符合關鍵詞 '{matched_keyword}' (優先級:{priority_score}): {item.title[:40]}...")
        
        logger.info(f"🎯 篩選完成，剩餘 {len(filtered_news)} 條相關新聞")
        
        # 按優先級和時間排序
        sorted_news = sorted(filtered_news, key=lambda x: (-getattr(x, 'priority_score', 0), -x.published_time.timestamp()))
        return sorted_news[:15]  # 返回前15條最相關的新聞
    
    def _parse_feed(self, feed_url: str) -> List[NewItem]:
        """解析RSS訂閱源"""
        news_items = []
        
        try:
            # 設置User-Agent
            feedparser.USER_AGENT = self.headers["User-Agent"]
            
            # 解析RSS訂閱源
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                logger.warning(f"⚠️ RSS訂閱源可能有格式問題: {feed_url}")
            
            feed_title = feed.feed.title if hasattr(feed.feed, 'title') else "未知來源"
            logger.info(f"📰 正在處理 {feed_title} 的 {len(feed.entries)} 條新聞")
            
            processed_count = 0
            insurance_related_count = 0
            
            for entry in feed.entries:
                try:
                    # 獲取標題和連結
                    title = entry.title if hasattr(entry, 'title') else ""
                    url = entry.link if hasattr(entry, 'link') else ""
                    
                    if not title or not url:
                        continue
                    
                    processed_count += 1
                    
                    # 預篩選：只處理包含保險相關詞彙的標題
                    title_lower = title.lower()
                    contains_insurance_keyword = any(keyword in title_lower for keyword in [
                        "保險", "壽險", "新光", "台新", "理賠", "保單", "保費", 
                        "健康險", "意外險", "醫療險", "投保", "承保", "給付",
                        "投資型", "利變", "年金", "儲蓄險", "重大疾病", "癌症險"
                    ])
                    
                    # 如果標題不包含保險相關詞彙，跳過
                    if not contains_insurance_keyword:
                        continue
                    
                    insurance_related_count += 1
                    logger.debug(f"🎯 發現保險相關新聞: {title[:50]}...")
                    
                    # 獲取發布時間
                    pub_time = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            pub_time = datetime(*entry.published_parsed[:6])
                        except:
                            pass
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        try:
                            pub_time = datetime(*entry.updated_parsed[:6])
                        except:
                            pass
                    
                    # 檢查時間限制
                    hours_diff = (datetime.now() - pub_time).total_seconds() / 3600
                    logger.debug(f"📅 新聞時間: {pub_time}, 距現在: {hours_diff:.1f} 小時")
                    
                    if hours_diff > self.hours_limit:
                        logger.debug(f"⏰ 跳過，超出時間限制: {self.hours_limit} 小時")
                        continue
                    
                    # 獲取內容
                    content = ""
                    if hasattr(entry, 'content') and entry.content:
                        content = entry.content[0].value
                    elif hasattr(entry, 'summary'):
                        content = entry.summary
                    elif hasattr(entry, 'description'):
                        content = entry.description
                    
                    # 如果內容是HTML，清理為純文本
                    if content and "<" in content:
                        soup = BeautifulSoup(content, 'html.parser')
                        content = soup.get_text()
                    
                    # 如果內容為空或太短，嘗試從原始頁面獲取
                    if not content or len(content) < 50:
                        content = self._get_article_content(url)
                    
                    # 清理標題
                    title = title.replace('\n', ' ').replace('\r', ' ').strip()
                    title = ''.join(char for char in title if ord(char) < 65536)
                    
                    # 創建新聞項目
                    news_item = NewItem(
                        title=title,
                        content=content,
                        url=url,
                        published_time=pub_time,
                        source=feed_title,
                        keyword=""
                    )
                    
                    news_items.append(news_item)
                    logger.debug(f"✅ 成功解析RSS條目: {title[:30]}...")
                    
                except Exception as e:
                    logger.warning(f"⚠️ 解析RSS條目時出錯: {str(e)}")
            
            logger.info(f"📊 {feed_title}: 處理了{processed_count}條新聞，找到{insurance_related_count}條保險相關，成功解析{len(news_items)}條")
            
        except Exception as e:
            logger.error(f"❌ 解析RSS訂閱源 '{feed_url}' 時出錯: {str(e)}")
        
        return news_items
    
    def _get_article_content(self, url: str) -> str:
        """獲取文章內容"""
        try:
            # 設置延遲，避免被封鎖
            time.sleep(1)
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            # 自動檢測編碼
            if response.apparent_encoding:
                response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 移除腳本和樣式標籤
            for script in soup(["script", "style", "iframe", "ins", ".ad", ".ads"]):
                script.extract()
            
            # 嘗試多種內容選擇器
            content_selectors = [
                "div.article-content", 
                "div.article-body",
                "div.story-content",
                "div.news-content",
                "div.cont",
                "div.content",
                "article",
                "main",
                ".news-detail",
                ".article",
                ".post-content",
                ".entry-content"
            ]
            
            content_text = ""
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    content_text = content_element.get_text(separator="\n").strip()
                    if len(content_text) > 100:
                        break
            
            # 如果找不到內容，使用更通用的方法
            if not content_text or len(content_text) < 100:
                # 移除頭部、底部等無關元素
                for element in soup.select("header, footer, nav, aside, .sidebar, .ads, .ad"):
                    element.extract()
                
                content_text = soup.get_text(separator="\n").strip()
                lines = [line.strip() for line in content_text.splitlines() if line.strip()]
                content_text = "\n".join(lines)
            
            # 清理文本
            if content_text:
                content_text = content_text.replace('\n', ' ').replace('\r', ' ').strip()
                content_text = ''.join(char for char in content_text if ord(char) < 65536)
            
            return content_text
            
        except Exception as e:
            logger.warning(f"⚠️ 獲取文章內容時出錯: {str(e)}")
            return "無法獲取文章內容"
