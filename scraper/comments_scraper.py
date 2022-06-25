from __future__ import annotations

import datetime
import shutil
from pprint import pprint
from typing import Dict, Iterator

import requests

from utils import extract_tiktok_id_from_url


class TikTokCommentsScraper:

    def __init__(self, tiktok_id: str) -> None:
        self.tiktok_id = tiktok_id
        self.comments_api_url = "https://www.tiktok.com/api/comment/list/"
        self._cursor = 0
        self.comments_per_request = 50
        self.replies_per_request = 20
        

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:100.0) Gecko/20100101 Firefox/100.0',
            'Accept': '*/*',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'Referer': "https://www.tiktok.com/",
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }

        self.params = {
            'aid': '1988',
            'app_language': 'ja-JP',
            'app_name': 'tiktok_web',
            'aweme_id': self.tiktok_id,
            'browser_language': 'fr',
            'browser_name': 'Mozilla',
            'browser_online': 'true',
            'browser_platform': 'Linux x86_64',
            'browser_version': '5.0 (X11)',
            'channel': 'tiktok_web',
            'cookie_enabled': 'true',
            'count': self.comments_per_request,
            'current_region': 'JP',
            'cursor': str(self._cursor),
            'device_platform': 'web_pc',
            'focus_state': 'true',
            'fromWeb': '1',
            'from_page': 'video',
            'history_len': '4',
            'is_fullscreen': 'false',
            'is_page_visible': 'true',
            'os': 'linux',
            'priority_region': '',
            'referer': '',
            'region': 'FR',
            'screen_height': '1080',
            'screen_width': '1920',
            'tz_name': 'Europe/Paris',
            'webcast_language': 'fr',
        }

    @classmethod
    def from_url(cls, tiktok_url: str) -> TikTokCommentsScraper:
        tiktok_id = extract_tiktok_id_from_url(tiktok_url)
        return cls(tiktok_id)

    def generate_replies_from_comment(self, comment: Dict) -> Iterator[Dict[str, str,]]:
        cursor = 0
        if comment["reply_comment_total"] > 0:
            comment_id = comment["cid"]

            has_replies = True
            while has_replies:

                # Generate new params
                _params = self.params.copy()
                _params["cursor"] = str(cursor)
                _params["count"] = str(self.replies_per_request)
                _params["comment_id"] = comment_id
                _params["item_id"] = self.tiktok_id
                del _params["aweme_id"]

                response = requests.get("https://www.tiktok.com/api/comment/list/reply/",
                                        headers=self.headers,
                                        params=_params)
                response.raise_for_status()
                data = response.json()
                comments = data["comments"]

                if comments is not None:
                    for comment in comments:
                        yield comment

                    # for reply in self.generate_replies_from_comment(comment):
                    #     yield reply

                if data["has_more"] == 1:
                    cursor += self.replies_per_request
                else:
                    has_replies = False

    def _extract_essentials_data_from_comment(self, comment: Dict) -> Dict[str, str]:
        comment_dict = {}
        comment_dict["comment_id"] = comment["cid"]
        comment_dict["text"] = comment["text"]
        comment_dict["create_time"] = datetime.datetime.fromtimestamp(comment["create_time"])
        comment_dict["user_nickname"] = comment["user"]["nickname"]
        comment_dict["comment_language"] = comment["comment_language"]
        comment_dict["likes"] = comment["digg_count"]
        return comment_dict

    def run(self) -> Iterator[Dict]:
        has_more_comments = True
        while has_more_comments:
            response = requests.get(self.comments_api_url,
                                    params=self.params,
                                    headers=self.headers)
            data = response.json()
            base_comments = data.get("comments", None)
            for comment in base_comments:
                yield self._extract_essentials_data_from_comment(comment)

                for reply in self.generate_replies_from_comment(comment):
                    yield self._extract_essentials_data_from_comment(reply)

            if data["has_more"] == 1:
                has_more_comments = True
                cursor = int(self.params["cursor"])
                cursor += self.comments_per_request
                self.params["cursor"] = str(cursor)
            else:
                has_more_comments = False


if __name__ == "__main__":
    screen_width, _ = shutil.get_terminal_size()

    # Alternative "constructor"
    comments_scraper = TikTokCommentsScraper.from_url("https://www.tiktok.com/@emmanuelmacron/video/7019344847035288837")

    # comments_scraper = TikTokCommentsScraper("7095374879951817989")

    counter = 0
    for comment in comments_scraper.run():
        pprint(comment)
        print("=" * screen_width)
        counter += 1

    print(f"Nombre de commentaires scrapés: {counter}")
