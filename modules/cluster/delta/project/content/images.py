"""The cards' images (new file): PNG files named by comb_id in one folder, indexed once at startup.

`data/images/<comb_id>.png` is a card's picture (2026-10-27, roadmap step 31). In the cards view the map's window
shows it while the card is selected; a card without a file gets a message there instead. The index lists the
folder once (`compose`); a file that matches no card of the course is reported at startup, not refused. The
server's `/card-image/<name>` route serves this folder only.

The names break when cards move in the sources: their ids shift, and a picture would show on another card
without notice. A move of cards needs a rename of the pictures after it.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

IMAGE_SUFFIX = ".png"


@dataclass(frozen=True)
class ImageIndex:
    folder: Path
    files: Dict[str, str]  # comb_id -> file name
    unmatched: Tuple[str, ...]  # file names that match no card

    def file(self, comb_id: Optional[str]) -> Optional[str]:
        """The file name of a card's image, or None."""
        return self.files.get(comb_id) if comb_id else None

    def __len__(self) -> int:
        return len(self.files)


def image_index(folder, comb_ids: Iterable[str]) -> ImageIndex:
    """The PNG files of `folder` (a missing folder has none) whose name is one of the course's comb_ids."""
    folder = Path(folder)
    known = set(comb_ids)
    files: Dict[str, str] = {}
    unmatched = []
    if folder.is_dir():
        for path in sorted(folder.iterdir()):
            if not path.is_file() or path.suffix.lower() != IMAGE_SUFFIX:
                continue
            if path.stem in known:
                files[path.stem] = path.name
            else:
                unmatched.append(path.name)
    return ImageIndex(folder, files, tuple(unmatched))
