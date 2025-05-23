import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
from typing import List, Dict, Any
from urllib.parse import urljoin
from loguru import logger
import chardet

from .base_crawler import BaseCrawler, NewItem

class FinanceNewsDirectCrawler(BaseCrawler):
    """放寬條件的財經新聞直接爬蟲"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.hours_limit = config.get('hours_limit', 24)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive"
        }
        
        self.sites = [
            {
                "name": "鉅亨網-台股",
                "url": "https://news.cnyes.com/news/cat/tw_stock",
                "article_selector": "a",
                "base_url": "https://news.cnyes.com"
            },
            {
                "name": "經濟日報-財經", 
                "url": "https://money.udn.com/money/cate/12017",
                "article_selector": "a",
                "base_url": "https://money.udn.com"
            },
            {
                "name": "經濟日報-金融",
                "url": "https://money.udn.com/money/cate/12016", 
                "article_selector": "a",
                "base_url": "https://money.udn.com"
            },
            {
                "name": "自由財經",
                "url": "https://ec.ltn.com.tw/",
                "article_selector": "a",
                "base_url": "https://ec.ltn.com.tw"
            },
            {
                "name": "工商時報-財經",
                "url": "https://ctee.com.tw/category/financial",
                "article_selector": "a",
                "base_url": "https://ctee.com.tw"
            }
        ]
        
        # 放寬關鍵詞條件
        self.broad_keywords = [
            # 公司相關（放寬）
            "新光", "台新", "新光人壽", "台新人壽", "新光金控", "台新金控", "新光金", "台新金",
            
            # 保險相關（放寬）
            "保險", "壽險", "人壽", "健康險", "醫療險", "意外險", "投資型", "年金", "儲蓄險",
            "理賠", "給付", "保單", "保費", "承保", "核保", "要保", "被保險", "受益人",
            
            # 金融相關（新增）
            "金控", "金融", "保障", "風險"
        ]
        
        # 大幅減少排除關鍵詞
        self.exclude_keywords = [
            "股東大會決議", "配息除息公告", "財報法說會"
        ]
    
    def _detect_encoding(self, content_bytes):
        """檢測編碼"""
        try:
            encodings = ['utf-8', 'big5', 'gb2312']
            for encoding in encodings:
                try:
                    decoded = content_bytes.decode(encoding)
                    return encoding
                except:
                    continue
            return 'utf-8'
        except:
            return 'utf-8'
    
    def crawl(self) -> List[NewItem]:
        """爬取財經新聞網站的新聞"""
        all_news = []
        
        for site in self.sites:
            site_name = site["name"]
            logger.info(f"🏢 正在爬取網站: {site_name}")
            
            try:
                news_items = self._crawl_site(site)
                all_news.extend(news_items)
                time.sleep(random.uniform(1, 3))
                logger.info(f"✅ 從 {site_name} 爬取到 {len(news_items)} 條新聞")
            except Exception as e:
                logger.error(f"❌ 爬取 {site_name} 時出錯: {str(e)}")
        
        logger.info(f"📊 財經直接爬蟲總計獲得 {len(all_news)} 條原始新聞")
        
        # 放寬篩選邏輯
        filtered_news = []
        
        for item in all_news:
            title_content = (item.title + " " + (item.content or "")).lower()
            
            # 檢查排除關鍵詞（大幅減少）
            contains_exclude = any(exclude_word in title_content for exclude_word in self.exclude_keywords)
            if contains_exclude:
                logger.debug(f"❌ 排除新聞: {item.title[:30]}...")
                continue
            
            matched_keyword = None
            priority_score = 1  # 預設分數
            
            # 檢查是否包含任何相關關鍵詞
            for keyword in self.broad_keywords:
                if keyword in item.title or (item.content and keyword in item.content):
                    matched_keyword = keyword
                    
                    # 設定優先級
                    if keyword in ["新光人壽", "台新人壽", "新光金控", "台新金控"]:
                        priority_score = 10
                    elif keyword in ["新光", "台新"]:
                        priority_score = 8
                    elif keyword in ["健康險", "醫療險", "投資型", "理賠"]:
                        priority_score = 6
                    elif keyword in ["保險", "壽險", "人壽"]:
                        priority_score = 4
                    else:
                        priority_score = 2
                    break
            
            # 如果找到任何匹配，就加入
            if matched_keyword:
                item.keyword = matched_keyword
                item.priority_score = priority_score
                filtered_news.append(item)
                logger.info(f"✅ 符合關鍵詞 '{matched_keyword}' (優先級:{priority_score}): {item.title[:40]}...")
        
        logger.info(f"🎯 財經直接爬蟲篩選完成，剩餘 {len(filtered_news)} 條相關新聞")
        
        # 按優先級排序
        sorted_news = sorted(filtered_news, key=lambda x: (-getattr(x, 'priority_score', 0), -x.published_time.timestamp()))
        return sorted_news[:30]  # 增加返回數量
    
    def _crawl_site(self, site: Dict[str, Any]) -> List[NewItem]:
        """爬取特定網站的新聞"""
        news_items = []
        
        try:
            response = requests.get(site["url"], headers=self.headers, timeout=15)
            response.raise_for_status()
            
            if response.content:
                detected_encoding = self._detect_encoding(response.content)
                response.encoding = detected_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 找所有連結
            article_elements = soup.find_all("a", href=True)
            
            processed_count = 0
            related_count = 0
            
            for element in article_elements:
                if processed_count >= 200:  # 增加處理數量
                    break
                    
                try:
                    # 獲取標題
                    title = element.get_text().strip()
                    
                    if not title or len(title) < 5:
                        continue
                    
                    # 清理標題
                    title = title.replace('\n', ' ').replace('\r', ' ').strip()
                    title = ''.join(char for char in title if ord(char) < 65536)
                    
                    processed_count += 1
                    
                    # 放寬預篩選條件
                    title_lower = title.lower()
                    
                    # 檢查是否包含任何相關關鍵詞
                    contains_related = any(keyword in title_lower for keyword in [
                        "保險", "壽險", "人壽", "新光", "台新", "理賠", "保單", "保費", 
                        "健康險", "醫療險", "意外險", "投保", "承保", "給付", "金控",
                        "投資型", "利變", "年金", "儲蓄險", "風險", "保障"
                    ])
                    
                    # 只要包含任何相關詞彙就處理
                    if not contains_related:
                        continue
                    
                    related_count += 1
                    
                    # 獲取連結
                    url = element.get("href")
                    if not url:
                        continue
                    
                    if not url.startswith(("http://", "https://")):
                        url = urljoin(site["base_url"], url)
                    
                    # 設定發布時間
                    pub_time = datetime.now()
                    
                    # 獲取內容（簡化）
                    content = title  # 暫時使用標題作為內容，避免過度請求
                    
                    # 創建新聞項目
                    news_item = NewItem(
                        title=title,
                        content=content,
                        url=url,
                        published_time=pub_time,
                        source=site["name"],
                        keyword=""
                    )
                    
                    news_items.append(news_item)
                    
                    # 限制每個網站的新聞數量
                    if len(news_items) >= 50:
                        break
                    
                except Exception as e:
                    logger.warning(f"⚠️ 解析文章時出錯: {str(e)}")
            
            logger.info(f"📊 {site['name']}: 處理了{processed_count}篇文章，找到{related_count}篇相關，成功解析{len(news_items)}篇")
            
        except Exception as e:
            logger.error(f"❌ 爬取網站 {site['name']} 時出錯: {str(e)}")
        
        return news_items
