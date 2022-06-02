import argparse

from playwright.sync_api import Page
from playwright.sync_api import Response
from playwright.sync_api import sync_playwright

from constants import ALL_POSTS_CONTAINER_CSS_SELECTOR
from constants import COOKIE_BANNER_ACCEPT_BUTTON
from constants import COOKIE_BANNER_CSS_SELECTOR
from constants import JAVASCRIPT_BOTTOM_PAGE_CHECKER
from constants import JAVASCRIPT_SCROLL_BOTTOM
from constants import MEDIA_URL_START_PATH
from constants import SINGLE_POST_CONTAINER_CSS_SELECTOR

from utils import download_video_background


class TikTokScraper:

    def __init__(self, account: str, headless: bool = True) -> None:
        self.account = account
        self._headless = headless
        self._media_urls = set()
        self._counter = 0
        self._viewport = {"width": 1920, "height": 1080}

    def _generate_tiktok_url(self, lang: str="fr") -> str:
        return f"https://www.tiktok.com/@{self.account}?lang={lang}"

    def _extract_videos_from_current_viewport(self, page: Page):
        posts_container = page.query_selector(ALL_POSTS_CONTAINER_CSS_SELECTOR)
        posts = posts_container.query_selector_all(SINGLE_POST_CONTAINER_CSS_SELECTOR)
        for post in posts:
            post_image = post.query_selector("img")
            box = post_image.bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        self._scroll_to_n_pixels_bottom(page)

    def _has_bot_reached_bottom_of_the_page(self, page: Page) -> bool:
        return page.evaluate(JAVASCRIPT_BOTTOM_PAGE_CHECKER)

    def _scroll_to_n_pixels_bottom(self, page: Page, n: int=750) -> None:
        page.evaluate(JAVASCRIPT_SCROLL_BOTTOM, [0, n])
        page.wait_for_timeout(300)

    def handle_response_media(self, response: Response) -> None:
        if response.url.startswith(MEDIA_URL_START_PATH):
            video_url = response.url
            if video_url not in self._media_urls:
                self._media_urls.add(video_url)
                self._counter += 1
                download_video_background(video_url, self.account)

    def run(self) -> None:
        with sync_playwright() as p:
            browser = p.firefox.launch(headless=self._headless)
            context = browser.new_context(viewport=self._viewport)
            page = context.new_page()
            page.on("response", self.handle_response_media)
            page.goto(self._generate_tiktok_url())
            page.wait_for_selector(COOKIE_BANNER_CSS_SELECTOR)
            page.locator(COOKIE_BANNER_ACCEPT_BUTTON).click()
            page.wait_for_selector(ALL_POSTS_CONTAINER_CSS_SELECTOR)

            while True:
                self._extract_videos_from_current_viewport(page)
                if self._has_bot_reached_bottom_of_the_page(page):

                    # Last crawl (two passes)
                    self._extract_videos_from_current_viewport(page)
                    self._extract_videos_from_current_viewport(page)
                    break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("account", help="Tiktok Account Name", type=str)
    args = parser.parse_args()
    account = args.account.lower()

    scraper = TikTokScraper(account)
    scraper.run()
