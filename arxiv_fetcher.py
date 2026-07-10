"""
ArXiv 论文抓取器 — 使用 RSS 分类源 + 关键词过滤
RSS 源不受 API 限速影响，更稳定可靠
"""
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import logging
import time
from config import Config

logger = logging.getLogger(__name__)

# Rydberg atom 论文最常出现的 arXiv 分类
ARXIV_CATEGORIES = [
    'physics.atom-ph',    # 原子物理 — 主要来源
    'quant-ph',           # 量子物理
    'cond-mat.quant-gas', # 量子气体
    'physics.optics',     # 光学
]


class ArxivFetcher:
    def __init__(self):
        self.keywords = Config.SEARCH_KEYWORDS
        self.max_results = Config.MAX_RESULTS

    def _fetch_category_rss(self, category: str) -> List[Dict]:
        """获取某个分类的最新 RSS 条目"""
        url = f"https://rss.arxiv.org/rss/{category}"
        try:
            resp = requests.get(
                url,
                timeout=30,
                headers={'User-Agent': 'ArxivDailyDigest/1.0'}
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"获取 {category} RSS 失败: {e}")
            return []

        feed = feedparser.parse(resp.content)
        papers = []

        for entry in feed.entries:
            try:
                title = entry.get('title', '')
                summary = entry.get('description', '')
                link = entry.get('link', '')

                # 从 arXiv URL 提取 ID (如 https://arxiv.org/abs/2607.06789)
                arxiv_id = ''
                if '/abs/' in link:
                    arxiv_id = link.split('/abs/')[-1]

                # 提取作者 — feedparser 将 dc:creator 映射为 author
                authors = []
                creator = entry.get('author', '')
                if creator:
                    authors = [a.strip() for a in creator.split(',')]

                # 提取分类标签
                categories = []
                if hasattr(entry, 'tags'):
                    for tag in entry.tags:
                        cat = tag.get('term', '')
                        if cat:
                            categories.append(cat)

                # 解析发布日期 — feedparser 将 RSS <pubDate> 映射为 published_parsed
                pub_parsed = entry.get('published_parsed')
                if pub_parsed:
                    pub_date = datetime(*pub_parsed[:6], tzinfo=timezone.utc)
                else:
                    continue

                # 构造 PDF URL
                pdf_url = ''
                if arxiv_id:
                    pdf_url = link.replace('/abs/', '/pdf/') + '.pdf' if '/abs/' in link else f'https://arxiv.org/pdf/{arxiv_id}.pdf'

                paper = {
                    'id': arxiv_id,
                    'title': title.strip(),
                    'authors': authors,
                    'abstract': summary.strip(),
                    'pdf_url': pdf_url,
                    'published': pub_date.strftime('%Y-%m-%d %H:%M'),
                    'primary_category': categories[0] if categories else category,
                    'categories': categories if categories else [category],
                    'arxiv_url': link,
                }
                papers.append(paper)

            except Exception as e:
                logger.warning(f"解析 RSS 条目失败: {e}")
                continue

        logger.info(f"  {category}: 从 RSS 共获取 {len(papers)} 篇论文")
        return papers

    def _matches_keywords(self, paper: Dict) -> bool:
        """检查论文是否匹配任一关键词"""
        text = f"{paper['title']} {paper['abstract']}".lower()
        for kw in self.keywords:
            # 每个关键词的词都必须出现（支持多词短语如 "Rydberg atom"）
            kw_parts = kw.strip().lower().split()
            if all(part in text for part in kw_parts):
                return True
        return False

    def fetch_recent_papers(self, days_back: int = 1) -> List[Dict]:
        """
        获取最近几天的论文

        Args:
            days_back: 回溯天数，默认为1（获取最近24小时的）
        """
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days_back)

            logger.info(f"搜索关键词: {self.keywords}")
            logger.info(f"日期范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
            logger.info(f"搜索分类: {ARXIV_CATEGORIES}")

            all_papers = []
            seen_ids = set()

            for category in ARXIV_CATEGORIES:
                logger.info(f"获取 {category} RSS 源...")
                papers = self._fetch_category_rss(category)

                # 过滤：关键词 + 日期
                matched = 0
                for paper in papers:
                    pid = paper['id']
                    if pid in seen_ids:
                        continue

                    # 解析日期
                    pub_str = paper['published']
                    try:
                        pub_dt = datetime.strptime(pub_str, '%Y-%m-%d %H:%M')
                        pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue

                    # 日期过滤
                    if pub_dt < start_date or pub_dt > end_date:
                        continue

                    # 关键词过滤
                    if not self._matches_keywords(paper):
                        continue

                    seen_ids.add(pid)
                    all_papers.append(paper)
                    matched += 1

                logger.info(f"{category}: 共获取 {len(papers)} 篇, 关键词匹配 {matched} 篇")

                # 类别间延迟（礼貌爬取）
                time.sleep(2)

            # 按日期排序（最新的在前）
            all_papers.sort(key=lambda p: p['published'], reverse=True)

            # 限制结果数
            all_papers = all_papers[:self.max_results]

            for p in all_papers:
                pcat = p.get('primary_category', '?')
                logger.info(f"✅ 找到论文: [{pcat}] {p['title'][:80]}... ({p['published'][:10]})")

            logger.info(f"共找到 {len(all_papers)} 篇相关论文 (过去{days_back}天内)")

            if len(all_papers) == 0:
                logger.info("提示: 今日可能确实无新论文，或者论文分布在其他分类中")
                logger.info(f"当前搜索分类: {ARXIV_CATEGORIES}")
                logger.info("如需扩展分类，可修改 ARXIV_CATEGORIES 列表")

            return all_papers

        except Exception as e:
            logger.error(f"获取论文失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def generate_summary(self, paper: Dict) -> str:
        """生成论文的中文摘要"""
        title = paper['title']
        abstract = paper['abstract']

        summary_lines = [
            "=" * 60,
            f"📄 标题: {title}",
            "",
            f"👥 作者: {', '.join(paper['authors'][:3])}{'等' if len(paper['authors']) > 3 else ''}",
            f"📅 发布时间: {paper['published']}",
            f"📚 分类: {paper['primary_category']}",
            "",
            "📝 摘要:",
            self._truncate_text(abstract, 800) + ("..." if len(abstract) > 800 else ""),
            "",
            "🔗 链接:",
            f"PDF: {paper['pdf_url']}",
            f"Arxiv: {paper['arxiv_url']}",
            "=" * 60,
            ""
        ]

        return "\n".join(summary_lines)

    def _truncate_text(self, text: str, max_length: int) -> str:
        """截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(' ', 1)[0]
