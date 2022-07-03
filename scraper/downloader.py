import asyncio
import collections
import json
import locale

from typing import Literal

import httpx

from bs4 import BeautifulSoup

import playwright.async_api
from playwright.async_api import async_playwright

from playwright_stealth import stealth_async

from constants import DOCUMENT_JSON_SCRIPT_CSS_SELECTOR
from constants import EXCLUDED_RESOURCE_TYPES
from constants import CHROMIUM_USER_AGENT

from config import HEADERS

from models import TikTok

from utils import download_video


async def block_unnecessary_resources(route: playwright.async_api.Route) -> None:
    """Block some requests to speed the scrolling.

    Args:
        route (playwright.async_api.Route): Playwright async route object.
    """
    if (route.request.resource_type in EXCLUDED_RESOURCE_TYPES):
        await route.abort()
    elif route.request.url == "https://mon-va.byteoversea.com/monitor_browser/collect/batch/":
        await route.abort()
    else:
        await route.continue_()

async def scroll_to_bottom(page: playwright.async_api.Page,
                           load_state_method: Literal["networkidle", "load", "domcontentloaded"] = "domcontentloaded"
                           ) -> None:
    """Method to scroll to the bottom of the page.

    Args:
        page (playwright.async_api.Page): Playwright async page object.
        load_state_method (Literal['networkidle', 'load', 'domcontentloaded'], optional): Loading state methode used for loading page body. Defaults to "networkidle".
    """
    positions_deque_size = 300
    last_y_positions = collections.deque(maxlen=positions_deque_size)

    has_reached = False
    while not has_reached:
        await page.mouse.wheel(delta_x=0, delta_y=75)
        await page.wait_for_load_state(load_state_method)

        value = await page.evaluate("window.scrollY")
        last_y_positions.append(value)

        if len(last_y_positions) == positions_deque_size and len(set(last_y_positions)) == 1:
            has_reached = True


async def handle_response(response: playwright.async_api.Response) -> None:
    """Main callback method to handle and parse responses with tiktoks data.

    Args:
        response (playwright.async_api.Response): Playwright async response object to pass to the function.
    """
    try:
        # Handle document response
        if (response.request.resource_type == "document" and response.status != 302):
            content = await response.text()
            soup = BeautifulSoup(content, "html.parser")
            json_data = soup.select_one(DOCUMENT_JSON_SCRIPT_CSS_SELECTOR).text
            data = json.loads(json_data)

            # Get users infos
            users = data["UserModule"]["users"]
            # Get tiktoks infos
            tiktoks = data["ItemModule"].values()

            # Replace user key with infos of corresponding user for each tiktok.
            for tiktok in tiktoks:
                user = tiktok["author"]
                tiktok["author"] = users[user]

        # Handle xhr response
        elif response.url.startswith("https://www.tiktok.com/api/post/item_list/"):
            json_data = await response.json()
            tiktoks = json_data["itemList"]

        # Process each tiktok here.
        async with httpx.AsyncClient(headers=HEADERS) as client:
            tasks = []
            for tiktok in tiktoks:
                item = TikTok(tiktok)
                tasks.append(asyncio.ensure_future(download_video(client, item.download_addr, item.video_filename, item.unique_id)))
            await asyncio.gather(*tasks)
    except:
        pass

async def scraper(username: str, headless: bool = True):
    """Main method to run the scraper.

    Args:
        username (str): Tiktok username to scrape.
        headless (bool, optional): Hide browser or not. Defaults to True.
    """

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            user_agent=CHROMIUM_USER_AGENT,
            locale=locale.getdefaultlocale()[0]
        )
        page = await context.new_page()
        await stealth_async(page)

        await page.route("**/*", block_unnecessary_resources)
        page.on("response", handle_response)

        await page.goto(f"https://www.tiktok.com/@{username}")
        await scroll_to_bottom(page)

        await context.close()
        await browser.close()

def run(username: str) -> None:
    asyncio.run(scraper(username, headless=True))

if __name__ == "__main__":
    run("charlidamelio")
