import schedule
import time
import logging
import os
from datetime import datetime
from loguru import logger

from config import Config
from arxiv_fetcher import ArxivFetcher
from email_sender import EmailSender

# 配置日志
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

logger.add(
    os.path.join(log_dir, "arxiv_digest_{time:YYYY-MM-DD}.log"),
    rotation="00:00",  # 每天午夜轮转
    retention="30 days",  # 保留30天
    level="INFO",
    encoding="utf-8"
)

class ArxivDailyDigest:
    def __init__(self):
        self.fetcher = ArxivFetcher()
        self.email_sender = EmailSender()
        
    def run(self, test_mode=False):
        """运行一次任务"""
        logger.info("=" * 60)
        logger.info(f"开始执行Arxiv论文抓取任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # 1. 获取论文
            days_back = 0 if test_mode else 1
            papers = self.fetcher.fetch_recent_papers(days_back=days_back)
            
            # 2. 生成摘要
            summaries = []
            if papers:
                summaries = [self.fetcher.generate_summary(paper) for paper in papers]
                logger.info(f"找到 {len(papers)} 篇相关论文")
            else:
                logger.info("今日没有找到相关论文，将发送『无新论文』通知")
            
            # 3. 总是发送邮件（无论有无论文）
            success = self.email_sender.send_digest(papers, summaries)
            
            if success:
                if papers:
                    logger.info(f"✅ 任务完成！成功发送 {len(papers)} 篇论文摘要")
                else:
                    logger.info("✅ 任务完成！已发送『今日无新论文』通知")
            else:
                logger.error("邮件发送失败")
                
        except Exception as e:
            logger.exception(f"任务执行失败: {e}")
        
        logger.info("=" * 60)
    
    def schedule_job(self):
        """定时任务"""
        # 每天9点执行
        schedule.every().day.at(Config.SCHEDULE_TIME).do(self.run)
        
        # 测试：每分钟执行一次
        if Config.TEST_MODE:
            logger.warning("⚠️  测试模式已开启，每分钟执行一次")
            schedule.every(1).minutes.do(self.run)
            # 立即执行一次
            self.run(test_mode=True)
        
        logger.info(f"定时任务已启动，将在每天 {Config.SCHEDULE_TIME} 执行")
        logger.info("按 Ctrl+C 退出程序")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            logger.info("程序已退出")

def main():
    """主函数"""
    # 验证配置
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"配置错误: {e}")
        logger.info("请检查 .env 文件是否配置正确")
        return
    
    # 创建并运行
    digest = ArxivDailyDigest()
    
    # 如果是测试模式或手动运行，只执行一次
    if Config.TEST_MODE:
        logger.info("运行测试模式...")
        digest.run(test_mode=True)
    else:
        digest.schedule_job()

if __name__ == "__main__":
    main()