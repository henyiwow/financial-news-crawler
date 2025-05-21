# 金融保險新聞爬蟲與Line推播

此專案是一個自動化工具，用於每日爬取特定金融保險相關新聞，生成簡短摘要，並通過Line通知發送給用戶。

## 功能特點

- 每日自動爬取台灣地區24小時內的金融與保險相關新聞（新光人壽、新光金控、台新金控、台新人壽、金控、壽險、健康險、意外險）
- 按照關鍵詞優先順序排序新聞
- 為每則新聞生成100字內的摘要
- 通過Line發送新聞摘要通知
- 自動截斷過長的Line訊息
- 使用GitHub Actions實現每天早上8:00自動執行

## 安裝與設置

### 前置條件

- Python 3.8+
- Line Messaging API帳號與Channel Access Token
- GitHub帳號（用於GitHub Actions自動執行）

### 安裝步驟

1. 克隆此專案
   ```bash
   git clone https://github.com/yourusername/financial-news-crawler.git
   cd financial-news-crawler
