import os
import sys
import yaml
import schedule
import time
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger

# 添加專案根目錄到系統路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.google_news_crawler import GoogleNewsCrawler
from src.crawler.rss_crawler import RssCrawler  # 添加這行
from src.summarizer.text_summarizer import TextSummarizer
from src.notification.line_notifier import LineNotifier
from src.crawler.utils import load_config, setup_logger

def run_crawler():
    """執行爬蟲、摘要和通知流程"""
    start_time = datetime.now()
    logger.info(f"開始執行爬蟲任務: {start_time}")
    
    try:
        # 載入配置
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.yaml')
        config = load_config(config_path)
        
        # 初始化爬蟲
        crawler = GoogleNewsCrawler(config['crawler'])
        
        # 爬取新聞
        news_items = crawler.crawl()
        logger.info(f"爬取到 {len(news_items)} 條新聞")
        
        if not news_items:
            logger.info("沒有找到相關新聞，任務結束")
            return
        
        # 初始化摘要器
        summarizer = TextSummarizer(config['summarizer'])
        
        # 生成摘要
        news_summaries = []
        for item in news_items:
            summary = summarizer.summarize(item.content)
            
            news_summaries.append({
                'title': item.title,
                'summary': summary,
                'url': item.url,
                'source': item.source,
                'keyword': item.keyword,
                'published_time': item.published_time
            })
            
            logger.info(f"已生成摘要: {item.title[:30]}...")
        
        # 初始化Line通知
        notifier = LineNotifier(config['line_notify'])
        
        # 發送摘要到Line
        sent = notifier.send_news_summary(news_summaries)
        if sent:
            logger.info("成功發送Line通知")
        else:
            logger.error("發送Line通知失敗")
        
    except Exception as e:
        logger.error(f"執行爬蟲任務時出錯: {str(e)}")
    
    end_time = datetime.now()
    logger.info(f"爬蟲任務結束，耗時: {end_time - start_time}")

def main():
    """主函數"""
    # 設置日誌
    setup_logger()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        # 立即執行
        run_crawler()
    else:
        # 排程每天執行
        logger.info("設置排程任務...")
        # 每天早上 8:00 執行爬蟲任務 (台灣時間)
        schedule.every().day.at("08:00").do(run_crawler)
        
        logger.info("爬蟲服務已啟動，等待排程執行...")
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    main()
