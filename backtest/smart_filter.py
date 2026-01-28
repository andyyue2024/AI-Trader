# -*- coding: utf-8 -*-
"""
智能过滤模块
精确检测和过滤未来信息，确保回测的准确性
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FilterConfig:
    """过滤配置"""
    current_datetime: datetime = None
    strict_mode: bool = True  # 严格模式：任何可疑信息都过滤
    filter_news: bool = True
    filter_financials: bool = True
    filter_analyst: bool = True
    filter_social: bool = True
    log_filtered: bool = True  # 记录被过滤的内容

    def __post_init__(self):
        if self.current_datetime is None:
            self.current_datetime = datetime.now()


@dataclass
class FilterResult:
    """过滤结果"""
    original_content: str
    filtered_content: str
    is_filtered: bool
    filter_reason: str = ""
    detected_future_dates: List[str] = field(default_factory=list)
    confidence: float = 1.0  # 置信度


class DatePatternMatcher:
    """日期模式匹配器"""

    # 常见日期格式正则
    DATE_PATTERNS = [
        r'\d{4}-\d{2}-\d{2}',                    # 2024-01-15
        r'\d{4}/\d{2}/\d{2}',                    # 2024/01/15
        r'\d{2}/\d{2}/\d{4}',                    # 01/15/2024
        r'\d{2}-\d{2}-\d{4}',                    # 01-15-2024
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}',  # January 15, 2024
        r'\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}',     # 15 January 2024
        r'Q[1-4] \d{4}',                         # Q1 2024
        r'FY\d{4}',                              # FY2024
        r'\d{4}年\d{1,2}月\d{1,2}日',            # 2024年1月15日
    ]

    # 相对日期关键词
    FUTURE_KEYWORDS = [
        'will', 'upcoming', 'next week', 'next month', 'next quarter',
        'forecast', 'expected', 'projected', 'anticipated',
        'tomorrow', 'next year', 'in the future',
        '预计', '将会', '预期', '下周', '下月', '明天', '未来'
    ]

    @classmethod
    def extract_dates(cls, text: str) -> List[str]:
        """从文本中提取所有日期"""
        dates = []
        for pattern in cls.DATE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        return dates

    @classmethod
    def parse_date(cls, date_str: str) -> Optional[datetime]:
        """解析日期字符串"""
        formats = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%B %d, %Y",
            "%B %d %Y",
            "%d %B %Y",
            "%Y年%m月%d日"
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue

        # 处理季度格式
        quarter_match = re.match(r'Q([1-4]) (\d{4})', date_str)
        if quarter_match:
            quarter, year = int(quarter_match.group(1)), int(quarter_match.group(2))
            month = (quarter - 1) * 3 + 1
            return datetime(year, month, 1)

        # 处理财年格式
        fy_match = re.match(r'FY(\d{4})', date_str)
        if fy_match:
            year = int(fy_match.group(1))
            return datetime(year, 1, 1)

        return None

    @classmethod
    def contains_future_keywords(cls, text: str) -> List[str]:
        """检测未来关键词"""
        found = []
        text_lower = text.lower()
        for keyword in cls.FUTURE_KEYWORDS:
            if keyword.lower() in text_lower:
                found.append(keyword)
        return found


class SmartFilter:
    """智能过滤器"""

    def __init__(self, config: FilterConfig = None):
        self.config = config or FilterConfig()
        self.filtered_log: List[Dict] = []
        self.date_matcher = DatePatternMatcher()

    def set_current_time(self, dt: datetime):
        """设置当前时间"""
        self.config.current_datetime = dt

    def filter_text(self, text: str, source: str = "unknown") -> FilterResult:
        """过滤文本内容"""
        if not text:
            return FilterResult(text, text, False)

        result = FilterResult(
            original_content=text,
            filtered_content=text,
            is_filtered=False
        )

        # 1. 检测日期
        dates = self.date_matcher.extract_dates(text)
        future_dates = []

        for date_str in dates:
            parsed = self.date_matcher.parse_date(date_str)
            if parsed and parsed > self.config.current_datetime:
                future_dates.append(date_str)

        if future_dates:
            result.detected_future_dates = future_dates
            result.is_filtered = True
            result.filter_reason = f"Contains future dates: {', '.join(future_dates)}"

        # 2. 检测未来关键词
        future_keywords = self.date_matcher.contains_future_keywords(text)
        if future_keywords and self.config.strict_mode:
            result.is_filtered = True
            result.filter_reason += f" Future keywords: {', '.join(future_keywords)}"

        # 3. 过滤处理
        if result.is_filtered:
            result.filtered_content = self._apply_filter(text, future_dates, future_keywords)
            result.confidence = self._calculate_confidence(future_dates, future_keywords)

            if self.config.log_filtered:
                self._log_filtered(result, source)

        return result

    def _apply_filter(
        self,
        text: str,
        future_dates: List[str],
        future_keywords: List[str]
    ) -> str:
        """应用过滤"""
        filtered = text

        # 替换未来日期
        for date_str in future_dates:
            filtered = filtered.replace(date_str, "[DATE_FILTERED]")

        # 标记未来关键词（不完全删除，只是标记）
        for keyword in future_keywords:
            # 使用正则替换以保留大小写
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            filtered = pattern.sub(f"[FUTURE:{keyword}]", filtered)

        return filtered

    def _calculate_confidence(
        self,
        future_dates: List[str],
        future_keywords: List[str]
    ) -> float:
        """计算过滤置信度"""
        confidence = 1.0

        # 每个未来日期降低置信度
        confidence -= len(future_dates) * 0.2

        # 未来关键词降低置信度（较少）
        confidence -= len(future_keywords) * 0.05

        return max(0.1, min(1.0, confidence))

    def _log_filtered(self, result: FilterResult, source: str):
        """记录被过滤的内容"""
        self.filtered_log.append({
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "reason": result.filter_reason,
            "future_dates": result.detected_future_dates,
            "confidence": result.confidence,
            "content_hash": hashlib.md5(result.original_content.encode()).hexdigest()[:8]
        })

    def filter_news(self, news_items: List[Dict]) -> List[Dict]:
        """过滤新闻列表"""
        if not self.config.filter_news:
            return news_items

        filtered = []
        for item in news_items:
            # 检查发布日期
            pub_date_str = item.get("published_at") or item.get("date", "")
            if pub_date_str:
                pub_date = self.date_matcher.parse_date(pub_date_str)
                if pub_date and pub_date > self.config.current_datetime:
                    continue  # 跳过未来发布的新闻

            # 过滤内容
            title = item.get("title", "")
            content = item.get("content", "") or item.get("summary", "")

            title_result = self.filter_text(title, "news_title")
            content_result = self.filter_text(content, "news_content")

            # 如果标题被过滤，跳过整条新闻
            if title_result.is_filtered and title_result.confidence < 0.5:
                continue

            # 更新过滤后的内容
            filtered_item = item.copy()
            filtered_item["title"] = title_result.filtered_content
            filtered_item["content"] = content_result.filtered_content
            filtered_item["_filtered"] = title_result.is_filtered or content_result.is_filtered

            filtered.append(filtered_item)

        logger.info(f"Filtered {len(news_items) - len(filtered)}/{len(news_items)} news items")
        return filtered

    def filter_financial_data(self, financials: Dict) -> Dict:
        """过滤财务数据"""
        if not self.config.filter_financials:
            return financials

        current_date = self.config.current_datetime.date()
        filtered = {}

        for key, value in financials.items():
            # 检查报告日期
            if isinstance(value, dict):
                report_date_str = value.get("report_date") or value.get("date", "")
                if report_date_str:
                    report_date = self.date_matcher.parse_date(report_date_str)
                    if report_date and report_date.date() > current_date:
                        continue  # 跳过未来的财报

            # 检查是否是预测数据
            if any(k in key.lower() for k in ["forecast", "estimate", "projected", "expected"]):
                if self.config.strict_mode:
                    continue

            filtered[key] = value

        return filtered

    def filter_analyst_ratings(self, ratings: List[Dict]) -> List[Dict]:
        """过滤分析师评级"""
        if not self.config.filter_analyst:
            return ratings

        current_date = self.config.current_datetime.date()
        filtered = []

        for rating in ratings:
            rating_date_str = rating.get("date", "")
            if rating_date_str:
                rating_date = self.date_matcher.parse_date(rating_date_str)
                if rating_date and rating_date.date() > current_date:
                    continue

            # 检查目标价是否是未来预测
            if "price_target" in rating:
                # 保留目标价，但标记为历史预测
                rating["_historical_target"] = True

            filtered.append(rating)

        return filtered

    def get_filter_stats(self) -> Dict:
        """获取过滤统计"""
        return {
            "total_filtered": len(self.filtered_log),
            "by_source": self._count_by_source(),
            "common_reasons": self._get_common_reasons()
        }

    def _count_by_source(self) -> Dict[str, int]:
        """按来源统计"""
        counts = {}
        for log in self.filtered_log:
            source = log["source"]
            counts[source] = counts.get(source, 0) + 1
        return counts

    def _get_common_reasons(self, top_n: int = 5) -> List[str]:
        """获取常见过滤原因"""
        reasons = {}
        for log in self.filtered_log:
            reason = log["reason"]
            reasons[reason] = reasons.get(reason, 0) + 1

        sorted_reasons = sorted(reasons.items(), key=lambda x: x[1], reverse=True)
        return [r[0] for r in sorted_reasons[:top_n]]

    def save_log(self, filepath: str):
        """保存过滤日志"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "stats": self.get_filter_stats(),
                "logs": self.filtered_log
            }, f, indent=2, ensure_ascii=False)


