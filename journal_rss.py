"""
期刊 RSS 抓取器 — 支持 PRL、Nature、Science、Optica、APL 系列
通过各期刊的 RSS 源获取最新论文，按关键词过滤
"""
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import logging
import time

logger = logging.getLogger(__name__)

# ========================
# 期刊 RSS 源配置
# ========================
# 格式: (显示名称, RSS URL)
JOURNAL_RSS_FEEDS: List[tuple] = [
    # --- APS (Physical Review) ---
    ("PRL", "https://journals.aps.org/prl/rss"),
    ("PRA", "https://journals.aps.org/pra/rss"),
    ("PRB", "https://journals.aps.org/prb/rss"),
    ("PRX", "https://journals.aps.org/prx/rss"),
    ("PRResearch", "https://journals.aps.org/prresearch/rss"),

    # --- Nature 系列 ---
    ("Nature", "https://www.nature.com/nature.rss"),
    ("Nature Physics", "https://www.nature.com/nphys.rss"),
    ("Nature Photonics", "https://www.nature.com/nphoton.rss"),
    ("Nature Nanotechnology", "https://www.nature.com/nnano.rss"),
    ("Nature Materials", "https://www.nature.com/nmat.rss"),
    ("Nature Chemistry", "https://www.nature.com/nchem.rss"),
    ("Nature Communications", "https://www.nature.com/ncomms.rss"),
    ("Nature Quantum Info", "https://www.nature.com/npjqi.rss"),

    # --- Science 系列 ---
    ("Science", "https://www.science.org/rss/current.xml"),
    ("Science Advances", "https://www.science.org/rss/advances_current.xml"),

    # --- Optica 系列 ---
    ("Optica", "https://opg.optica.org/optica/rss.cfm"),
    ("Optics Letters", "https://opg.optica.org/ol/rss.cfm"),
    ("Optics Express", "https://opg.optica.org/oe/rss.cfm"),
    ("Photonics Research", "https://opg.optica.org/prj/rss.cfm"),
    ("JOSA B", "https://opg.optica.org/josab/rss.cfm"),

    # --- AIP (APL) 系列 ---
    ("APL", "https://pubs.aip.org/aip/apl/rss"),
    ("APL Photonics", "https://pubs.aip.org/aip/app/rss"),
    ("J. Appl. Phys.", "https://pubs.aip.org/aip/jap/rss"),
    ("Appl. Phys. Rev.", "https://pubs.aip.org/aip/apr/rss"),
]


class JournalRSSFetcher:
    """从多个期刊 RSS 源抓取并过滤论文"""

    def __init__(self, keywords: List[str]):
        self.keywords = keywords

    def _fetch_rss(self, journal_name: str, url: str) -> List[Dict]:
        """获取单个期刊 RSS 源"""
        try:
            resp = requests.get(
                url,
                timeout=30,
                headers={'User-Agent': 'ArxivDailyDigest/1.0'}
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.debug(f"  {journal_name}: RSS 获取失败 ({e})")
            return []

        feed = feedparser.parse(resp.content)
        papers = []

        for entry in feed.entries:
            try:
                title = entry.get('title', '').strip()
                summary = entry.get('summary', '') or entry.get('description', '')
                link = entry.get('link', '')

                # 解析日期
                pub_parsed = entry.get('published_parsed')
                if not pub_parsed:
                    continue
                pub_date = datetime(*pub_parsed[:6], tzinfo=timezone.utc)

                # 提取作者
                authors = []
                author_str = entry.get('author', '')
                if author_str:
                    authors = [a.strip() for a in author_str.split(',')]

                paper = {
                    'id': link,
                    'title': title,
                    'authors': authors,
                    'abstract': summary.strip(),
                    'pdf_url': link,
                    'published': pub_date.strftime('%Y-%m-%d %H:%M'),
                    'primary_category': journal_name,
                    'categories': [journal_name],
                    'arxiv_url': link,
                    'source': journal_name,  # 标记来源期刊
                }
                papers.append(paper)

            except Exception:
                continue

        return papers

    def _matches_keywords(self, paper: Dict) -> bool:
        """检查论文是否匹配关键词"""
        text = f"{paper['title']} {paper['abstract']}".lower()
        for kw in self.keywords:
            kw_parts = kw.strip().lower().split()
            if all(part in text for part in kw_parts):
                return True
        return False

    def fetch_all(self, days_back: int = 1) -> List[Dict]:
        """
        从所有期刊 RSS 源获取近期论文

        Args:
            days_back: 回溯天数
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days_back + 1)  # +1 天缓冲

        all_papers = []
        seen_titles = set()

        successful = 0
        failed = 0
        total_matched = 0

        for journal_name, url in JOURNAL_RSS_FEEDS:
            logger.info(f"获取 {journal_name} RSS...")
            papers = self._fetch_rss(journal_name, url)

            if not papers:
                failed += 1
                continue

            successful += 1
            matched = 0

            for paper in papers:
                # 日期过滤
                pub_str = paper['published']
                try:
                    pub_dt = datetime.strptime(pub_str, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)
                except ValueError:
                    continue

                if pub_dt < start_date or pub_dt > end_date:
                    continue

                # 关键词过滤
                if not self._matches_keywords(paper):
                    continue

                # 标题去重
                title_key = paper['title'].lower().strip()
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)

                all_papers.append(paper)
                matched += 1

            if matched > 0:
                logger.info(f"  {journal_name}: {len(papers)}篇 → 匹配 {matched}篇")
            total_matched += matched

            # 期刊间延迟
            time.sleep(1)

        # 按日期排序
        all_papers.sort(key=lambda p: p['published'], reverse=True)

        logger.info(f"期刊RSS: {successful} 个期刊成功, {failed} 个失败, 共匹配 {total_matched} 篇论文")
        return all_papers
