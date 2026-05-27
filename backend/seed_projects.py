"""Project seeder — runs at startup.

If no active project exists in the database, seed the canonical first DropKit
project (SafeKeyVault) so the homepage and `/apps/makerbox/projects` always
render real content.

Safe to re-run: looks up by slug and upserts only the immutable fields.
"""
from datetime import datetime, timezone

from db import get_db


SAFEKEYVAULT = {
    "title": "SafeKeyVault",
    "slug": "safekeyvault",
    "tagline": "A local, open-source password vault + hardware authenticator.",
    "description": (
        "SafeKeyVault is a complete alternative to managed password holders. "
        "One-click copy for authenticators (same access model as Microsoft Authenticator, "
        "but with full control), autofill, and hardware-key capabilities — all wrapped in "
        "the same device. Built on the ATECC608A secure element with PIN binding, so a "
        "stolen device is useless without the PIN. Browser-based universal interface means "
        "any device with a browser can use it. Phishing detection alerts you when you "
        "attempt to fill credentials on a look-alike domain (G00gle.com vs google.com). "
        "Includes weak-password indicators and auto-generated secure passwords."
    ),
    "board": "ATECC608A + RP2040",
    "difficulty": "INTERMEDIATE",
    "estimatedTime": "3-4 hours",
    "componentsPreview": [
        "1× custom SafeKeyVault PCB (assembled)",
        "2-part 3D-printed enclosure shell",
        "RP2040 microcontroller",
        "ATECC608A secure element",
        "2× W25Q128JV flash",
        "USB-C connector + ESD protection",
        "2× APA102 LEDs",
        "TTP223 touch sensor",
        "AMS1117-3.3 regulator",
        "16 MHz crystal",
    ],
    "imageUrl": "/images/safekeyvault.png",
    "additionalImages": [
        "https://github.com/user-attachments/assets/a55a89b5-dc85-487a-8d1f-d79f0d79a8d3",
        "https://github.com/user-attachments/assets/b230057c-1807-45fe-a675-53db1be5a1c6",
    ],
    "githubUrl": "https://github.com/Toasterfire-come/SafeKeyVault",
    "guideUrl": "https://github.com/Toasterfire-come/SafeKeyVault#readme",
    "youtubeUrl": "https://www.youtube.com/@DropKit-marketing",
    "license": "MIT / CC BY-SA",
    "stockCount": 100,  # Default to a positive value on first insert
    "isActive": True,
}


async def seed_safekeyvault() -> bool:
    """Idempotent seed: returns True if inserted, False if it already existed."""
    db = get_db()
    now = datetime.now(timezone.utc)
    existing = await db.projects.find_one({"slug": SAFEKEYVAULT["slug"]})

    payload = dict(SAFEKEYVAULT)
    payload["cycleMonth"] = now.month
    payload["cycleYear"] = now.year

    if existing:
        # Only refresh non-stock, non-cycle fields so we don't trample real data.
        # stockCount is intentionally not updated here to preserve it.
        refresh = {
            k: v for k, v in payload.items()
            if k not in ("stockCount", "cycleMonth", "cycleYear", "isActive")
        }
        await db.projects.update_one({"_id": existing["_id"]}, {"$set": refresh})
        return False

    # First-run insert: also flip any other active projects off (only one active at a time).
    await db.projects.update_many({"isActive": True}, {"$set": {"isActive": False}})
    payload["createdAt"] = now
    payload["updatedAt"] = now
    await db.projects.insert_one(payload)
    return True