class DataIntegrityChecker:
    """数据完整性检查器"""

    def __init__(self, reference_date: datetime):
        self.reference_date = reference_date
        self.issues: List[Dict] = []

    def check_price_data(self, prices: List[Dict], symbol: str) -> bool:
        """检查价格数据完整性"""
        is_valid = True

        for i, record in enumerate(prices):
            # 检查日期顺序
            date_str = record.get("date", "")
            if date_str:
                try:
                    record_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if record_date > self.reference_date:
                        self.issues.append({
                            "type": "future_price",
                            "symbol": symbol,
                            "date": date_str,
                            "index": i
                        })
                        is_valid = False
                except:
                    pass

            # 检查价格合理性
            close = float(record.get("4. close") or record.get("close", 0))
            high = float(record.get("2. high") or record.get("high", 0))
            low = float(record.get("3. low") or record.get("low", 0))

            if close > high or close < low:
                self.issues.append({
                    "type": "price_anomaly",
                    "symbol": symbol,
                    "date": date_str,
                    "details": f"Close ({close}) outside High-Low range ({low}-{high})"
                })
                is_valid = False

        return is_valid

    def get_report(self) -> Dict:
        """获取检查报告"""
        return {
            "total_issues": len(self.issues),
            "issues_by_type": self._count_by_type(),
            "issues": self.issues[:100]  # 最多返回100条
        }

    def _count_by_type(self) -> Dict[str, int]:
        """按类型统计问题"""
        counts = {}
        for issue in self.issues:
            t = issue["type"]
            counts[t] = counts.get(t, 0) + 1
        return counts


