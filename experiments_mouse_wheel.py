import collections
from playwright.sync_api import sync_playwright
from playwright.sync_api import Page
from playwright.sync_api import Route

from constants import JAVASCRIPT_BOTTOM_PAGE_CHECKER

EXCLUDED_RESOURCE_TYPES = set(["stylesheet", "image", "media", "font"])

def _has_bot_reached_bottom_of_the_page(page: Page) -> bool:
    return page.evaluate(JAVASCRIPT_BOTTOM_PAGE_CHECKER)

def block_unnecessary_resources(route: Route) -> None: 
    if (route.request.resource_type in EXCLUDED_RESOURCE_TYPES):
        route.abort()
    elif route.request.url == "https://mon-va.byteoversea.com/monitor_browser/collect/batch/":
        route.abort()
    else:
        route.continue_()

def scroll_to_bottom(page: Page) -> None:
    positions_deque_size = 200
    last_y_positions = collections.deque(maxlen=positions_deque_size)

    has_reached = False
    while not has_reached:
        page.mouse.wheel(delta_x=0, delta_y=75)
        page.wait_for_load_state("domcontentloaded")

        value = page.evaluate("window.scrollY")
        last_y_positions.append(value)

        if len(last_y_positions) == positions_deque_size and len(set(last_y_positions)) == 1:
            has_reached = True


with sync_playwright() as p:
    browser = p.firefox.launch(headless=False)
    context = browser.new_context(viewport={"width": 1920, "height": 1080})
    page = context.new_page()
    page.route("**/*", block_unnecessary_resources)
    page.goto("https://www.tiktok.com/@emmanuelmacron?lang=fr")
    scroll_to_bottom(page)
    page.pause()
