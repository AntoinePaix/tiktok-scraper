JAVASCRIPT_BOTTOM_PAGE_CHECKER = """
window.onscroll = function(ev) {
  if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight) {
    return true;
  }
};
"""
JAVASCRIPT_SCROLL_BOTTOM = "([x, y]) => window.scrollBy(x, y)"

COOKIE_BANNER_CSS_SELECTOR = "div.tiktok-cookie-banner"
COOKIE_BANNER_ACCEPT_BUTTON = "button:has-text('Tout accepter')"

ALL_POSTS_CONTAINER_CSS_SELECTOR = "div[data-e2e='user-post-item-list']"
SINGLE_POST_CONTAINER_CSS_SELECTOR = "div[data-e2e='user-post-item']"

MEDIA_URL_START_PATH = "https://v16-webapp.tiktok.com/"

DOCUMENT_JSON_SCRIPT_CSS_SELECTOR = "script#SIGI_STATE"

SCROLL_DELAY = 120
SCROLLING_DELTA_Y = 120

EXCLUDED_RESOURCE_TYPES = ["stylesheet", "image", "media", "font"]
