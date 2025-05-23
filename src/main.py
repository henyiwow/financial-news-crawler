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
from src.crawler.rss_crawler import RssCrawler
from src.crawler.finance_direct_crawler import FinanceNewsDirectCrawler
from src.summarizer.text_summarizer import TextSummarizer
from src.notification.line_notifier import LineNotifier
from src.crawler.utils import load_config, setup_logger

def run_crawler():
    """執行爬蟲、摘要和通知流程 - 優化版本"""
    start_time = datetime.now()
    logger.info(f"🚀 開始執行保險新聞爬蟲任務: {start_time}")
    
    try:
        # 載入配置
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.yaml')
        config = load_config(config_path)
        
        # 輸出配置資訊用於診斷
        logger.info(f"✅ 配置檔案載入成功")
        logger.info(f"📡 啟用的爬蟲來源: {config['crawler'].get('sources', [])}")
        logger.info(f"🔍 搜尋關鍵詞: {config['crawler'].get('search_terms', [])}")
        logger.info(f"⏰ 時間限制: {config['crawler'].get('hours_limit', 24)} 小時")
        
        all_news = []
        
        # 優先使用財經新聞直接爬蟲，因為這更有可能找到相關新聞
        if 'finance_direct' in config['crawler']['sources']:
            logger.info("=== 🏢 開始使用財經新聞直接爬蟲 ===")
            try:
                finance_crawler = FinanceNewsDirectCrawler(config['crawler'])
                finance_news = finance_crawler.crawl()
                all_news.extend(finance_news)
                logger.info(f"🏢 財經直接爬蟲結果: {len(finance_news)} 條新聞")
                
                # 輸出詳細資訊
                for i, news in enumerate(finance_news[:5]):
                    logger.info(f"  📰 財經新聞 {i+1}: {news.title[:50]}... (🏷️ {news.keyword})")
                    
            except Exception as e:
                logger.error(f"❌ 財經直接爬蟲執行錯誤: {str(e)}")
        
        # 使用Google新聞爬蟲
        if 'google_news' in config['crawler']['sources']:
            logger.info("=== 🔍 開始使用Google新聞爬蟲 ===")
            try:
                google_crawler = GoogleNewsCrawler(config['crawler'])
                google_news = google_crawler.crawl()
                all_news.extend(google_news)
                logger.info(f"🔍 Google新聞爬蟲結果: {len(google_news)} 條新聞")
                
                # 輸出詳細資訊
                for i, news in enumerate(google_news[:5]):
                    logger.info(f"  📰 Google新聞 {i+1}: {news.title[:50]}... (🏷️ {news.keyword})")
                    
            except Exception as e:
                logger.error(f"❌ Google新聞爬蟲執行錯誤: {str(e)}")
        
        # 使用RSS爬蟲
        if 'rss' in config['crawler']['sources']:
            logger.info("=== 📡 開始使用RSS爬蟲 ===")
            try:
                rss_crawler = RssCrawler(config['crawler'])
                rss_news = rss_crawler.crawl()
                all_news.extend(rss_news)
                logger.info(f"📡 RSS爬蟲結果: {len(rss_news)} 條新聞")
                
                # 輸出詳細資訊
                for i, news in enumerate(rss_news[:5]):
                    logger.info(f"  📰 RSS新聞 {i+1}: {news.title[:50]}... (🏷️ {news.keyword})")
                    
            except Exception as e:
                logger.error(f"❌ RSS爬蟲執行錯誤: {str(e)}")
        
        logger.info(f"📊 === 所有爬蟲完成，總共獲得 {len(all_news)} 條新聞 ===")
        
        # 詳細輸出前10條新聞供診斷
        if all_news:
            logger.info("📋 === 前10條新聞詳細列表 ===")
            for i, news in enumerate(all_news[:10]):
                logger.info(f"📰 新聞 {i+1}:")
                logger.info(f"  📋 標題: {news.title}")
                logger.info(f"  🏢 來源: {news.source}")
                logger.info(f"  🏷️ 關鍵詞: {news.keyword}")
                logger.info(f"  📅 時間: {news.published_time}")
                logger.info(f"  📄 內容長度: {len(news.content or '')} 字元")
                logger.info(f"  👀 內容預覽: {(news.content or '')[:100]}...")
                logger.info("  ────────────")
        
        # 根據關鍵詞優先排序所有新聞
        if all_news:
            priority_map = {term: i for i, term in enumerate(config['crawler']['search_terms'])}
            all_news = sorted(all_news, key=lambda item: (
                priority_map.get(item.keyword, float('inf')),
                -item.published_time.timestamp()
            ))
            logger.info(f"🔄 新聞按優先級和時間排序完成")
        
        if not all_news:
            logger.warning("⚠️ 沒有找到任何相關新聞！")
            logger.info("🔍 可能的原因：")
            logger.info("  1. 關鍵詞設定過於嚴格")
            logger.info("  2. 新聞來源網站結構變更")
            logger.info("  3. 網路連線問題")
            logger.info("  4. 24小時內沒有相關保險新聞")
            logger.info("💡 建議：檢查關鍵詞設定或增加時間範圍")
            return
        
        # 取前15條最相關的新聞
        selected_news = all_news[:15]
        logger.info(f"🎯 選擇前 {len(selected_news)} 條最相關新聞進行摘要")
        
        # 初始化摘要器
        logger.info("📝 === 開始生成摘要 ===")
        try:
            summarizer = TextSummarizer(config['summarizer'])
            logger.info(f"✅ 摘要器初始化成功")
        except Exception as e:
            logger.error(f"❌ 摘要器初始化失敗: {str(e)}")
            logger.info("🔄 使用備用摘要方案")
            summarizer = None
        
        # 生成摘要
        news_summaries = []
        for i, item in enumerate(selected_news):
            logger.info(f"📝 正在處理第 {i+1}/{len(selected_news)} 條新聞: {item.title[:40]}...")
            
            try:
                if summarizer:
                    summary = summarizer.summarize(item.content)
                else:
                    # 備用方案：使用內容的前120字作為摘要
                    content_preview = (item.content or "無內容")
                    if len(content_preview) > 120:
                        summary = content_preview[:120] + "..."
                    else:
                        summary = content_preview
                
                news_summaries.append({
                    'title': item.title,
                    'summary': summary,
                    'url': item.url,
                    'source': item.source,
                    'keyword': item.keyword,
                    'published_time': item.published_time.strftime("%Y-%m-%d %H:%M")
                })
                
                logger.info(f"  ✅ 摘要: {summary[:60]}...")
                
            except Exception as e:
                logger.error(f"❌ 生成摘要時出錯: {str(e)}")
                # 使用標題作為摘要
                news_summaries.append({
                    'title': item.title,
                    'summary': f"無法生成摘要，請查看原文。",
                    'url': item.url,
                    'source': item.source,
                    'keyword': item.keyword,
                    'published_time': item.published_time.strftime("%Y-%m-%d %H:%M")
                })
        
        logger.info(f"📝 === 摘要生成完成，共 {len(news_summaries)} 條 ===")
        
        # 輸出摘要供檢查
        logger.info("📋 === 摘要內容預覽 ===")
        for i, summary_item in enumerate(news_summaries[:3]):
            logger.info(f"📰 摘要 {i+1}:")
            logger.info(f"  📋 {summary_item['title']}")
            logger.info(f"  📝 {summary_item['summary']}")
            logger.info(f"  🏷️ {summary_item['keyword']}")
            logger.info("  ────────────")
        
        if len(news_summaries) > 3:
            logger.info(f"📊 還有 {len(news_summaries) - 3} 條摘要...")
        
        # 初始化Line通知
        logger.info("📱 === 開始Line通知 ===")
        try:
            notifier = LineNotifier(config['line_notify'])
            
            # 發送摘要到Line
            sent = notifier.send_news_summary(news_summaries)
            if sent:
                logger.info(f"✅ 成功發送 {len(news_summaries)} 條新聞到Line")
            else:
                logger.error("❌ 發送Line通知失敗")
                
        except Exception as e:
            logger.error(f"❌ Line通知執行錯誤: {str(e)}")
            logger.info("📱 跳過Line通知，摘要已生成完成")
        
    except Exception as e:
        logger.error(f"❌ 執行爬蟲任務時出錯: {str(e)}")
        import traceback
        logger.error(f"🔍 詳細錯誤: {traceback.format_exc()}")
    
    end_time = datetime.now()
    logger.info(f"🏁 === 爬蟲任務結束，總耗時: {end_time - start_time} ===")

def main():
    """主函數"""
    # 設置詳細的日誌
    setup_logger()
    
    # 設置日誌等級
    logger.remove()
    logger.add(
        "insurance_crawler.log", 
        level="INFO", 
        rotation="1 day",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )
    logger.add(
        sys.stdout, 
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}"
    )
    
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        # 立即執行
        logger.info("🚀 === 立即執行保險新聞爬蟲 ===")
        run_crawler()
    else:
        # 排程每天執行
        logger.info("⏰ 設置排程任務...")
        # 每天早上 8:00 執行爬蟲任務 (台灣時間)
        schedule.every().day.at("08:00").do(run_crawler)
        
        logger.info("🤖 爬蟲服務已啟動，等待排程執行...")
        logger.info("📅 執行時間：每天早上 8:00")
        logger.info("💡 手動執行請使用：python main.py --now")
        
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    main()
