import re
from typing import Dict, Any
from loguru import logger

class TextSummarizer:
    """修正版文字摘要器 - 解決逗號問題"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_length = config.get('max_length', 120)
        self.language = config.get('language', 'zh-TW')
        self.summary_type = config.get('type', 'simple')
        
        # 保險相關關鍵詞
        self.insurance_keywords = [
            '新光人壽', '台新人壽', '新光金控', '台新金控',
            '保險', '壽險', '健康險', '醫療險', '意外險', '投資型保險', 
            '利變壽險', '年金險', '儲蓄險', '理賠', '給付', '保費', '保單'
        ]
        
        logger.info(f"📝 摘要器初始化完成，最大長度: {self.max_length}")
    
    def summarize(self, content: str) -> str:
        """生成摘要 - 修正版"""
        if not content or len(content.strip()) < 20:
            return "內容過短，無法生成摘要"
        
        try:
            # 使用簡化但穩定的摘要方法
            return self._create_clean_summary(content)
                
        except Exception as e:
            logger.error(f"❌ 摘要生成失敗: {str(e)}")
            return self._simple_fallback(content)
    
    def _create_clean_summary(self, content: str) -> str:
        """創建乾淨的摘要"""
        try:
            # 1. 清理內容
            cleaned_content = self._deep_clean_content(content)
            
            # 2. 分割成有意義的句子
            sentences = self._extract_meaningful_sentences(cleaned_content)
            
            if not sentences:
                return self._simple_fallback(content)
            
            # 3. 選擇最重要的1-2句
            important_sentences = self._select_best_sentences(sentences)
            
            # 4. 組合成摘要
            summary = self._build_summary(important_sentences)
            
            # 5. 最終清理
            summary = self._final_cleanup(summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ 創建摘要失敗: {str(e)}")
            return self._simple_fallback(content)
    
    def _deep_clean_content(self, content: str) -> str:
        """深度清理內容"""
        # 移除HTML標籤
        content = re.sub(r'<[^>]+>', '', content)
        
        # 移除多餘空白和特殊字符
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'[^\u4e00-\u9fff\w\s。！？；：，（）「」『』""''．]', '', content)
        
        # 移除常見無用文字
        remove_patterns = [
            r'點擊.*?更多',
            r'繼續閱讀.*',
            r'更多新聞.*',
            r'記者.*?報導',
            r'【.*?】',
            r'\[.*?\]',
            r'圖片來源.*',
            r'資料來源.*',
            r'廣告.*',
            r'AD.*'
        ]
        
        for pattern in remove_patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        return content.strip()
    
    def _extract_meaningful_sentences(self, content: str) -> list:
        """提取有意義的句子"""
        # 按句號分割
        sentences = re.split(r'[。！？]', content)
        
        meaningful_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            
            # 過濾條件
            if len(sentence) < 15:  # 太短
                continue
            if len(sentence) > 150:  # 太長
                continue
            if not any(keyword in sentence for keyword in ['保險', '壽險', '新光', '台新', '理賠', '保單', '醫療', '健康', '意外', '投資']):
                continue
            
            # 移除開頭的連接詞
            sentence = re.sub(r'^[，,、而且此外另外同時]', '', sentence)
            sentence = sentence.strip()
            
            if sentence:
                meaningful_sentences.append(sentence)
        
        return meaningful_sentences
    
    def _select_best_sentences(self, sentences: list) -> list:
        """選擇最佳句子"""
        if not sentences:
            return []
        
        # 計算每個句子的分數
        scored_sentences = []
        
        for sentence in sentences:
            score = 0
            
            # 包含公司名稱加分
            if any(company in sentence for company in ['新光人壽', '台新人壽', '新光金控', '台新金控']):
                score += 10
            
            # 包含具體險種加分
            if any(product in sentence for product in ['健康險', '醫療險', '投資型保險', '利變壽險', '意外險']):
                score += 8
            
            # 包含重要動作加分
            if any(action in sentence for action in ['推出', '發布', '宣布', '理賠', '給付', '調整']):
                score += 6
            
            # 包含數字資訊加分
            if re.search(r'\d+[億萬元%]', sentence):
                score += 4
            
            # 句子長度適中加分
            if 20 <= len(sentence) <= 80:
                score += 2
            
            scored_sentences.append((sentence, score))
        
        # 按分數排序，取前2句
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # 最多取2句，總長度不超過限制
        selected = []
        total_length = 0
        
        for sentence, score in scored_sentences[:3]:
            if total_length + len(sentence) <= self.max_length - 10:
                selected.append(sentence)
                total_length += len(sentence)
                
                if len(selected) >= 2:  # 最多2句
                    break
        
        return selected
    
    def _build_summary(self, sentences: list) -> str:
        """構建摘要"""
        if not sentences:
            return "無法提取關鍵資訊"
        
        # 清理每個句子並組合
        clean_sentences = []
        
        for sentence in sentences:
            # 移除句子開頭的逗號和連接詞
            sentence = re.sub(r'^[，,、]', '', sentence)
            sentence = sentence.strip()
            
            # 確保句子有適當結尾
            if not sentence.endswith(('。', '！', '？')):
                sentence += '。'
            
            clean_sentences.append(sentence)
        
        # 用句號連接（不用逗號）
        summary = ''.join(clean_sentences)
        
        return summary
    
    def _final_cleanup(self, summary: str) -> str:
        """最終清理"""
        # 移除多餘的逗號
        summary = re.sub(r'，+', '，', summary)
        summary = re.sub(r',+', '，', summary)
        
        # 移除句子間的逗號（這是造成問題的主因）
        summary = re.sub(r'。，', '。', summary)
        summary = re.sub(r'，(?=[。！？])', '', summary)
        
        # 移除重複的句號
        summary = re.sub(r'。+', '。', summary)
        
        # 移除開頭和結尾的標點符號
        summary = re.sub(r'^[，,。]', '', summary)
        
        # 確保結尾正確
        if not summary.endswith(('。', '！', '？')):
            summary += '。'
        
        # 長度控制
        if len(summary) > self.max_length:
            # 在適當位置截斷
            truncated = summary[:self.max_length]
            last_period = truncated.rfind('。')
            if last_period > 30:
                summary = truncated[:last_period + 1]
            else:
                summary = truncated[:self.max_length - 3] + '...'
        
        return summary.strip()
    
    def _simple_fallback(self, content: str) -> str:
        """簡單備用方案"""
        try:
            # 清理內容
            content = re.sub(r'<[^>]+>', '', content)
            content = re.sub(r'\s+', ' ', content)
            
            # 找第一個包含保險關鍵詞的段落
            sentences = content.split('。')
            
            for sentence in sentences:
                sentence = sentence.strip()
                if (len(sentence) > 20 and 
                    any(keyword in sentence for keyword in self.insurance_keywords)):
                    
                    # 清理並返回
                    sentence = re.sub(r'^[，,、]', '', sentence)
                    if not sentence.endswith(('。', '！', '？')):
                        sentence += '。'
                    
                    if len(sentence) > self.max_length:
                        sentence = sentence[:self.max_length - 3] + '...'
                    
                    return sentence
            
            # 如果找不到，返回前80字
            clean_content = content[:80].strip()
            if not clean_content.endswith(('。', '！', '？')):
                clean_content += '...'
            
            return clean_content
            
        except Exception as e:
            logger.error(f"❌ 備用方案失敗: {str(e)}")
            return "無法生成摘要，請查看原文。"
