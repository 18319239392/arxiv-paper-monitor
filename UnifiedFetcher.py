"""
统一论文抓取器 — 合并 arXiv + 期刊 RSS 两个数据源，去重
"""
from arxiv_fetcher import ArxivFetcher
from journal_rss import JournalRSSFetcher, JOURNAL_RSS_FEEDS
from config import Config
import logging

logger = logging.getLogger(__name__)


class UnifiedPaperFetcher:
    def __init__(self):
        self.arxiv = ArxivFetcher()
        self.journals = JournalRSSFetcher(Config.SEARCH_KEYWORDS)

    def fetch_all(self, days_back=1):
        """从所有数据源获取论文并去重"""
        logger.info(f"数据源: arXiv分类RSS + {len(JOURNAL_RSS_FEEDS)} 个期刊RSS")

        arxiv_papers = self.arxiv.fetch_recent_papers(days_back)
        journal_papers = self.journals.fetch_all(days_back)

        all_papers = arxiv_papers + journal_papers

        # 基于 title 去重（arXiv 预印本 ≈ 期刊发表版）
        seen = set()
        unique = []
        for p in all_papers:
            t = p['title'].lower().strip()
            if t not in seen:
                seen.add(t)
                unique.append(p)

        logger.info(f"总计: arXiv {len(arxiv_papers)}篇 + 期刊 {len(journal_papers)}篇 → 去重后 {len(unique)}篇")
        return unique

    def generate_summary(self, paper):
        return self.arxiv.generate_summary(paper)
