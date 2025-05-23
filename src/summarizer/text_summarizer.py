import re
from typing import Dict, Any
from loguru import logger

class TextSummarizer:
    """優化版文字摘要器 - 專注保險新聞摘要"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_length = config.get('max_length', 150)
        self.language = config.get('language', 'zh-TW')
        self.summary_type = config.get('type', 'simple')
        
        # 簡單摘要設定
        self.simple_config = config.get('simple_summary', {
            'max_sentences': 3,
            'min_length': 60,
            'keywords_highlight': True
        })
        
        # 保險相關關鍵詞
        self.insurance_keywords = [
            # 公司名稱
            '新光人壽', '台新人壽', '新光金控', '台新金控', '新光金', '台新金',
            
            # 險種
            '保險', '壽險', '健康險', '醫療險', '意外險', '投資型保險', '利變壽險',
            '年金險', '儲蓄險', '癌症險', '重大疾病險', '實支實付',
            
            # 業務關鍵詞
            '理賠', '給付', '保費', '保單', '承保', '核保', '要保人', '被保險人', '受益人',
            
            # 重要動詞
            '推出', '發布', '宣布', '提供', '調整', '增加', '減少', '暫停', '恢復'
        ]
        
        # 重要數字模式
        self.number_patterns = [
            r'\d+億元?', r'\d+萬元?', r'\d+元', r'\d+%', r'\d+倍',
            r'\d+年', r'\d+月', r'\d+日', r'\d+歲'
        ]
        
        logger.info(f"📝 摘要器初始化完成，類型: {self.summary_type}, 最大長度: {self.max_length}")
    
    def summarize(self, content: str) -> str:
        """生成摘要"""
        if not content or len(content.strip()) < 10:
            return "內容過短，無法生成摘要"
        
        try:
            if self.summary_type == 'simple':
                return self._simple_summarize(content)
            else:
                # 如果設定了AI摘要但無法使用，回退到簡單摘要
                return self._simple_summarize(content)
                
        except Exception as e:
            logger.error(f"❌ 摘要生成失敗: {str(e)}")
            return self._fallback_summary(content)
    
    def _simple_summarize(self, content: str) -> str:
        """智能簡單摘要方法"""
        try:
            # 清理內容
            cleaned_content = self._clean_content(content)
            
            # 分割句子
            sentences = self._split_sentences(cleaned_content)
            
            if not sentences:
                return self._fallback_summary(content)
            
            # 計算句子分數
            sentence_scores = self._calculate_sentence_scores(sentences)
            
            # 選擇最重要的句子
            important_sentences = self._select_important_sentences(
                sentences, sentence_scores
            )
            
            # 組合摘要
            summary = self._combine_summary(important_sentences)
            
            # 限制長度
            if len(summary) > self.max_length:
                summary = summary[:self.max_length-3] + "..."
            
            # 確保最少長度
            if len(summary) < self.simple_config['min_length']:
                summary = self._expand_summary(sentences, summary)
            
            # 最終檢查和優化
            summary = self._optimize_summary(summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ 簡單摘要生成失敗: {str(e)}")
            return self._fallback_summary(content)
    
    def _clean_content(self, content: str) -> str:
        """清理內容"""
        # 移除多餘的空白
        content = re.sub(r'\s+', ' ', content)
        
        # 移除常見的網頁元素
        patterns_to_remove = [
            r'點擊看更多.*?$',
            r'繼續閱讀.*?$',
            r'更多新聞.*?$',
            r'相關新聞.*?$',
            r'廣告.*?$',
            r'AD.*?$',
            r'記者.*?報導',
            r'\[.*?\]',
            r'【.*?】(?!.*保險)',  # 保留包含保險的標籤
            r'圖片來源.*?$',
            r'資料來源.*?$',
        ]
        
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content, flags=re.MULTILINE)
        
        return content.strip()
    
    def _split_sentences(self, content: str) -> list:
        """分割句子"""
        # 中文句子分割
        sentences = re.split(r'[。！？；]', content)
        
        # 過濾短句子和空句子
        sentences = [s.strip() for s in sentences if len(s.strip()) > 8]
        
        # 移除明顯的無關句子
        filtered_sentences = []
        for sentence in sentences:
            # 跳過太短或太長的句子
            if len(sentence) < 10 or len(sentence) > 200:
                continue
            
            # 跳過明顯的廣告或導航文字
            if any(word in sentence for word in ['點擊', '更多', '廣告', '登入', '註冊', '訂閱']):
                continue
            
            filtered_sentences.append(sentence)
        
        return filtered_sentences
    
    def _calculate_sentence_scores(self, sentences: list) -> dict:
        """計算句子重要性分數"""
        scores = {}
        
        for i, sentence in enumerate(sentences):
            score = 0
            sentence_lower = sentence.lower()
            
            # 位置分數（開頭的句子更重要）
            if i == 0:
                score += 5
            elif i == 1:
                score += 3
            elif i < len(sentences) * 0.3:  # 前30%的句子
                score += 2
            
            # 保險關鍵詞分數（根據重要性加權）
            for keyword in self.insurance_keywords:
                if keyword in sentence:
                    if keyword in ['新光人壽', '台新人壽', '新光金控', '台新金控']:
                        score += 5  # 公司名稱高分
                    elif keyword in ['健康險', '醫療險', '投資型保險', '利變壽險', '意外險']:
                        score += 4  # 主要險種
                    elif keyword in ['理賠', '給付', '推出', '發布', '宣布']:
                        score += 3  # 重要動作
                    else:
                        score += 2  # 一般保險詞彙
            
            # 數字和統計資料分數
            for pattern in self.number_patterns:
                if re.search(pattern, sentence):
                    score += 2
            
            # 包含重要動詞的分數
            important_verbs = [
                '宣布', '推出', '發布', '提供', '調整', '增加', '減少',
                '理賠', '給付', '承保', '拒保', '暫停', '恢復', '修正'
            ]
            for verb in important_verbs:
                if verb in sentence:
                    score += 2
            
            # 句子長度分數（適中長度加分）
            if 20 <= len(sentence) <= 100:
                score += 1
            elif len(sentence) > 150:
                score -= 1  # 太長的句子扣分
            
            # 包含引號的句子（可能是重要聲明）
            if '「' in sentence or '『' in sentence or '"' in sentence:
                score += 1
            
            # 包含具體時間的句子
            if re.search(r'\d{4}年|\d+月\d+日|今年|明年|去年', sentence):
                score += 1
            
            scores[i] = score
        
        return scores
    
    def _select_important_sentences(self, sentences: list, scores: dict) -> list:
        """選擇重要句子"""
        max_sentences = self.simple_config['max_sentences']
        
        # 按分數排序
        sorted_indices = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        
        # 選擇前N個句子，但確保第一句總是被包含（如果分數不太低）
        selected_indices = []
        
        # 優先選擇高分句子
        for idx in sorted_indices:
            if len(selected_indices) >= max_sentences:
                break
            selected_indices.append(idx)
        
        # 按原始順序排列
        selected_indices.sort()
        
        return [sentences[i] for i in selected_indices if i < len(sentences)]
    
    def _combine_summary(self, sentences: list) -> str:
        """組合摘要"""
        if not sentences:
            return "無法生成摘要"
        
        # 確保句子之間的邏輯連接
        summary_parts = []
        
        for i, sentence in enumerate(sentences):
            # 清理句子
            sentence = sentence.strip()
            
            # 確保句子結尾正確
            if not sentence.endswith(('。', '！', '？')):
                sentence += '。'
            
            summary_parts.append(sentence)
        
        summary = ''.join(summary_parts)
        return summary
    
    def _expand_summary(self, sentences: list, current_summary: str) -> str:
        """擴展摘要（如果太短）"""
        if len(current_summary) >= self.simple_config['min_length']:
            return current_summary
        
        # 找到更多相關句子
        additional_sentences = []
        current_length = len(current_summary)
        
        for sentence in sentences:
            if sentence not in current_summary and current_length < self.max_length:
                # 檢查是否包含保險關鍵詞
                if any(keyword in sentence for keyword in self.insurance_keywords):
                    additional_sentences.append(sentence)
                    current_length += len(sentence)
                    if len(additional_sentences) >= 2:  # 最多加2句
                        break
        
        if additional_sentences:
            expanded = current_summary.rstrip('。') + '。' + ''.join([s + '。' if not s.endswith(('。', '！', '？')) else s for s in additional_sentences])
            return expanded
        
        return current_summary
    
    def _optimize_summary(self, summary: str) -> str:
        """優化摘要"""
        # 移除重複的句號
        summary = re.sub(r'。+', '。', summary)
        
        # 確保摘要以句號結尾
        if not summary.endswith(('。', '！', '？')):
            summary += '。'
        
        # 移除開頭和結尾的空白
        summary = summary.strip()
        
        return summary
    
    def _fallback_summary(self, content: str) -> str:
        """備用摘要方法"""
        try:
            # 簡單地取前100字，並在適當位置截斷
            cleaned = self._clean_content(content)
            if len(cleaned) <= self.max_length:
                return cleaned
            
            # 找到第一個句號位置
            truncated = cleaned[:self.max_length]
            last_period = truncated.rfind('。')
            
            if last_period > 50:  # 確保有足夠內容
                return truncated[:last_period + 1]
            else:
                return truncated[:self.max_length - 3] + "..."
                
        except Exception as e:
            logger.error(f"❌ 備用摘要也失敗: {str(e)}")
            return "摘要生成失敗，請查看原文"
