from typing import List, Dict, Any
import yaml
import os
from datetime import datetime
from loguru import logger

def load_config(config_path: str) -> Dict[str, Any]:
    """載入配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        logger.error(f"載入配置文件時出錯: {str(e)}")
        raise

def setup_logger():
    """設置日誌"""
    log_path = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_path, exist_ok=True)
    
    log_file = os.path.join(log_path, f"crawler_{datetime.now().strftime('%Y%m%d')}.log")
    logger.add(log_file, rotation="1 day", retention="7 days", level="INFO")
