import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
from typing import List, Dict, Any
import newspaper
from newspaper import Article
from urllib.parse import quote
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
            news_divs = soup.find_all("div", class_="SoaBEf")
            
            count = 0
            for div in news_divs:
                if count >= self.max_news_per_term:
                    break
                
                try:
                    # 解析新聞元素
                    title_element = div.find("div", class_="mCBkyc")
                    link_element = div.find("a")
                    source_element = div.find("div", class_="CEMjEf")
                    time_element = div.find("div", class_="OSrXXb")
                    
                    if not all([title_element, link_element, source_element]):
                        continue
                    
                    title = title_element.get_text().strip()
                    url = link_element.get("href")
                    source = source_element.get_text().strip() if source_element else "未知來源"
                    
                    # 解析發布時間
                    pub_time = datetime.now()
                    if time_element:
                        time_text = time_element.get_text().strip()
                        # 簡單的時間解析邏輯
                        if "小時前" in time_text:
                            hours = int(time_text.split(" ")[0])
                            pub_time = datetime.now() - timedelta(hours=hours)
                        elif "天前" in time_text:
                            days = int(time_text.split(" ")[0])
                            pub_time = datetime.now() - timedelta(days=days)
                    
                    # 僅保留24小時內的新聞
                    hours_diff = (datetime.now() - pub_time).total_seconds() / 3600
                    if hours_diff > 24:
                        continue
                    
                    # 獲取詳細內容
                    content = self._get_article_content(url)
                    
                    # 創建新聞項目
                    news_item = NewItem(
                        title=title,
                        content=content,
                        url=url,
                        published_time=pub_time,
                        source=source,
                        keyword=term
                    )
                    
                    news_items.append(news_item)
                    count += 1
                    
                except Exception as e:
                    logger.warning(f"解析新聞時出錯: {str(e)}")
            
        except requests.RequestException as e:
            logger.error(f"請求Google新聞時出錯: {str(e)}")
        
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
