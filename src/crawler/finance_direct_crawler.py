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
    """財經新聞網站直接爬蟲"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.hours_limit = config.get('hours_limit', 24)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Charset": "utf-8, big5, gb2312, iso-8859-1",
            "Connection": "keep-alive"
        }
        
        # 定義財經新聞網站及其爬取規則，使用更通用的選擇器
        self.sites = [
            {
                "name": "鉅亨網-台股",
                "url": "https://news.cnyes.com/news/cat/tw_stock",
                "article_selector": "a",
                "title_selector": "h3, h2, h4, .title",
                "time_selector": "time, .time, .date, span.date",
                "time_format": "%Y/%m/%d %H:%M",
                "base_url": "https://news.cnyes.com"
            },
            {
                "name": "經濟日報-財經",
                "url": "https://money.udn.com/money/cate/12017",
                "article_selector": "a",
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
                "url": "https://www.cna.com.tw/list/aie.aspx",  # 修正URL
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
        
        # 定義廣泛的財經關鍵詞
        self.broad_keywords = [
            "保險", "壽險", "健康險", "意外險", "理賠", "保單", "保費", "保障",
            "金控", "金融", "銀行", "理財", "投資", "股市", "股票", "基金", 
            "證券", "央行", "利率", "定存", "財富", "經濟", "財經", "金融業",
            "新光", "台新", "富邦", "國泰", "中信", "第一金", "玉山", "永豐",
            "上市", "上櫃", "市值", "營收", "獲利", "股價", "配息", "股利",
            "ETF", "債券", "匯率", "通膨", "升息", "降息", "QE", "貨幣",
            "財報", "季報", "年報", "法說", "股東會", "除權", "除息",
            "IPO", "增資", "減資", "併購", "重組", "融資", "放款", "存款",
            "房貸", "信貸", "卡債", "風險", "資產", "負債", "現金流",
            "毛利", "淨利", "eps", "本益比", "殖利率", "市場", "交易",
            "買進", "賣出", "持有", "漲跌", "波動", "趨勢", "分析"
        ]
    
    def _detect_encoding(self, content_bytes):
        """檢測並返回正確的編碼"""
        try:
            # 嘗試常見的中文編碼
            encodings = ['utf-8', 'big5', 'gb2312', 'gbk', 'utf-16', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    decoded = content_bytes.decode(encoding)
                    # 檢查是否包含明顯的中文字符
                    if any('\u4e00' <= char <= '\u9fff' for char in decoded[:100]):
                        return encoding
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            # 使用chardet自動檢測
            detected = chardet.detect(content_bytes)
            if detected and detected['confidence'] > 0.7:
                return detected['encoding']
            
            # 默認使用UTF-8
            return 'utf-8'
        except:
            return 'utf-8'
    
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
        
        # 關鍵詞匹配邏輯
        filtered_news = []
        for item in all_news:
            title_content = (item.title + " " + (item.content or "")).lower()
            
            matched_keyword = None
            for term in self.search_terms:
                if term in item.title or (item.content and term in item.content):
                    matched_keyword = term
                    break
            
            if not matched_keyword:
                for broad_term in self.broad_keywords:
                    if broad_term in title_content:
                        matched_keyword = broad_term
                        break
            
            if matched_keyword:
                item.keyword = matched_keyword
                filtered_news.append(item)
                logger.info(f"符合關鍵詞 '{matched_keyword}' 的新聞: {item.title[:30]}...")
        
        logger.info(f"過濾後剩餘 {len(filtered_news)} 條相關新聞")
        
        sorted_news = self.sort_by_priority(filtered_news)
        return sorted_news
    
    def _crawl_site(self, site: Dict[str, Any]) -> List[NewItem]:
        """爬取特定網站的新聞"""
        news_items = []
        
        try:
            # 獲取網頁內容
            response = requests.get(site["url"], headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # 自動檢測並設置正確的編碼
            if response.content:
                detected_encoding = self._detect_encoding(response.content)
                response.encoding = detected_encoding
                logger.debug(f"檢測到編碼: {detected_encoding}")
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser', from_encoding=response.encoding)
            
            # 尋找所有文章元素
            article_elements = soup.select(site["article_selector"])
            
            if not article_elements:
                article_elements = soup.find_all("a", href=True)
                logger.info(f"使用通用選擇器找到 {len(article_elements)} 個候選文章")
            else:
                logger.info(f"找到 {len(article_elements)} 個候選文章")
            
            for element in article_elements[:20]:
                try:
                    # 獲取標題
                    title = None
                    if site["title_selector"] == "self":
                        title = element.get_text().strip()
                    else:
                        for selector in site["title_selector"].split(", "):
                            title_element = element.select_one(selector)
                            if title_element:
                                title = title_element.get_text().strip()
                                break
                        
                        if not title:
                            title = element.get_text().strip()
                    
                    # 清理標題，移除特殊字符
                    if title:
                        title = title.replace('\n', ' ').replace('\r', ' ').strip()
                        # 移除明顯的亂碼字符
                        title = ''.join(char for char in title if ord(char) < 65536)
                    
                    if not title or len(title) < 10:
                        continue
                    
                    # 獲取連結
                    url = element.get("href")
                    if not url:
                        continue
                    
                    if not url.startswith(("http://", "https://")):
                        url = urljoin(site["base_url"], url)
                    
                    # 獲取發布時間
                    pub_time = datetime.now()
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
                    
                    # 檢查時間限制
                    hours_diff = (datetime.now() - pub_time).total_seconds() / 3600
                    if hours_diff > self.hours_limit:
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
                        keyword=""
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
            time.sleep(random.uniform(0.5, 1.5))
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # 自動檢測編碼
            if response.content:
                detected_encoding = self._detect_encoding(response.content)
                response.encoding = detected_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser', from_encoding=response.encoding)
            
            # 嘗試識別文章主體
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
                    for element in content_element.select("script, style, iframe, ins, .ad, .ads, .adsbygoogle"):
                        element.extract()
                    
                    content_text = content_element.get_text(separator="\n").strip()
                    if content_text:
                        break
            
            if not content_text:
                for element in soup.select("header, footer, nav, aside, .header, .footer, .sidebar, .ads, .ad, script, style"):
                    element.extract()
                
                content_text = soup.get_text(separator="\n").strip()
                lines = [line.strip() for line in content_text.splitlines() if line.strip()]
                content_text = "\n".join(lines)
            
            # 清理內容，移除亂碼
            if content_text:
                content_text = content_text.replace('\n', ' ').replace('\r', ' ').strip()
                content_text = ''.join(char for char in content_text if ord(char) < 65536)
            
            return content_text
        
        except Exception as e:
            logger.warning(f"獲取文章內容時出錯: {str(e)}")
            return "無法獲取文章內容"
