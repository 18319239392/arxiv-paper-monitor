"""
APS (American Physical Society) 论文抓取器
当前版本：由于 APS RSS feed 不支持关键词搜索参数，
而大部分 PRL 论文也会同步上传到 arXiv，因此 arXiv 搜索已经覆盖了 PRL 论文。
此类保留作为框架，后续可通过 APS 官方 API 实现更精确的搜索。
"""
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class PRLFetcher:
    BASE_URL = "https://journals.aps.org/feeds/rss.xml"

    def __init__(self, keywords):
        self.keywords = keywords

    def fetch_recent_papers(self, days_back: int = 1) -> List[Dict]:
        """
        从 APS RSS feed 获取近期论文
        注意：RSS feed 不支持关键词过滤，需要获取后在代码中过滤
        """
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days_back + 1)  # 多获取一天作为缓冲

            # RSS feed 不支持搜索参数，直接获取最近的论文
            response = requests.get(self.BASE_URL, timeout=30)
            response.raise_for_status()

            papers = self._parse_rss(response.text, start_date, end_date)
            logger.info(f"PRL/APS: 找到 {len(papers)} 篇近期论文（过滤后）")
            return papers

        except Exception as e:
            logger.warning(f"PRL/APS 获取失败（非致命错误，arXiv搜索通常已覆盖PRL论文）: {e}")
            return []

    def _parse_rss(self, xml_text, start_date, end_date):
        """解析 RSS feed 并按日期和关键词过滤"""
        try:
            import feedparser
        except ImportError:
            logger.warning("feedparser 未安装，跳过 APS 搜索。安装: pip install feedparser")
            return []

        feed = feedparser.parse(xml_text)
        papers = []

        # 构建关键词匹配集合（不区分大小写）
        keyword_set = set(kw.strip().lower() for kw in self.keywords)

        for entry in feed.entries:
            try:
                pub_time = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                # 日期过滤
                if pub_time < start_date or pub_time > end_date:
                    continue

                # 关键词过滤：检查标题和摘要
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                text_to_check = f"{title} {summary}".lower()

                if not any(kw in text_to_check for kw in keyword_set):
                    continue

                paper = {
                    'id': entry.get('id', ''),
                    'title': title,
                    'authors': [a.get('name', '') for a in entry.get('authors', [])],
                    'abstract': summary,
                    'pdf_url': entry.get('links', [{}])[0].get('href', '').replace('abstract', 'pdf') if entry.get('links') else '',
                    'published': pub_time.strftime('%Y-%m-%d %H:%M'),
                    'primary_category': 'PRL',
                    'categories': ['PRL', 'physics.atom-ph'],
                    'arxiv_url': entry.get('link', ''),
                }

                papers.append(paper)
                logger.info(f"PRL: 找到论文: {title[:80]}...")

            except Exception as e:
                logger.debug(f"解析PRL条目失败: {e}")
                continue

        return papers
