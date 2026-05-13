# DropKit — PRD

## Problem statement
Curated open-source electronics project, every month. Microcontroller + components + guide + community vote. US-only MVP.

## Architecture
- **Backend**: FastAPI + Motor (MongoDB). `email_service` (Gmail API) replaces old Klaviyo. EasyPost for shipping. Stripe Tax (off until enabled). Shopify Admin API for subscriptions + fulfillment. JWT cookie auth + role=dev for admin surface.
- **Frontend**: React + Tailwind (DropKit-themed). Routes split into public marketing site + `/apps/makerbox/*` subscriber app + `/dev` admin panel.

## What's implemented (cumulative)

### 2026-05-12 — codebase replacement
- Replaced /app with Toasterfire-come/DropKit; preserved protected env files; deps installed; supervisor restarted.

### 2026-05-12 — production shipping + Q&A pass
- Fixed `create_fulfillment` to query `fulfillmentOrders` first; surfaces `userErrors` as `shopify_skipped_reason`.
- `.env.example` files for backend + frontend (every PLACEHOLDER documented in one place).
- 20+ public endpoints curl-tested; lint clean.

### 2026-05-12 — Gmail switchover + conversion lift
- Klaviyo removed entirely (module, env vars, imports).
- `email_service.py` (`mailer.*`) renders 12 lifecycle templates → sends via dev's connected Gmail. `email_log` collection with `unique_id` idempotency.
- Personalised hero: `?ref=<code>` → `{Referrer first name} thinks you'd love this.`

### 2026-05-13 — SEO overhaul + complete QA
- **23/23 SEO checks pass** on rendered `index.html` (meta, OG, Twitter, canonical, manifest, JSON-LD x3, font preconnects, RSS alternate, sitemap link).
- **Per-page dynamic titles** via `useDocMeta` hook — Home, About, FAQ, Subscribe, BuyGift, ProjectCatalog, ProjectDetail (dynamic from project), Leaderboard, ReplacementRequest.
- **3 JSON-LD blocks** parsed clean: Organization (+5 socials), WebSite (with SearchAction sitelinks), Product (subscription, $40, PreOrder, US).
- **Static SEO assets**: `robots.txt` (custom rules merged with Cloudflare AI-bot policy), `sitemap.xml`, `manifest.json` (PWA-ready), `favicon.svg`.
- **Dynamic backend SEO**: `/api/seo/sitemap.xml` + `/api/seo/feed.xml` (auto-include every project row, lastmod from `updatedAt`).
- **Admin auth UX fix**: `/api/admin/*` accepts either `X-Admin-Token` header (cron) OR dev JWT cookie (UI); 401 enforced.
- **Cycle-close idempotency**: switched to upsert so re-running same month no longer 500s.

### Backend QA results (curl)
- All 75 endpoints respond with correct status codes.
- Auth gates verified on: dev/orders, dev/ops/*, dev/inventory/*, admin/*, account/subscription, votes.
- Address validation returns 422 on bad zip; webhook DLQ persists dispatch errors and returns 200 to Shopify.

### Frontend QA results (Playwright)
- 9 public routes return 200, render correct H1s, no JS console errors (only background 401s when unauth — normal SPA).
- Per-page titles confirmed via `document.title`.

### 2026-05-13 — order-flow + admin-time roadmap (all 15 items)
- **Batch labels + pack slips** PDF generator (`pack_slip.py` + `pypdf` merge). Real `%PDF-1.3` outputs verified.
- **Barcode-scan fulfillment**: QR on every pack slip → `/dev/ops/scan/{id}/fulfill` one-tap.
- **Today's queue** dashboard (8 counters: needs-label, printed, fulfilled, overdue, pending subs/replacements, active subscribers, waitlist 24h).
- **Substitution batch approve** queue.
- **USPS SCAN-form** manifest endpoint (`shipping_service.create_scan_form`).
- **Auto-PO** the moment stock crosses below threshold (in `adjust_stock`).
- **Address validation** on checkout quote → 422 on undeliverable.
- **Webhook DLQ** — `webhook_failures` collection, always 200 to Shopify on errors.
- **Pause/skip/resume** self-service exposed via existing `/api/account/subscription`.
- **Cycle-close automation** generates POs + emails founder summary (template `14_cycle_summary.html`).
- **Cohort retention** dashboard, `users` aggregation by signup-month + status.
- **Replacement queue** — public `/help/replacement` page + `/api/replacements` form + admin approve flow + template `13_replacement_approved.html`.
- **Live shop-floor SSE feed** at `/api/dev/ops/feed`, in-process queue, every ops action publishes.
- **Tax-nexus** monitor — YTD revenue by ship-to state, threshold map for every US state, monthly idempotent founder alert email at 80%.
- New Operations tab in `/dev` surfaces everything.

## Core requirements (static)
- Single active project at a time; isActive flip is atomic via admin route.
- Voting only for `subscriptionStatus=active` users with the right `voteEligibleCycles`.
- Substitution window: ≤10th of month; one per cycle; atomic stock decrement.
- Referral: 3 waitlist refs = priority; 5 paid + self-active = free-month Shopify discount code.
- Idempotent emails: every send gets a unique_id; re-firing same event is a no-op.

## Backlog (next)
### P0
- One-click "send tracking email" from /dev/ops/scan after fulfill (currently auto-sends; expose UI surface).
- Frontend Account.jsx → surface pause/skip/resume buttons inline.

### P1
- Public BOM + cost-transparency page (HN bait, free SEO).
- Embedded YouTube build-logs on ProjectDetail.jsx (`youtubeUrl` field already present).
- Klaviyo flow exports for users who want both (out of scope now).
- Refund webhook → populate `refunds_cents` in cycle close summary.

### P2
- Project changelogs as RSS (`/feed.xml`).
- A/B hero copy (infra in place).
- Auto-place POs based on parsed supplier order-confirmation emails (Gmail watch + filter).
- Pause-instead-of-cancel UX on Account page (Shopify subscriptionContractUpdate wired).

## Test credentials
- Dev: `founder@dropkit.example.com` / `dropkit_qa_password_123` (seeded from backend/.env).
- See `/app/memory/test_credentials.md`.
