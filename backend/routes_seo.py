"""SEO routes — sitemap.xml + RSS feed for the public site.

These live under /api/seo/* so the Kubernetes ingress routes them to the
backend. A reverse-proxy/CDN can rewrite `/sitemap.xml` → `/api/seo/sitemap.xml`
in production for the canonical /sitemap.xml path.
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Response

from config import settings
from db import get_db

router = APIRouter(prefix="/seo")


def _site_url() -> str:
    return (settings.APP_URL or "https://dropkit.marketing").rstrip("/")


@router.get("/sitemap.xml", response_class=Response)
async def sitemap_xml():
    db = get_db()
    site = _site_url()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    static_routes = [
        ("/", "daily", "1.0"),
        ("/about", "monthly", "0.7"),
        ("/subscribe", "weekly", "0.9"),
        ("/gift", "monthly", "0.7"),
        ("/apps/makerbox/projects", "weekly", "0.9"),
        ("/pages/faq", "monthly", "0.6"),
        ("/leaderboard", "daily", "0.5"),
        ("/help/replacement", "monthly", "0.4"),
    ]

    rows = []
    for path, freq, prio in static_routes:
        rows.append(
            f"<url><loc>{site}{path}</loc>"
            f"<lastmod>{now}</lastmod>"
            f"<changefreq>{freq}</changefreq>"
            f"<priority>{prio}</priority></url>"
        )

    # Dynamic project pages
    async for p in db.projects.find({}, {"slug": 1, "updatedAt": 1, "createdAt": 1, "isActive": 1}):
        slug = p.get("slug")
        if not slug:
            continue
        lastmod_dt = p.get("updatedAt") or p.get("createdAt") or datetime.now(timezone.utc)
        lastmod = lastmod_dt.strftime("%Y-%m-%d") if hasattr(lastmod_dt, "strftime") else now
        prio = "0.9" if p.get("isActive") else "0.7"
        rows.append(
            f"<url><loc>{site}/apps/makerbox/projects/{slug}</loc>"
            f"<lastmod>{lastmod}</lastmod>"
            f"<changefreq>monthly</changefreq>"
            f"<priority>{prio}</priority></url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(rows)
        + "</urlset>"
    )
    return Response(content=xml, media_type="application/xml")


@router.get("/feed.xml", response_class=Response)
async def feed_xml():
    """RSS 2.0 feed of the most-recent projects.

    Klaviyo / Mailchimp RSS-driven flows can pull from this for an automated
    weekly digest. Also discoverable via the `<link rel="alternate">` tag in
    index.html.
    """
    db = get_db()
    site = _site_url()

    items = []
    cursor = db.projects.find({}, {"slug": 1, "title": 1, "description": 1, "createdAt": 1, "imageUrl": 1, "isActive": 1}).sort([("cycleYear", -1), ("cycleMonth", -1)]).limit(50)
    async for p in cursor:
        pub_dt = p.get("createdAt") or datetime.now(timezone.utc)
        pub = pub_dt.strftime("%a, %d %b %Y %H:%M:%S +0000") if hasattr(pub_dt, "strftime") else ""
        link = f"{site}/apps/makerbox/projects/{p.get('slug','')}"
        desc = (p.get("description") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        title = (p.get("title") or "Untitled").replace("&", "&amp;")
        items.append(
            f"<item><title>{title}</title>"
            f"<link>{link}</link>"
            f"<guid isPermaLink=\"true\">{link}</guid>"
            f"<pubDate>{pub}</pubDate>"
            f"<description><![CDATA[{desc}]]></description></item>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rss version="2.0">'
        '<channel>'
        f"<title>DropKit · Projects</title>"
        f"<link>{site}</link>"
        f"<description>Open-source hardware projects, delivered monthly.</description>"
        f"<language>en-us</language>"
        + "".join(items)
        + "</channel></rss>"
    )
    return Response(content=xml, media_type="application/rss+xml")
