import enum

WEBPAGE_URL = "https://www.tiktok.com/"
USER_URL_FORMAT = "https://www.tiktok.com/@{username}"
VIDEO_URL_FORMAT = "https://www.tiktok.com/@{username}/video/{video_id}"

USER_ITEM_LIST_API_URL = "https://www.tiktok.com/api/creator/item_list/"


class TikTokStatus(enum.IntEnum):
    """`statusCode` values found in the page rehydration data.

    Subclasses `IntEnum` so members compare equal to the raw integers TikTok returns in the JSON.
    """

    OK = 0
    USER_NOT_FOUND = 10202
    ITEM_NOT_FOUND = 10204  # statusMsg: "item doesn't exist"
    PRIVATE_ITEM = 10216
    USER_BANNED = 10221
    PRIVATE_ACCOUNT = 10222


DOWNLOAD_DIRECTORY = "downloaded_videos"
MAX_CONCURRENT_DOWNLOADS = 4

COMMENTS_API_URL = "https://www.tiktok.com/api/comment/list/"
REPLIES_API_URL = "https://www.tiktok.com/api/comment/list/reply/"
SEARCH_VIDEOS_API_URL = "https://www.tiktok.com/api/search/general/full/"
SEARCH_USERS_API_URL = "https://www.tiktok.com/api/search/user/full/"
HASHTAG_DETAIL_API_URL = "https://www.tiktok.com/api/challenge/detail/"
HASHTAG_VIDEOS_API_URL = "https://www.tiktok.com/api/challenge/item_list/"
