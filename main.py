"""
arXiv + 期刊 论文每日摘要 — 适配 GitHub Actions
每天获取过去 24 小时的 Rydberg atom 相关论文，邮件推送
"""
import os
from datetime import datetime
import logging

from config import Config
from UnifiedFetcher import UnifiedPaperFetcher
from email_sender import EmailSender

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class ArxivDailyDigest:
    def __init__(self):
        self.fetcher = UnifiedPaperFetcher()
        self.email_sender = EmailSender()

    def run(self):
        """运行一次论文抓取 + 邮件发送"""
        logger.info("=" * 60)
        logger.info(f"开始执行论文抓取任务 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # 获取过去 24 小时的论文
            papers = self.fetcher.fetch_all(days_back=1)

            # 生成摘要
            summaries = []
            if papers:
                summaries = [self.fetcher.generate_summary(paper) for paper in papers]
                logger.info(f"找到 {len(papers)} 篇相关论文")
            else:
                logger.info("今日没有找到相关论文，将发送『无新论文』通知")

            # 发送邮件
            success = self.email_sender.send_digest(papers, summaries)
            if success:
                logger.info(f"✅ 任务完成！{'成功发送 ' + str(len(papers)) + ' 篇论文摘要' if papers else '已发送『今日无新论文』通知'}")
            else:
                logger.error("邮件发送失败")

        except Exception as e:
            logger.exception(f"任务执行失败: {e}")

        logger.info("=" * 60)


def main():
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"配置错误: {e}")
        return

    digest = ArxivDailyDigest()

    if os.getenv('GITHUB_ACTIONS') == 'true' or os.getenv('RUN_MODE') == 'ci':
        logger.info("CI/CD 环境，单次运行模式")
    else:
        logger.info("本地环境，单次运行模式")

    digest.run()
    logger.info("任务执行完毕")


if __name__ == "__main__":
    main()