if __name__ == "__main__":
    # 测试智能过滤
    config = FilterConfig(
        current_datetime=datetime(2024, 6, 15),
        strict_mode=True
    )

    filter = SmartFilter(config)

    # 测试文本过滤
    test_texts = [
        "AAPL reported strong Q1 2024 earnings on January 15, 2024.",
        "The company expects revenue to grow 20% in Q3 2024.",
        "Analysts forecast price target of $200 by December 2024.",
        "Historical data shows growth since 2020.",
        "预计2024年7月发布新产品。"
    ]

    print("=== Text Filtering Test ===")
    for text in test_texts:
        result = filter.filter_text(text)
        status = "🔴 FILTERED" if result.is_filtered else "🟢 PASSED"
        print(f"{status}: {text[:50]}...")
        if result.is_filtered:
            print(f"   Reason: {result.filter_reason}")

    # 测试新闻过滤
    print("\n=== News Filtering Test ===")
    news = [
        {"title": "AAPL beats Q1 earnings", "date": "2024-01-15", "content": "Strong performance in Q1."},
        {"title": "AAPL to release iPhone 16 in September 2024", "date": "2024-06-10", "content": "Expected launch next month."},
        {"title": "AAPL future outlook for 2025", "date": "2024-08-01", "content": "Analysts predict growth."},
    ]

    filtered_news = filter.filter_news(news)
    print(f"Original: {len(news)}, Filtered: {len(filtered_news)}")

    # 统计
    print("\n=== Filter Stats ===")
    print(json.dumps(filter.get_filter_stats(), indent=2))
