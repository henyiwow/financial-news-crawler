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
    """優化後的Google新聞爬蟲 - 專注保險新聞"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = "https://www.google.com/search"
        self.region = config.get('region', 'tw')
        self.hours_limit = config.get('hours_limit', 48)  # 增加到48小時
        self.max_pages = config.get('max_pages', 3)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        # 專門針對保險的搜尋關鍵詞
        self.insurance_search_terms = [
            # 公司名稱相關
            "新光人壽 OR 新光金控",
            "台新人壽 OR 台新金控", 
            
            # 險種相關
            "健康險 OR 醫療險",
            "投資型保險 OR 變額保險",
            "壽險 OR 終身壽險",
            "利變壽險 OR 利率變動型",
            "意外險 OR 傷害險",
            "年金險 OR 退休年金",
            "儲蓄險 OR 還本險",
            
            # 保險業務
            "保險理賠",
            "保單給付",
            "保險新商品",
            "保險法規",
            
            # 組合搜尋
            "保險 健康險",
            "保險 投資型",
            "壽險 新光",
            "壽險 台新"
        ]
        
        # 優先關鍵詞 - 用於結果排序
        self.priority_keywords = [
            "新光人壽", "新光金控", "台新人壽", "台新金控",
            "健康險", "投資型保險", "利變壽險", "意外險"
        ]
    
    def crawl(self) -> List[NewItem]:
        """爬取Google新聞"""
        all_news = []
        
        # 使用專門的保險搜尋關鍵詞
        search_terms = self.insurance_search_terms + self.search_terms
        
        for term in search_terms:
            logger.info(f"搜尋關鍵詞: {term}")
            try:
                news_items = self._search_term_multiple_pages(term)
                all_news.extend(news_items)
                
                # 避免被Google封鎖，增加隨機延遲
                time.sleep(random.uniform(3, 6))
            except Exception as e:
                logger.error(f"爬取關鍵詞 '{term}' 時出錯: {str(e)}")
        
        # 去重複
        unique_news = self._remove_duplicates(all_news)
        logger.info(f"去重後剩餘 {len(unique_news)} 條新聞")
        
        # 過濾保險相關新聞
        filtered_news = self._filter_insurance_news(unique_news)
        logger.info(f"過濾後剩餘 {len(filtered_news)} 條保險相關新聞")
        
        # 根據優先順序排序
        sorted_news = self.sort_by_priority(filtered_news)
        return sorted_news[:15]  # 返回前15條
    
    def _filter_insurance_news(self, news_list: List[NewItem]) -> List[NewItem]:
        """過濾出保險相關新聞"""
        filtered_news = []
        
        # 保險相關關鍵詞
        insurance_keywords = [
            "新光人壽", "新光金控", "台新人壽", "台新金控",
            "保險", "壽險", "健康險", "醫療險", "意外險", "傷害險",
            "投資型保險", "變額保險", "利變壽險", "年金險", "儲蓄險",
            "理賠", "給付", "保單", "保費", "承保", "核保",
            "重大疾病險", "癌症險", "實支實付"
        ]
        
        # 排除關鍵詞
        exclude_keywords = [
            "股價", "配息", "除權", "除息", "ETF", "基金", "債券",
            "銀行存款", "信用卡", "房貸", "車貸"
        ]
        
        for item in news_list:
            title_content = (item.title + " " + (item.content or "")).lower()
            
            # 檢查是否包含排除關鍵詞
            contains_exclude = any(exclude_word in title_content for exclude_word in exclude_keywords)
            if contains_exclude:
                continue
            
            # 檢查是否包含保險關鍵詞
            contains_insurance = any(keyword in title_content for keyword in insurance_keywords)
            
            if contains_insurance:
                # 計算優先級分數
                priority_score = 0
                matched_keyword = ""
                
                for keyword in self.priority_keywords:
                    if keyword in title_content:
                        priority_score += 10
                        matched_keyword = keyword
                        break
                
                for keyword in insurance_keywords:
                    if keyword in title_content:
                        if priority_score == 0:
                            priority_score = 5
                            matched_keyword = keyword
                        break
                
                item.keyword = matched_keyword
                item.priority_score = priority_score
                filtered_news.append(item)
                logger.info(f"保險相關新聞: {item.title[:30]}...")
        
        return filtered_news
    
    def _search_term_multiple_pages(self, term: str) -> List[NewItem]:
        """搜尋多頁結果"""
        all_news = []
        
        for page in range(self.max_pages):
            logger.info(f"搜尋關鍵詞 '{term}' 第 {page + 1} 頁")
            
            try:
                news_items = self._search_term(term, page)
                all_news.extend(news_items)
                
                # 如果沒有找到新聞，提前結束
                if not news_items:
                    logger.info(f"關鍵詞 '{term}' 第 {page + 1} 頁無結果，停止搜尋")
                    break
                
                # 頁面間延遲
                if page < self.max_pages - 1:
                    time.sleep(random.uniform(2, 4))
                    
            except Exception as e:
                logger.error(f"搜尋關鍵詞 '{term}' 第 {page + 1} 頁時出錯: {str(e)}")
                break
        
        logger.info(f"關鍵詞 '{term}' 總共找到 {len(all_news)} 條新聞")
        return all_news
    
    def _search_term(self, term: str, page: int = 0) -> List[NewItem]:
        """使用特定關鍵詞搜尋Google新聞"""
        news_items = []
        
        # 構建更精確的查詢參數
        params = {
            "q": f"{term} site:tw",  # 限制台灣網站
            "tbm": "nws",  # 新聞搜尋
            "tbs": "qdr:w2",  # 最近2週
            "hl": "zh-TW",  # 語言
            "gl": "tw",     # 地區：台灣
            "start": page * 10,  # 分頁參數
            "num": 20  # 每頁結果數
        }
        
        try:
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 嘗試多種可能的新聞元素選擇器
            news_divs = []
            
            selector_attempts = [
                "div.SoaBEf",
                "div.WlydOe", 
                "div.xuvV6b",
                "div.DBQmFf",
                "g-card.ftSUBd",
                "div.v7W49e",
                "div.g",
                ".g .rc",
                "[jscontroller='SC7lYd']"
            ]
            
            for selector in selector_attempts:
                elements = soup.select(selector)
                if elements:
                    news_divs = elements
                    logger.info(f"第 {page + 1} 頁找到選擇器 {selector} 的新聞元素: {len(elements)} 個")
                    break
            
            if not news_divs:
                # 更通用的方法
                news_divs = soup.find_all("div", recursive=True, limit=50)
                news_divs = [div for div in news_divs if div.find("a") and div.find("h3")]
                logger.info(f"第 {page + 1} 頁使用通用方法找到 {len(news_divs)} 個可能的新聞元素")
            
            count = 0
            for div in news_divs:
                if count >= 20:  # 每頁處理20條新聞
                    break
                
                try:
                    # 解析新聞元素
                    title = None
                    url = None
                    source = None
                    time_text = None
                    
                    # 尋找標題
                    title_elements = [
                        div.find("div", class_="mCBkyc"),
                        div.find("h3"),
                        div.find("a", class_="DY5T1d"),
                        div.find(["h3", "h4", "h2"]),
                        div.find("div", class_="BNeawe"),
                        div.find("div", class_="r")
                    ]
                    
                    for element in title_elements:
                        if element and element.get_text().strip():
                            title = element.get_text().strip()
                            break
                    
                    # 尋找連結
                    link_element = div.find("a")
                    if link_element and link_element.get("href"):
                        url = link_element.get("href")
                        if url.startswith("/url?"):
                            try:
                                parsed = parse_qs(url.split("?")[1])
                                if "url" in parsed and parsed["url"]:
                                    url = parsed["url"][0]
                            except Exception as e:
                                logger.warning(f"解析URL時出錯: {str(e)}")
                    
                    # 尋找來源
                    source_elements = [
                        div.find("div", class_="CEMjEf"),
                        div.find("div", class_="UPmit"),
                        div.find("span", class_="xQ82C"),
                        div.find("div", class_="BNeawe"),
                        div.find("cite"),
                        div.find(["div", "span"], string=lambda s: "·" in s if s else False),
                    ]
                    
                    for element in source_elements:
                        if element and element.get_text().strip():
                            source = element.get_text().strip()
                            # 清理來源文本
                            if "·" in source:
                                source = source.split("·")[0].strip()
                            # 移除URL部分
                            if "http" in source:
                                source = source.split("http")[0].strip()
                            break
                    
                    # 尋找時間
                    time_elements = [
                        div.find("div", class_="OSrXXb"),
                        div.find("span", class_="WG9SHc"),
                        div.find("time"),
                        div.find("span", class_="f"),
                        div.find("div", class_="slp"),
                        div.find(["span", "div"], string=lambda s: "前" in s if s else False),
                    ]
                    
                    for element in time_elements:
                        if element and element.get_text().strip():
                            time_text = element.get_text().strip()
                            break
                    
                    # 確保所有必需元素都存在
                    if not title or not url:
                        continue
                    
                    # 預篩選：只處理包含保險關鍵詞的新聞
                    title_lower = title.lower()
                    insurance_terms = [
                        "保險", "壽險", "新光", "台新", "理賠", "保單", 
                        "健康險", "意外險", "醫療險", "投資型", "年金"
                    ]
                    
                    if not any(term in title_lower for term in insurance_terms):
                        continue
                    
                    # 設置默認來源
                    if not source:
                        source = "Google新聞"
                    
                    # 解析發布時間
                    pub_time = datetime.now()
                    if time_text:
                        try:
                            if "小時前" in time_text:
                                hours = int(''.join(filter(str.isdigit, time_text)))
                                pub_time = datetime.now() - timedelta(hours=hours)
                            elif "分鐘前" in time_text:
                                minutes = int(''.join(filter(str.isdigit, time_text)))
                                pub_time = datetime.now() - timedelta(minutes=minutes)
                            elif "天前" in time_text:
                                days = int(''.join(filter(str.isdigit, time_text)))
                                pub_time = datetime.now() - timedelta(days=days)
                            elif "週前" in time_text or "周前" in time_text:
                                weeks = int(''.join(filter(str.isdigit, time_text)))
                                pub_time = datetime.now() - timedelta(weeks=weeks)
                        except ValueError:
                            logger.debug(f"無法解析時間文本: {time_text}")
                    
                    # 檢查時間限制
                    hours_diff = (datetime.now() - pub_time).total_seconds() / 3600
                    logger.debug(f"新聞時間: {pub_time}, 距現在: {hours_diff:.1f} 小時")
                    
                    if hours_diff > self.hours_limit:
                        logger.debug(f"跳過，超出時間限制: {self.hours_limit} 小時")
                        continue
                    
                    # 清理標題
                    if title:
                        title = title.replace('\n', ' ').replace('\r', ' ').strip()
                        title = ''.join(char for char in title if ord(char) < 65536)
                    
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
                    logger.debug(f"成功解析新聞: {title[:30]}...")
                    
                except Exception as e:
                    logger.warning(f"解析新聞時出錯: {str(e)}")
            
        except requests.RequestException as e:
            logger.error(f"請求Google新聞時出錯: {str(e)}")
        
        return news_items
    
    def _remove_duplicates(self, news_list: List[NewItem]) -> List[NewItem]:
        """移除重複的新聞"""
        seen_titles = set()
        seen_urls = set()
        unique_news = []
        
        for news in news_list:
            # 標準化標題用於比較
            normalized_title = news.title.lower().strip()
            
            # 檢查是否重複
            if (normalized_title not in seen_titles and 
                news.url not in seen_urls):
                seen_titles.add(normalized_title)
                seen_urls.add(news.url)
                unique_news.append(news)
            else:
                logger.debug(f"移除重複新聞: {news.title[:30]}...")
        
        return unique_news
    
    def _get_article_content(self, url: str) -> str:
        """獲取文章內容"""
        try:
            # 設置隨機等待，避免被網站封鎖
            time.sleep(random.uniform(0.5, 1.2))
            
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
                "div.content",
                "article",
                "main",
                ".post-content",
                ".entry-content",
                ".news-detail"
            ]
            
            content_text = ""
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    content_text = content_element.get_text(separator=" ").strip()
                    if len(content_text) > 100:  # 確保內容足夠長
                        break
            
            # 如果找不到內容，使用更通用的方法
            if not content_text or len(content_text) < 100:
                # 移除頭部、底部等
                for element in soup.select("header, footer, nav, aside, .sidebar"):
                    element.extract()
                
                content_text = soup.get_text(separator=" ").strip()
            
            # 清理文本
            if content_text:
                lines = [line.strip() for line in content_text.splitlines() if line.strip()]
                content_text = " ".join(lines)
                # 移除亂碼字符
                content_text = ''.join(char for char in content_text if ord(char) < 65536)
            
            return content_text
        
        except Exception as e:
            logger.warning(f"獲取文章內容時出錯: {str(e)}")
            return "無法獲取文章內容"
