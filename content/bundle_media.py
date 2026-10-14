"""Copy licensed images already used by the Android package into app assets.

Sources are the WebP files written by build_media.py. Only public-domain, CC0,
CC BY and CC BY-SA files are in that manifest. The app reads them from
assets/media so a phone does not need the development server.
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "android" / "app" / "src" / "main" / "assets" / "knowledge-package.json"
MEDIA = ROOT / "backend" / "media"
DEST = ROOT / "android" / "app" / "src" / "main" / "assets" / "media"


def main() -> None:
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    paths = {row["image"] for row in package["people"] + package["regions"] if row.get("image")}
    copied = 0
    missing = 0
    for relative in sorted(paths):
        source = MEDIA / relative
        target = DEST / relative
        if not source.exists():
            missing += 1
            continue
        if target.exists() and target.stat().st_size == source.stat().st_size:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
    print(f"media: {len(paths)} referenced, {copied} copied, {missing} missing")


if __name__ == "__main__":
    main()
