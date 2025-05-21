import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
from typing import List, Dict, Any
from urllib.parse import urljoin
from loguru import logger

from .base_crawler import BaseCrawler, NewItem

class FinanceNewsDirectCrawler(BaseCrawler):
    """財經新聞網站直接爬蟲"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.hours_limit = config.get('hours_limit', 24)  # 預設限制24小時
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        # 定義財經新聞網站及其爬取規則，使用更通用的選擇器
        self.sites = [
            {
                "name": "鉅亨網-台股",
                "url": "https://news.cnyes.com/news/cat/tw_stock",
                "article_selector": "a",  # 更通用
                "title_selector": "h3, h2, h4, .title",  # 更多選擇器
                "time_selector": "time, .time, .date, span.date",
                "time_format": "%Y/%m/%d %H:%M",
                "base_url": "https://news.cnyes.com"
            },
            {
                "name": "經濟日報-財經",
                "url": "https://money.udn.com/money/cate/12017",
                "article_selector": "a",  # 更通用
                "title_selector": "h3, h2, .title",
                "time_selector": ".time, span.time, .date",
                "time_format": "%Y-%m-%d %H:%M",
                "base_url": "https://money.udn.com"
            },
            {
                "name": "自由財經",
                "url": "https://ec.ltn.com.tw/",
                "article_selector": "a.tit, a.title, a.boxText, a",
                "title_selector": "self",
                "time_selector": ".time, span.time",
                "time_format": "%Y/%m/%d %H:%M",
                "base_url": "https://ec.ltn.com.tw"
            },
            {
                "name": "中央社財經",
                "url": "https://www.cna.com.tw/list/money.aspx",
                "article_selector": "a.listInfo, a",
                "title_selector": "h2, .listTitle, self",
                "time_selector": ".date, .time",
                "time_format": "%Y/%m/%d %H:%M",
                "base_url": "https://www.cna.com.tw"
            },
            {
                "name": "MoneyDJ理財網",
                "url": "https://www.moneydj.com/",
                "article_selector": "a.link, a",
                "title_selector": "self, h3, h2",
                "time_selector": ".time, span.time, .date",
                "time_format": "%Y-%m-%d %H:%M:%S",
                "base_url": "https://www.moneydj.com"
            }
        ]
    
    def crawl(self) -> List[NewItem]:
        """爬取財經新聞網站的新聞"""
        all_news = []
        
        for site in self.sites:
            site_name = site["name"]
            logger.info(f"爬取網站: {site_name}")
            
            try:
                news_items = self._crawl_site(site)
                all_news.extend(news_items)
                
                # 避免過度請求，增加隨機延遲
                time.sleep(random.uniform(1, 3))
                
                logger.info(f"從 {site_name} 爬取到 {len(news_items)} 條新聞")
            except Exception as e:
                logger.error(f"爬取 {site_name} 時出錯: {str(e)}")
        
        # 更進一步放寬關鍵詞匹配邏輯
        filtered_news = []
        for item in all_news:
            for term in self.search_terms:
                # 檢查標題或內容中是否包含關鍵詞（部分匹配），或關鍵詞的部分匹配
                if (term in item.title or 
                    (item.content and term in item.content) or 
                    (item.source and term in item.source) or
                    # 新增：檢查關鍵詞的部分匹配（例如"保險"可以匹配"壽險保險"）
                    any(kw in term or term in kw for kw in ["保險", "金控", "金融", "銀行", "證券", "投資", "理財"] if kw in item.title or (item.content and kw in item.content))):
                    
                    item.keyword = term  # 設置關鍵詞
                    filtered_news.append(item)
                    logger.info(f"符合關鍵詞 '{term}' 的新聞: {item.title[:30]}...")
                    break
        
        logger.info(f"過濾後剩餘 {len(filtered_news)} 條相關新聞")
        
        # 根據優先順序排序
        sorted_news = self.sort_by_priority(filtered_news)
        return sorted_news
    
    def _crawl_site(self, site: Dict[str, Any]) -> List[NewItem]:
        """爬取特定網站的新聞"""
        news_items = []
        
        try:
            # 設置請求頭，模擬瀏覽器訪問
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0"
            }
            
            # 獲取網頁內容
            response = requests.get(site["url"], headers=headers, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'  # 確保正確處理中文
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尋找所有文章元素（更通用的方法）
            article_elements = soup.select(site["article_selector"])
            
            # 如果找不到文章元素，嘗試更通用的選擇器
            if not article_elements:
                article_elements = soup.find_all("a", href=True)
                logger.info(f"使用通用選擇器找到 {len(article_elements)} 個候選文章")
            else:
                logger.info(f"找到 {len(article_elements)} 個候選文章")
            
            for element in article_elements[:20]:  # 只處理前20個，避免處理過多
                try:
                    # 獲取標題
                    title = None
                    if site["title_selector"] == "self":
                        title = element.get_text().strip()
                    else:
                        # 嘗試多個選擇器
                        for selector in site["title_selector"].split(", "):
                            title_element = element.select_one(selector)
                            if title_element:
                                title = title_element.get_text().strip()
                                break
                        
                        # 如果還是找不到標題，嘗試從元素本身獲取
                        if not title:
                            title = element.get_text().strip()
                    
                    # 如果標題太短，可能不是新聞
                    if not title or len(title) < 10:
                        continue
                    
                    # 獲取連結
                    url = element.get("href")
                    if not url:
                        continue
                    
                    # 處理相對URL
                    if not url.startswith(("http://", "https://")):
                        url = urljoin(site["base_url"], url)
                    
                    # 獲取發布時間（嘗試多種方法）
                    pub_time = None
                    # 方法1：從頁面元素獲取
                    for selector in site["time_selector"].split(", "):
                        time_element = element.select_one(selector)
                        if not time_element and element.parent:
                            time_element = element.parent.select_one(selector)
                        
                        if time_element:
                            time_text = time_element.get_text().strip()
                            try:
                                pub_time = datetime.strptime(time_text, site["time_format"])
                                break
                            except:
                                # 嘗試解析相對時間
                                if "分鐘前" in time_text:
                                    minutes = int(''.join(filter(str.isdigit, time_text)))
                                    pub_time = datetime.now() - timedelta(minutes=minutes)
                                    break
                                elif "小時前" in time_text:
                                    hours = int(''.join(filter(str.isdigit, time_text)))
                                    pub_time = datetime.now() - timedelta(hours=hours)
                                    break
                                elif "天前" in time_text:
                                    days = int(''.join(filter(str.isdigit, time_text)))
                                    pub_time = datetime.now() - timedelta(days=days)
                                    break
                    
                    # 如果找不到時間，使用當前時間
                    if not pub_time:
                        pub_time = datetime.now()
                    
                    # 檢查時間是否在限制範圍內
                    hours_diff = (datetime.now() - pub_time).total_seconds() / 3600
                    logger.debug(f"新聞時間: {pub_time}, 距現在: {hours_diff:.1f} 小時")
                    
                    if hours_diff > self.hours_limit:
                        logger.debug(f"跳過，超出時間限制: {self.hours_limit} 小時")
                        continue
                    
                    # 獲取詳細內容
                    content = self._get_article_content(url)
                    
                    # 創建新聞項目
                    news_item = NewItem(
                        title=title,
                        content=content,
                        url=url,
                        published_time=pub_time,
                        source=site["name"],
                        keyword=""  # 暫時將關鍵詞設為空，後續會根據內容設置
                    )
                    
                    news_items.append(news_item)
                    logger.debug(f"成功解析新聞: {title[:30]}...")
                    
                except Exception as e:
                    logger.warning(f"解析文章時出錯: {str(e)}")
            
        except Exception as e:
            logger.error(f"爬取網站 {site['name']} 時出錯: {str(e)}")
        
        return news_items
    
    def _get_article_content(self, url: str) -> str:
        """獲取文章內容"""
        try:
            # 設置隨機等待，避免被網站封鎖
            time.sleep(random.uniform(0.5, 1.5))
            
            # 設置請求頭，模擬瀏覽器訪問
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
                "Referer": url,  # 添加 Referer 頭
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0"
            }
            
            # 獲取頁面內容
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'  # 確保正確處理中文
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 嘗試識別文章主體（使用更多選擇器）
            content_selectors = [
                "div.article-content", 
                "div.article-body",
                "div.story-content",
                "div.news-content",
                "div.cont",
                "div.editor",
                "div#MainContent",
                "article",
                "div.text",
                "div.news-content-box",
                "div.paragraph",
                "div.content",
                ".news-detail",
                ".news-body",
                ".article",
                "main"
            ]
            
            content_text = ""
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    # 移除不必要的元素
                    for element in content_element.select("script, style, iframe, ins, .ad, .ads, .adsbygoogle"):
                        element.extract()
                    
                    content_text = content_element.get_text(separator="\n").strip()
                    if content_text:
                        break
            
            # 如果找不到內容，使用更通用的方法
            if not content_text:
                # 移除頭部、底部、側邊欄等
                for element in soup.select("header, footer, nav, aside, .header, .footer, .sidebar, .ads, .ad, script, style"):
                    element.extract()
                
                # 獲取剩餘部分的文本
                content_text = soup.get_text(separator="\n").strip()
                
                # 清理文本
                lines = [line.strip() for line in content_text.splitlines() if line.strip()]
                content_text = "\n".join(lines)
            
            return content_text
        
        except Exception as e:
            logger.warning(f"獲取文章內容時出錯: {str(e)}")
            return "無法獲取文章內容"
