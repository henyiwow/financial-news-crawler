# 尋找來源 - 使用更多選擇器
                    source_elements = [
                        div.find("div", class_="CEMjEf"),
                        div.find("div", class_="UPmit"),
                        div.find("span", class_="xQ82C"),
                        div.find("div", class_="BNeawe"),  # 新增
                        div.find("cite"),                  # 新增
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
                    
                    # 尋找時間 - 使用更多選擇器
                    time_elements = [
                        div.find("div", class_="OSrXXb"),
                        div.find("span", class_="WG9SHc"),
                        div.find("time"),
                        div.find("span", class_="f"),      # 新增
                        div.find("div", class_="slp"),     # 新增
                        div.find(["span", "div"], string=lambda s: "前" in s if s else False),
                    ]
                    
                    for element in time_elements:
                        if element and element.get_text().strip():
                            time_text = element.get_text().strip()
                            break
                    
                    # 確保所有必需元素都存在
                    if not title or not url:
                        continue
                    
                    # 設置默認來源
                    if not source:
                        source = "Google新聞"
                    
                    # 解析發布時間
                    pub_time = datetime.now()
                    if time_text:
                        # 嘗試解析多種時間格式
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
            time.sleep(random.uniform(0.3, 0.8))
            
            response = requests.get(url, headers=self.headers, timeout=10)
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
                ".entry-content"
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
