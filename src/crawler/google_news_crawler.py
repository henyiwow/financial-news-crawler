import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
from typing import List, Dict, Any
from urllib.parse import quote, parse_qs
from loguru import logger

from .base_crawler import BaseCrawler, NewItem

class GoogleNewsCrawler(BaseCrawler):
    """Google新聞爬蟲"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = "https://www.google.com/search"
        self.region = config.get('region', 'tw')  # 預設為台灣地區
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }
    
    def crawl(self) -> List[NewItem]:
        """爬取Google新聞"""
        all_news = []
        
        for term in self.search_terms:
            logger.info(f"搜尋關鍵詞: {term}")
            try:
                news_items = self._search_term(term)
                all_news.extend(news_items)
                
                # 避免被Google封鎖，增加隨機延遲
                time.sleep(random.uniform(1, 3))
            except Exception as e:
                logger.error(f"爬取關鍵詞 '{term}' 時出錯: {str(e)}")
        
        # 根據優先順序排序
        sorted_news = self.sort_by_priority(all_news)
        return sorted_news
    
    def _search_term(self, term: str) -> List[NewItem]:
        """使用特定關鍵詞搜尋Google新聞"""
        news_items = []
        
        # 構建查詢參數
        params = {
            "q": f"{term}",
            "tbm": "nws",  # 新聞搜尋
            "tbs": f"qdr:{self.time_period}",  # 時間範圍
            "hl": "zh-TW",  # 語言
            "gl": "tw"      # 地區：台灣
        }
        
        try:
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 嘗試多種可能的新聞元素選擇器
            news_divs = []
            
            # 嘗試方法1：常見的Google新聞結構
            selector_attempts = [
                "div.SoaBEf",
                "div.WlydOe",
                "div.xuvV6b",
                "div.DBQmFf",
                "g-card.ftSUBd",
                "div.v7W49e"
            ]
            
            for selector in selector_attempts:
                elements = soup.select(selector)
                if elements:
                    news_divs = elements
                    logger.info(f"找到選擇器 {selector} 的新聞元素: {len(elements)} 個")
                    break
            
            # 如果前面的選擇器都沒找到元素，嘗試更通用的方法
            if not news_divs:
                # 尋找包含標題、連結和來源的元素（更通用的方法）
                news_divs = soup.find_all("div", recursive=True, limit=20)
                news_divs = [div for div in news_divs if div.find("a") and div.find("h3")]
                logger.info(f"使用通用方法找到 {len(news_divs)} 個可能的新聞元素")
            
            count = 0
            for div in news_divs:
                if count >= self.max_news_per_term:
                    break
                
                try:
                    # 嘗試多種方式解析新聞元素
                    title = None
                    url = None
                    source = None
                    time_text = None
                    
                    # 尋找標題
                    title_elements = [
                        div.find("div", class_="mCBkyc"),
                        div.find("h3"),
                        div.find("a", class_="DY5T1d"),
                        div.find(["h3", "h4"]),
                    ]
                    
                    for element in title_elements:
                        if element and element.get_text().strip():
                            title = element.get_text().strip()
                            break
                    
                    # 尋找連結
                    link_element = div.find("a")
                    if link_element and link_element.get("href"):
                        url = link_element.get("href")
                        # 修正URL，確保是完整URL
                        if url.startswith("/url?"):
                            parsed = parse_qs(url.split("?")[1])
                            if "url" in pars
