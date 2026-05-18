"""
Lightweight multi-face tracker for stabilizing recognition across frames.
"""

from dataclasses import dataclass
import time
import uuid
from typing import Dict, List, Optional, Tuple

import numpy as np

import config


@dataclass
class FaceTrack:
    track_id: str
    box: Tuple[int, int, int, int]
    first_seen: float
    last_seen: float
    embedding: Optional[np.ndarray] = None
    last_embedding_at: float = 0.0
    name: Optional[str] = None
    person_id: Optional[str] = None
    confidence: Optional[float] = None
    requires_registration: bool = False
    unknown_since: Optional[float] = None
    prompt_at: Optional[float] = None
    last_meeting_at: Optional[float] = None
    last_meeting: Optional[Dict] = None
    face_image: Optional[np.ndarray] = None


class FaceTracker:
    """Track faces between frames using simple IoU matching."""

    def __init__(
        self,
        iou_threshold: float = config.TRACK_IOU_THRESHOLD,
        max_age_sec: float = config.TRACK_MAX_AGE_SEC,
        embed_refresh_sec: float = config.TRACK_EMBED_REFRESH_SEC,
        prompt_cooldown_sec: float = config.UNKNOWN_PROMPT_COOLDOWN_SEC
    ):
        self.iou_threshold = iou_threshold
        self.max_age_sec = max_age_sec
        self.embed_refresh_sec = embed_refresh_sec
        self.prompt_cooldown_sec = prompt_cooldown_sec
        self._tracks: Dict[str, FaceTrack] = {}

    def update(self, detections: List[Dict]) -> List[FaceTrack]:
        now = time.time()
        updated_tracks: List[FaceTrack] = []
        used_tracks = set()

        for detection in detections:
            box_raw = detection.get('box')
            if not box_raw or len(box_raw) < 4:
                continue
            box = tuple(int(v) for v in box_raw)
            match_id = self._find_best_track(box, used_tracks)

            if match_id is None:
                track_id = str(uuid.uuid4())
                track = FaceTrack(
                    track_id=track_id,
                    box=box,
                    first_seen=now,
                    last_seen=now
                )
                self._tracks[track_id] = track
            else:
                track = self._tracks[match_id]
                track.box = self._smooth_box(track.box, box)
                track.last_seen = now
                used_tracks.add(match_id)

            track.face_image = detection.get('face_image')
            updated_tracks.append(track)

        self._prune(now)
        return updated_tracks

    def should_refresh_embedding(self, track: FaceTrack) -> bool:
        return track.embedding is None or (time.time() - track.last_embedding_at) >= self.embed_refresh_sec

    def should_prompt_registration(self, track: FaceTrack) -> bool:
        now = time.time()
        if track.prompt_at is None:
            return True
        return (now - track.prompt_at) >= self.prompt_cooldown_sec

    def mark_prompted(self, track: FaceTrack) -> None:
        track.prompt_at = time.time()

    def _find_best_track(self, box: Tuple[int, int, int, int], used_tracks: set) -> Optional[str]:
        best_iou = 0.0
        best_id = None
        for track_id, track in self._tracks.items():
            if track_id in used_tracks:
                continue
            iou = self._iou(box, track.box)
            if iou > best_iou:
                best_iou = iou
                best_id = track_id
        if best_iou >= self.iou_threshold:
            return best_id
        return None

    def _prune(self, now: float) -> None:
        stale = [tid for tid, t in self._tracks.items() if (now - t.last_seen) > self.max_age_sec]
        for tid in stale:
            self._tracks.pop(tid, None)

    def _iou(self, box_a: Tuple[int, int, int, int], box_b: Tuple[int, int, int, int]) -> float:
        ax, ay, aw, ah = box_a
        bx, by, bw, bh = box_b
        ax2, ay2 = ax + aw, ay + ah
        bx2, by2 = bx + bw, by + bh

        inter_x1 = max(ax, bx)
        inter_y1 = max(ay, by)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)

        inter_w = max(0, inter_x2 - inter_x1)
        inter_h = max(0, inter_y2 - inter_y1)
        inter_area = inter_w * inter_h

        area_a = aw * ah
        area_b = bw * bh
        union = area_a + area_b - inter_area

        if union <= 0:
            return 0.0
        return inter_area / union

    def _smooth_box(self, prev: Tuple[int, int, int, int], new: Tuple[int, int, int, int], alpha: float = 0.6) -> Tuple[int, int, int, int]:
        px, py, pw, ph = prev
        nx, ny, nw, nh = new
        return (
            int(px * (1 - alpha) + nx * alpha),
            int(py * (1 - alpha) + ny * alpha),
            int(pw * (1 - alpha) + nw * alpha),
            int(ph * (1 - alpha) + nh * alpha)
        )
