import arxiv
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import logging
from config import Config

logger = logging.getLogger(__name__)

class ArxivFetcher:
    def __init__(self):
        self.client = arxiv.Client()
        self.keywords = Config.SEARCH_KEYWORDS

    def fetch_recent_papers(self, days_back: int = 1) -> List[Dict]:
        """
        获取最近几天的论文

        Args:
            days_back: 回溯天数，默认为1（获取过去24小时的）
        """
        try:
            # 计算日期范围（使用UTC时间）
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days_back)

            # 构建搜索查询 - 使用 all: 字段搜索（标题+摘要+作者等），
            # 不在API层面做日期过滤，而是获取更多结果后在代码中过滤
            # 因为 submittedDate 过滤可能因格式问题导致0结果
            keyword_terms = []
            for kw in self.keywords:
                kw = kw.strip()
                if ' ' in kw:
                    # 多词短语用引号包围
                    keyword_terms.append(f'all:"{kw}"')
                else:
                    keyword_terms.append(f'all:{kw}')

            keyword_query = " OR ".join(keyword_terms)

            logger.info(f"搜索关键词: {self.keywords}")
            logger.info(f"搜索查询: {keyword_query}")
            logger.info(f"日期范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")

            # 搜索论文（获取足够多的结果，在代码中按日期过滤）
            search = arxiv.Search(
                query=keyword_query,
                max_results=min(Config.MAX_RESULTS * 3, 100),  # 多获取一些以便日期过滤
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )

            papers = []
            for result in self.client.results(search):
                # 在Python中按日期过滤
                # arXiv result.published 返回的是带时区的datetime
                pub_date = result.published
                if pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)

                if pub_date < start_date:
                    logger.debug(f"跳过旧论文: {result.title[:50]}... (发布于 {pub_date.strftime('%Y-%m-%d')})")
                    continue

                paper = {
                    'id': result.get_short_id(),
                    'title': result.title,
                    'authors': [author.name for author in result.authors],
                    'abstract': result.summary,
                    'pdf_url': result.pdf_url,
                    'published': pub_date.strftime('%Y-%m-%d %H:%M'),
                    'primary_category': result.primary_category,
                    'categories': result.categories,
                    'arxiv_url': result.entry_id,
                }
                papers.append(paper)
                logger.info(f"✅ 找到论文: {paper['title'][:80]}... ({pub_date.strftime('%Y-%m-%d')})")

            logger.info(f"共找到 {len(papers)} 篇相关论文 (过去{days_back}天内)")
            return papers

        except Exception as e:
            logger.error(f"获取论文失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def generate_summary(self, paper: Dict) -> str:
        """生成论文的中文摘要"""
        title = paper['title']
        abstract = paper['abstract']

        # 简单总结逻辑（后续可以接入AI）
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
        return text[:max_length].rsplit(' ', 1)[0]  # 在最后一个空格处截断
