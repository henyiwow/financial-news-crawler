from typing import Dict, Any
import re
from loguru import logger

class TextSummarizer:
    """文本摘要類"""
    
    def __init__(self, config: Dict[str, Any]):
        self.max_length = config.get('max_length', 100)
        self.language = config.get('language', 'chinese')
    
    def summarize(self, text: str) -> str:
        """生成文本摘要"""
        if not text:
            return "文章內容為空"
        
        try:
            # 使用智能摘要方法
            return self._intelligent_summarize(text)
        except Exception as e:
            logger.error(f"生成摘要時出錯: {str(e)}")
            return self._simple_summarize(text)
    
    def _intelligent_summarize(self, text: str) -> str:
        """智能摘要方法"""
        # 清理文本
        text = self._clean_text(text)
        
        if len(text) <= self.max_length:
            return text
        
        # 分句
        sentences = self._split_sentences(text)
        
        if not sentences:
            return self._simple_summarize(text)
        
        # 如果只有一句話且太長，直接截取
        if len(sentences) == 1:
            return sentences[0][:self.max_length - 3] + "..."
        
        # 選擇重要句子
        important_sentences = self._select_important_sentences(sentences)
        
        # 組合摘要
        summary = ""
        for sentence in important_sentences:
            if len(summary + sentence) <= self.max_length - 3:
                summary += sentence
            else:
                break
        
        # 如果摘要太短，添加更多內容
        if len(summary) < self.max_length * 0.5 and len(important_sentences) > len(summary.split('。')) - 1:
            for sentence in sentences:
                if sentence not in summary and len(summary + sentence) <= self.max_length - 3:
                    summary += sentence
                else:
                    break
        
        # 確保摘要不超過限制
        if len(summary) > self.max_length:
            summary = summary[:self.max_length - 3] + "..."
        
        return summary or self._simple_summarize(text)
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多餘的空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 移除常見的無用信息
        useless_patterns = [
            r'記者\s*\w+\s*報導',
            r'編輯\s*\w+\s*報導',
            r'攝影[：:]\s*\w+',
            r'圖片來源[：:]\s*\w+',
            r'資料來源[：:]\s*\w+',
            r'\[廣告\]',
            r'\[AD\]',
            r'延伸閱讀[：:]',
            r'相關新聞[：:]',
            r'更多.*內容',
            r'點我看更多',
            r'繼續閱讀',
            r'※.*版權.*',
            r'©.*版權.*',
        ]
        
        for pattern in useless_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def _split_sentences(self, text: str) -> list:
        """將文本分句"""
        # 中文分句標點
        sentence_endings = r'[。！？；.]'
        sentences = re.split(sentence_endings, text)
        
        # 清理並過濾句子
        clean_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # 過濾太短的句子
                clean_sentences.append(sentence + '。')
        
        return clean_sentences
    
    def _select_important_sentences(self, sentences: list) -> list:
        """選擇重要句子"""
        # 關鍵詞列表（用於判斷句子重要性）
        important_keywords = [
            # 公司和金融機構
            '新光', '台新', '金控', '銀行', '保險', '壽險',
            # 財務指標
            '營收', '獲利', '股價', '市值', '配息', '股利', 'EPS', '本益比',
            # 市場動態
            '上漲', '下跌', '成長', '衰退', '投資', '買進', '賣出',
            # 政策和法規
            '央行', '利率', '政策', '法規', '監管',
            # 重要事件
            '宣布', '發布', '公告', '簽署', '合作', '併購'
        ]
        
        # 計算每句的重要性分數
        sentence_scores = []
        for sentence in sentences:
            score = 0
            
            # 根據關鍵詞計分
            for keyword in important_keywords:
                if keyword in sentence:
                    score += 1
            
            # 根據句子位置計分（開頭的句子通常更重要）
            position_score = len(sentences) - sentences.index(sentence)
            score += position_score * 0.1
            
            # 根據句子長度計分（適中長度的句子通常更重要）
            length = len(sentence)
            if 20 <= length <= 80:
                score += 1
            elif 10 <= length <= 120:
                score += 0.5
            
            sentence_scores.append((sentence, score))
        
        # 按分數排序並選擇前幾句
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 選擇分數最高的句子，但保持原有順序
        selected_sentences = []
        for sentence, score in sentence_scores[:3]:  # 最多選3句
            if sentence not in [s for s, _ in selected_sentences]:
                selected_sentences.append((sentence, sentences.index(sentence)))
        
        # 按原有順序排序
        selected_sentences.sort(key=lambda x: x[1])
        
        return [sentence for sentence, _ in selected_sentences]
    
    def _simple_summarize(self, text: str) -> str:
        """簡單的文本摘要方法（截取前面的文字）"""
        text = self._clean_text(text)
        
        if len(text) > self.max_length:
            return text[:self.max_length - 3] + "..."
        return text
