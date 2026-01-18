import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 邮箱配置
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
    
    # Arxiv配置
    SEARCH_KEYWORDS = os.getenv("SEARCH_KEYWORDS", "Rydberg atom").split(",")
    MAX_RESULTS = int(os.getenv("MAX_RESULTS", 20))
    
    # 定时任务配置
    SCHEDULE_TIME = "09:00"  # 每天9点
    TEST_MODE = False  # 测试模式，为True时立即运行
    
    # 日志配置
    LOG_FILE = "logs/arxiv_digest.log"
    
    @classmethod
    def validate(cls):
        """验证配置"""
        if not cls.EMAIL_SENDER or not cls.EMAIL_PASSWORD:
            raise ValueError("邮箱配置不完整，请检查.env文件")
        return True