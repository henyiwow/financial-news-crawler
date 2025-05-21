from typing import Dict, Any
from transformers import pipeline
from transformers import BertTokenizer, BertForSequenceClassification
from loguru import logger

class TextSummarizer:
    """文本摘要類"""
    
    def __init__(self, config: Dict[str, Any]):
        self.max_length = config.get('max_length', 100)
        self.language = config.get('language', 'chinese')
        self._initialize_model()
    
    def _initialize_model(self):
        """初始化摘要模型"""
        try:
            # 使用預訓練的中文BERT模型進行摘要
            model_name = "uer/roberta-base-chinese-extractive-qa"
            
            # 使用 transformers 的 summarization pipeline
            if self.language == 'chinese':
                model_name = "ckiplab/bert-base-chinese"
            
            self.summarizer = pipeline(
                "summarization",
                model=model_name,
                tokenizer=model_name
            )
            logger.info(f"已初始化摘要模型: {model_name}")
        except Exception as e:
            logger.error(f"初始化摘要模型時出錯: {str(e)}")
            # 如果模型初始化失敗，採用簡單的摘要策略
            self.summarizer = None
    
    def summarize(self, text: str) -> str:
        """生成文本摘要"""
        if not text:
            return "文章內容為空"
        
        try:
            # 如果有摘要模型可用
            if self.summarizer:
                # 限制輸入長度，避免處理過長的文本
                max_input_length = 1024
                input_text = text[:max_input_length] if len(text) > max_input_length else text
                
                summary = self.summarizer(input_text, max_length=self.max_length, min_length=30, do_sample=False)
                return summary[0]['summary_text']
            else:
                # 使用簡單的摘要方法（取前N個字）
                return self._simple_summarize(text)
        except Exception as e:
            logger.error(f"生成摘要時出錯: {str(e)}")
            return self._simple_summarize(text)
    
    def _simple_summarize(self, text: str) -> str:
        """簡單的文本摘要方法（截取前面的文字）"""
        # 清理文本
        text = text.replace('\n', ' ').strip()
        
        # 取前N個字作為摘要
        if len(text) > self.max_length:
            return text[:self.max_length - 3] + "..."
        return text
