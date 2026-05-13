import asyncio
import json
import sys
from pathlib import Path

import ezkl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


async def generate_srs():
    artifact_dir = Path("ezkl_artifacts")
    artifact_dir.mkdir(exist_ok=True)

    settings_path = artifact_dir / "settings.json"
    if not settings_path.exists():
        settings_path = Path("settings.json")

    srs_path = artifact_dir / "kzg.srs"

    with open(settings_path, "r") as f:
        settings = json.load(f)
    logrows = settings["run_args"]["logrows"]

    print(f"Generating SRS for logrows {logrows}... This might take a moment to download/compute.")
    await ezkl.get_srs(srs_path=str(srs_path), settings_path=str(settings_path))
    print(f"✓ SRS Generated: {srs_path}")


if __name__ == "__main__":
    asyncio.run(generate_srs())
