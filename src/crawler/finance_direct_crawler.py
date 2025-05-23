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
    """優化後的財經新聞網站直接爬蟲 - 專注保險新聞"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.hours_limit = config.get('hours_limit', 48)  # 增加到48小時
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Charset": "utf-8, big5, gb2312, iso-8859-1",
            "Connection": "keep-alive"
        }
        
        # 擴充保險相關新聞網站
        self.sites = [
            {
                "name": "鉅亨網-保險專區",
                "url": "https://news.cnyes.com/news/cat/tw_insurance",
                "article_selector": "a.theme-list-title, a[href*='news']",
                "title_selector": "h3, h2, .title",
                "time_selector": "time, .time",
                "time_format": "%Y/%m/%d %H:%M",
                "base_url": "https://news.cnyes.com"
            },
            {
                "name": "鉅亨網-台股",
                "url": "https://news.cnyes.com/news/cat/tw_stock",
                "article_selector": "a.theme-list-title, a[href*='news']",
                "title_selector": "h3, h2, .title",
                "time_selector": "time, .time",
                "time_format": "%Y/%m/%d %H:%M",
                "base_url": "https://news.cnyes.com"
            },
            {
                "name": "經濟日報-財經",
                "url": "https://money.udn.com/money/cate/12017",
                "article_selector": "a[href*='story'], a[href*='news']",
                "title_selector": "h3, h2, .title",
                "time_selector": ".time, .date",
                "time_format": "%Y-%m-%d %H:%M",
                "base_url": "https://money.udn.com"
            },
            {
                "name": "經濟日報-金融",
                "url": "https://money.udn.com/money/cate/12016",
                "article_selector": "a[href*='story'], a[href*='news']",
                "title_selector": "h3, h2, .title",
                "time_selector": ".time, .date",
                "time_format": "%Y-%m-%d %H:%M",
                "base_url": "https://money.udn.com"
            },
            {
                "name": "自由財經",
                "url": "https://ec.ltn.com.tw/",
                "article_selector": "a.tit, a[href*='news']",
                "title_selector": "self",
                "time_selector": ".time",
                "time_format": "%Y/%m/%d %H:%M",
                "base_url": "https://ec.ltn.com.tw"
            },
            {
                "name": "工商時報-財經",
                "url": "https://ctee.com.tw/category/financial",
                "article_selector": "a[href*='news'], .post-title a",
                "title_selector": "self",
                "time_selector": ".time, .date",
                "time_format": "%Y-%m-%d %H:%M:%S",
                "base_url": "https://ctee.com.tw"
            },
            {
                "name": "MoneyDJ理財網",
                "url": "https://www.moneydj.com/",
                "article_selector": "a[href*='news']",
                "title_selector": "self",
                "time_selector": ".time, .date",
                "time_format": "%Y-%m-%d %H:%M:%S",
                "base_url": "https://www.moneydj.com"
            },
            {
                "name": "保險雜誌",
                "url": "https://www.rmim.com.tw/news/",
                "article_selector": "a[href*='news']",
                "title_selector": "self",
                "time_selector": ".time, .date",
                "time_format": "%Y-%m-%d",
                "base_url": "https://www.rmim.com.tw"
            }
        ]
        
        # 重新整理保險關鍵詞 - 更精確的匹配
        self.primary_insurance_keywords = [
            # 指定公司
            "新光人壽", "新光金控", "新光金", "新光保險", 
            "台新人壽", "台新金控", "台新金", "台新保險",
            
            # 具體險種
            "健康險", "醫療險", "癌症險", "重大疾病險", "實支實付",
            "投資型保險", "投資型", "變額保險", "變額萬能",
            "壽險", "終身壽險", "定期壽險", "終身險",
            "利變壽險", "利率變動型", "利變險", "增額終身",
            "意外險", "傷害險", "意外醫療", "意外死殘",
            "年金險", "即期年金", "遞延年金", "退休年金",
            "儲蓄險", "還本險", "生存險",
            
            # 保險業務相關
            "理賠", "給付", "保險金", "死亡給付", "生存給付",
            "保費", "保單", "投保", "承保", "核保",
            "要保人", "被保險人", "受益人",
            "保險期間", "保險金額", "保障額度",
            
            # 監理法規
            "保險法", "保險業法", "RBC", "清償能力",
            "保險局", "金管會保險局", "保險監理",
            "IFRS17", "會計準則"
        ]
        
        # 次要關鍵詞 - 保險業相關但不是核心
        self.secondary_keywords = [
            "保險業", "保險公司", "人壽保險", "產險", "壽險業",
            "保險密度", "保險滲透率", "保險市場",
            "再保險", "保險經紀", "保險代理", "保險通路",
            "團體保險", "個人保險", "企業保險",
            "保險科技", "數位保險", "線上投保",
            "風險評估", "精算", "保險精算"
        ]
        
        # 排除的關鍵詞 - 避免無關新聞
        self.exclude_keywords = [
            "股價", "股票", "配息", "除權", "除息", "股東會",
            "ETF", "基金", "債券", "匯率", "央行", "升息", "降息",
            "銀行", "存款", "放款", "信用卡", "房貸", "車貸"
        ]
    
    def _detect_encoding(self, content_bytes):
        """檢測並返回正確的編碼"""
        try:
            encodings = ['utf-8', 'big5', 'gb2312', 'gbk', 'utf-16', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    decoded = content_bytes.decode(encoding)
                    if any('\u4e00' <= char <= '\u9fff' for char in decoded[:100]):
                        return encoding
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            detected = chardet.detect(content_bytes)
            if detected and detected['confidence'] > 0.7:
                return detected['encoding']
            
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
                
                time.sleep(random.uniform(1, 3))
                
                logger.info(f"從 {site_name} 爬取到 {len(news_items)} 條新聞")
            except Exception as e:
                logger.error(f"爬取 {site_name} 時出錯: {str(e)}")
        
        # 改進的篩選邏輯
        filtered_news = []
        for item in all_news:
            title_content = (item.title + " " + (item.content or "")).lower()
            
            # 檢查是否包含排除關鍵詞
            contains_exclude = any(exclude_word in title_content for exclude_word in self.exclude_keywords)
            if contains_exclude:
                logger.debug(f"排除新聞（包含排除關鍵詞）: {item.title[:30]}...")
                continue
            
            matched_keyword = None
            priority_score = 0
            
            # 首先檢查主要保險關鍵詞（最高優先級）
            for insurance_term in self.primary_insurance_keywords:
                if insurance_term in item.title or (item.content and insurance_term in item.content):
                    matched_keyword = insurance_term
                    priority_score = 10  # 最高優先級
                    break
            
            # 如果沒有匹配主要關鍵詞，檢查次要關鍵詞
            if not matched_keyword:
                for secondary_term in self.secondary_keywords:
                    if secondary_term in item.title or (item.content and secondary_term in item.content):
                        matched_keyword = secondary_term
                        priority_score = 5
                        break
            
            # 最後檢查原始搜尋關鍵詞
            if not matched_keyword:
                for term in self.search_terms:
                    if term in item.title or (item.content and term in item.content):
                        matched_keyword = term
                        priority_score = 1
                        break
            
            if matched_keyword:
                item.keyword = matched_keyword
                item.priority_score = priority_score  # 添加優先級分數
                filtered_news.append(item)
                logger.info(f"符合關鍵詞 '{matched_keyword}' (優先級:{priority_score}) 的新聞: {item.title[:30]}...")
        
        logger.info(f"過濾後剩餘 {len(filtered_news)} 條相關新聞")
        
        # 按優先級和時間排序
        sorted_news = sorted(filtered_news, key=lambda x: (-getattr(x, 'priority_score', 0), -x.published_time.timestamp()))
        return sorted_news[:20]  # 返回前20條最相關的新聞
    
    def _crawl_site(self, site: Dict[str, Any]) -> List[NewItem]:
        """爬取特定網站的新聞"""
        news_items = []
        
        try:
            response = requests.get(site["url"], headers=self.headers, timeout=15)
            response.raise_for_status()
            
            if response.content:
                detected_encoding = self._detect_encoding(response.content)
                response.encoding = detected_encoding
                logger.debug(f"檢測到編碼: {detected_encoding}")
            
            soup = BeautifulSoup(response.text, 'html.parser', from_encoding=response.encoding)
            
            article_elements = soup.select(site["article_selector"])
            
            if not article_elements:
                article_elements = soup.find_all("a", href=True)
                logger.info(f"使用通用選擇器找到 {len(article_elements)} 個候選文章")
            else:
                logger.info(f"找到 {len(article_elements)} 個候選文章")
            
            processed_count = 0
            for element in article_elements:
                if processed_count >= 50:  # 增加處理數量
                    break
                    
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
                    
                    if title:
                        title = title.replace('\n', ' ').replace('\r', ' ').strip()
                        title = ''.join(char for char in title if ord(char) < 65536)
                    
                    if not title or len(title) < 5:
                        continue
                    
                    # 改進的標題預篩選
                    title_lower = title.lower()
                    
                    # 檢查是否包含保險相關詞彙
                    contains_insurance_keyword = any(keyword in title_lower for keyword in [
                        "保險", "壽險", "新光", "台新", "理賠", "保單", "保費", 
                        "健康險", "意外險", "醫療險", "投保", "承保", "給付",
                        "投資型", "利變", "年金", "儲蓄險", "重大疾病", "癌症險"
                    ])
                    
                    # 如果標題包含排除關鍵詞，跳過
                    contains_exclude = any(exclude_word in title_lower for exclude_word in self.exclude_keywords)
                    
                    # 只處理保險相關且不包含排除關鍵詞的新聞
                    if not contains_insurance_keyword or contains_exclude:
                        continue
                    
                    # 獲取連結
                    url = element.get("href")
                    if not url:
                        continue
                    
                    if not url.startswith(("http://", "https://")):
                        url = urljoin(site["base_url"], url)
                    
                    # 獲取發布時間
                    pub_time = datetime.now()  # 簡化時間處理，默認為當前時間
                    
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
                    processed_count += 1
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
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            if response.content:
                detected_encoding = self._detect_encoding(response.content)
                response.encoding = detected_encoding
            
            soup = BeautifulSoup(response.text, 'html.parser', from_encoding=response.encoding)
            
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
                ".post-content"
            ]
            
            content_text = ""
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    for element in content_element.select("script, style, iframe, ins, .ad, .ads"):
                        element.extract()
                    
                    content_text = content_element.get_text(separator="\n").strip()
                    if content_text:
                        break
            
            if not content_text:
                for element in soup.select("header, footer, nav, aside, .sidebar, .ads, .ad, script, style"):
                    element.extract()
                
                content_text = soup.get_text(separator="\n").strip()
                lines = [line.strip() for line in content_text.splitlines() if line.strip()]
                content_text = "\n".join(lines)
            
            if content_text:
                content_text = content_text.replace('\n', ' ').replace('\r', ' ').strip()
                content_text = ''.join(char for char in content_text if ord(char) < 65536)
            
            return content_text
        
        except Exception as e:
            logger.warning(f"獲取文章內容時出錯: {str(e)}")
            return "無法獲取文章內容"
