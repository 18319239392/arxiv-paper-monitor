import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # 邮箱配置
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

    # 搜索配置
    SEARCH_KEYWORDS = os.getenv("SEARCH_KEYWORDS", "Rydberg atom").split(",")
    MAX_RESULTS = int(os.getenv("MAX_RESULTS", 20))

    @classmethod
    def validate(cls):
        if not cls.EMAIL_SENDER or not cls.EMAIL_PASSWORD:
            raise ValueError("邮箱配置不完整，请检查环境变量 EMAIL_SENDER, EMAIL_PASSWORD")
        return True
