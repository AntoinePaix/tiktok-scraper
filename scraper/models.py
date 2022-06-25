from typing import Any
from typing import Dict


class TikTok:
    def __init__(self, tiktok_data: Dict[str, Any]) -> None:
        self._tiktok_data = tiktok_data

    def __str__(self) -> str:
        return f"<{self.__class__.__name__}(id='{self.id}', description='{self.description}')>"

    @property
    def id(self) -> str:
        return self._tiktok_data["id"]

    @property
    def download_addr(self) -> str:
        return self._tiktok_data["video"]["downloadAddr"]

    @property
    def description(self) -> str:
        return self._tiktok_data["desc"]

    @property
    def create_time(self) -> int:
        return self._tiktok_data["createTtime"]

    @property
    def unique_id(self) -> str:
        return self._tiktok_data["author"]["uniqueId"]

    @property
    def video_format(self) -> str:
        return self._tiktok_data["video"]["format"]

    @property
    def video_filename(self) -> str:
        return f"{self.id}.{self.video_format}"
