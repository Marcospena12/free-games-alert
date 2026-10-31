"""Camada de serviços: monitoramento, parsing e regras de negócio."""

from .deals import extract_store_url, is_free_title
from .feed_fetcher import FeedFetchError, FeedFetcher, UrlFeedFetcher
from .monitor import MonitorService
from .rss_parser import RssParseError, parse_feed

__all__ = [
    "FeedFetchError",
    "FeedFetcher",
    "UrlFeedFetcher",
    "MonitorService",
    "RssParseError",
    "extract_store_url",
    "is_free_title",
    "parse_feed",
]