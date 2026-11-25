"""Extension seams: heavy adapters and optional video-video search remain replaceable."""
from pathlib import Path
from typing import Protocol, Any

class VideoBackend(Protocol):
    def probe(self,path:Path)->dict: ...
    def sample(self,path:Path,times:list[float],short_side:int,gray:bool=False)->list[tuple[float,Any]]: ...

class ImageFeatureExtractor(Protocol):
    def extract(self,images:list[Any])->list[dict]: ...

class QualityReviewer(Protocol):
    """ND1: human-reviewed single-scene / duplicates / logo, independent of class."""
    def review(self,video_id:str,sha256:str)->dict: ...

class VideoSimilarityService(Protocol):
    """ND3 optional endpoint; must use all four features and trace each score.

    Separate from mandatory image endpoint. No fake motion for a still image.
    """
    def search_video(self,video_path:Path)->list[dict]: ...
