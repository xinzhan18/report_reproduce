"""
BrowserManager — Playwright 浏览器管理器

提供网页浏览和 Google 搜索能力，惰性初始化 Playwright Chromium（headless）。
Playwright 不可用时 graceful degradation（browse/search 工具不注册）。
"""

# INPUT:  logging, playwright (可选)
# OUTPUT: BrowserManager 类
# POSITION: Agent层 - 浏览器工具，提供 browse_webpage / google_search 能力

import logging

logger = logging.getLogger("agents.browser_manager")

# 检查 Playwright 是否可用
_PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.info("Playwright not installed. Browser tools will be unavailable.")


def is_playwright_available() -> bool:
    """检查 Playwright 是否可用。"""
    return _PLAYWRIGHT_AVAILABLE


class BrowserManager:
    """Playwright 浏览器管理器（单例模式）。"""

    _instance = None

    @classmethod
    def get_instance(cls) -> "BrowserManager":
        """获取单例实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._playwright = None
        self._browser = None

    def _ensure_browser(self):
        """惰性初始化浏览器。"""
        if self._browser is not None:
            return
        if not _PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not installed")
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        logger.info("Playwright Chromium browser launched (headless)")

    def browse(self, url: str, extract_text: bool = True, max_text_length: int = 10000) -> dict:
        """浏览网页，返回标题和文本内容。

        Args:
            url: 目标 URL
            extract_text: 是否提取纯文本
            max_text_length: 文本最大长度

        Returns:
            {"url": str, "title": str, "text": str}
        """
        self._ensure_browser()
        page = self._browser.new_page()
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            title = page.title()
            text = ""
            if extract_text:
                text = page.inner_text("body")[:max_text_length]
            return {"url": url, "title": title, "text": text}
        except Exception as e:
            logger.warning(f"Browse failed for {url}: {e}")
            return {"url": url, "title": "", "text": f"[ERROR] Failed to load page: {e}"}
        finally:
            page.close()

    def search_google(self, query: str, max_results: int = 5) -> list[dict]:
        """Google 搜索，返回搜索结果列表。

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            [{"title": str, "url": str, "snippet": str}, ...]
        """
        self._ensure_browser()
        page = self._browser.new_page()
        try:
            search_url = f"https://www.google.com/search?q={query}&num={max_results}"
            page.goto(search_url, timeout=30000, wait_until="domcontentloaded")

            results = []
            search_items = page.query_selector_all("div.g")
            for item in search_items[:max_results]:
                try:
                    link_el = item.query_selector("a")
                    title_el = item.query_selector("h3")
                    snippet_el = item.query_selector("div[data-sncf]") or item.query_selector("span.st") or item.query_selector("div.VwiC3b")

                    title = title_el.inner_text() if title_el else ""
                    url = link_el.get_attribute("href") if link_el else ""
                    snippet = snippet_el.inner_text() if snippet_el else ""

                    if title and url:
                        results.append({"title": title, "url": url, "snippet": snippet})
                except Exception:
                    continue

            return results

        except Exception as e:
            logger.warning(f"Google search failed for '{query}': {e}")
            return [{"title": "Search failed", "url": "", "snippet": str(e)}]
        finally:
            page.close()

    def cleanup(self):
        """关闭浏览器和 Playwright。"""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        BrowserManager._instance = None
        logger.info("BrowserManager cleaned up")
