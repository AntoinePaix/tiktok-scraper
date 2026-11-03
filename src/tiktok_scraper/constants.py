WEBPAGE_URL = "https://www.tiktok.com/"
USER_URL_FORMAT = "https://www.tiktok.com/@{username}"
VIDEO_URL_FORMAT = "https://www.tiktok.com/@{username}/video/{video_id}"

USER_ITEM_LIST_API_URL = "https://www.tiktok.com/api/creator/item_list/"

UNIVERSAL_DATA_SCRIPT_ID = "__UNIVERSAL_DATA_FOR_REHYDRATION__"

# Browser fingerprint impersonated by curl_cffi (TLS + HTTP/2 + headers), like yt-dlp's `impersonate=True`.
IMPERSONATE_TARGET = "chrome"

# Timestamp (ms) of September 2016: going further back than this means TikTok did not exist yet.
TIKTOK_EPOCH_MS = 1472706000000
ONE_WEEK_MS = 7 * 86_400_000

# TikTok status codes found in the rehydration data.
STATUS_OK = 0
STATUS_USER_NOT_FOUND = 10202
STATUS_USER_BANNED = 10221
STATUS_PRIVATE_ACCOUNT = 10222

DOWNLOAD_DIRECTORY = "downloaded_videos"
MAX_CONCURRENT_DOWNLOADS = 4

COMMENTS_API_URL = "https://www.tiktok.com/api/comment/list/"
REPLIES_API_URL = "https://www.tiktok.com/api/comment/list/reply/"
