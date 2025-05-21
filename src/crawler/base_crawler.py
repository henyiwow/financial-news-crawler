from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime

class NewItem:
    """新聞項目類"""
    def __init__(self, title: str, content: str, url: str, 
                 published_time: datetime, source: str, keyword: str):
        self.title = title
        self.content = content
        self.url = url
        self.published_time = published_time
        self.source = source
        self.keyword = keyword  # 相關的關鍵詞
    
    def __repr__(self) -> str:
        return f"News(title={self.title}, source={self.source}, keyword={self.keyword})"


class BaseCrawler(ABC):
    """基礎爬蟲抽象類"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.search_terms = config['search_terms']
        self.max_news_per_term = config.get('max_news_per_term', 3)
        self.time_period = config.get('time_period', '1d')
    
    @abstractmethod
    def crawl(self) -> List[NewItem]:
        """執行爬蟲並返回新聞列表"""
        pass
    
    def sort_by_priority(self, news_items: List[NewItem]) -> List[NewItem]:
        """根據關鍵詞優先順序排序新聞"""
        # 為每個關鍵詞創建優先級順序映射
        priority_map = {term: i for i, term in enumerate(self.search_terms)}
        
        # 根據優先級排序
        return sorted(news_items, key=lambda item: priority_map.get(item.keyword, float('inf')))
