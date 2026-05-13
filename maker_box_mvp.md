# DropKit — MVP Documentation

**Version:** 2.2  
**Status:** Draft  
**Last Updated:** May 2026  
**Target Launch:** 1–2 months from document date

---

## 1. Product Overview

An open-source hardware subscription box service targeting adult makers and intermediate electronics enthusiasts. Each month, subscribers receive a curated project kit — including a microcontroller/development board, all required components, and access to the project's open-source software — shipped directly to their door. The community drives the roadmap by voting each month on a future project, keeping the platform collaborative at its core.

**Brand:** DropKit  
**Price:** $40 + shipping per box  
**Billing:** Monthly, auto-renewing via Shopify Subscriptions (Shopify Payments / Stripe)  
**Shipping:** United States only  
**Fulfillment:** Owner-packed and shipped  
**Target Audience:** Adult makers and intermediate hobbyists  
**Target Launch:** 1–2 months

---

## 2. MVP Goals

The MVP validates three core assumptions before scaling:

1. There is sufficient demand among adult makers to sustain a community-driven subscription.
2. The community voting system creates enough engagement to reduce churn and increase retention.
3. The operational workflow (sourcing → building → shipping) can be executed sustainably at $40 + shipping.

---

## 3. Design System

### 3.1 Brand Personality

Professional, technical, and community-driven. The aesthetic draws from the physical world of makers: raw materials, circuit boards, solder, and the glow of an IDE at midnight. It should feel like a well-built product — not a craft fair or a toy store. Think Adafruit meets Kickstarter.

### 3.2 Color Palette

| Role | Name | Hex | Usage |
|------|------|-----|-------|
| **Primary** | Circuit Orange | `#E8510A` | CTAs, active states, highlights, icons |
| **Secondary** | Solder Tin | `#A8B2B8` | Subtext, borders, inactive UI |
| **Background (dark)** | Deep PCB | `#0D1117` | Page background, hero sections |
| **Background (mid)** | Matte Carbon | `#161B22` | Cards, panels, code blocks |
| **Background (light)** | Graphite | `#21262D` | Hover states, input fields |
| **Text primary** | Warm White | `#F0F0EE` | Body copy, headings |
| **Text secondary** | Cool Gray | `#8B949E` | Captions, labels, metadata |
| **Accent green** | Solder Flux | `#39D353` | Success states, Active badges, vote confirmations |
| **Accent blue** | Trace Blue | `#58A6FF` | Links, info states, code highlights |
| **Danger** | Short Circuit | `#FF4444` | Errors, warnings, destructive actions |

The overall palette is **dark-first** — the primary experience is a dark-mode UI that evokes a lit PCB on a workbench.

### 3.3 Typography

| Role | Font | Weight | Notes |
|------|------|--------|-------|
| **Display / Hero** | Space Grotesk | 700 | Large headings, hero tagline |
| **Body** | Inter | 400 / 500 | Readable at all sizes |
| **Code / Technical** | JetBrains Mono | 400 | Board names, component labels, code snippets |
| **Labels / Badges** | Inter | 600, uppercase, tracked | Difficulty ratings, status chips |

All three are available on Google Fonts and load fast. JetBrains Mono used sparingly adds technical authenticity without feeling gimmicky.

### 3.4 Visual Language & UI Dynamics

**Overall feel:** Dark panels, sharp edges with subtle `2px` border-radius, orange glows on interactive elements. Components feel like they belong on a PCB — grids, traces, and precision.

**Key UI patterns:**

- **CTA glow:** Primary buttons use `box-shadow: 0 0 16px rgba(232, 81, 10, 0.5)` to create an LED-style glow on hover.
- **Circuit trace backgrounds:** Hero and feature sections use a very low-opacity SVG pattern of PCB traces (`opacity: 0.04`) behind solid backgrounds — visible on close inspection, never distracting.
- **Card style:** `background: #161B22`, `border: 1px solid #30363D`, no drop shadows. Hover state elevates the border to `#E8510A` with a `200ms` transition.
- **Badge / chip style:** Difficulty and status chips use monospaced uppercase text with a thin colored left-border (`border-left: 3px solid [accent]`) instead of filled pill backgrounds — reads like a terminal status line.
- **Progress / countdowns:** Vote countdown and billing cycle use a segmented horizontal indicator styled like a PCB trace filling in, not a generic progress bar.
- **Iconography:** Line icons only (Lucide or Phosphor), `1.5px` stroke, never filled. Technical subject icons (chip, soldering iron, breadboard) for feature sections.
- **Transitions:** `150ms ease-out` for hovers; `300ms ease-in-out` for panels and drawers. Nothing bouncy — precise and snappy.
- **Grid:** 12-column, max content width `1280px`, gutters `24px`. Feature sections alternate left/right layouts with a vertical circuit-trace SVG divider between columns.

### 3.5 Shopify Theme Implementation Notes

- Base theme: **Dawn** (Shopify's fastest, most customizable free theme).
- Override Dawn's accent color and border-radius with the design tokens above via CSS custom properties in `base.css` and `theme.liquid`.
- Custom sections (voting, project catalog, countdown) built as **Shopify Theme App Extensions** — they render inside the Shopify theme with no iframes and full access to theme CSS variables.

---

## 4. Core Features

### 4.1 Home Page

The public-facing landing page communicates the value proposition and drives subscription conversions.

**Sections (in order):**

1. **Pre-launch / Waitlist Hero** *(active before store goes live)* — Replaces the standard hero during the waitlist phase. Same dark circuit-trace background. Tagline, "Launching soon" badge, short pitch, and a single email capture field ("Get early access"). Powered by a Klaviyo embedded form. CTA switches to "Subscribe Now" once the store goes live.
2. **Hero** *(post-launch)* — Full-width dark section with circuit-trace SVG background. Tagline, one-line description, price callout (`$40/mo + shipping`), and a glowing orange "Subscribe Now" CTA. Animated SVG illustration of a dev board on the right column.
3. **How It Works** — 3-step horizontal flow: `Vote → Build → Receive`. Each step uses a numbered monospaced chip (orange) connected by a horizontal trace line.
4. **This Month's Project** — Featured card showing the current box: project name, board, difficulty badge, component list preview, GitHub link, and a "View Guide" CTA.
5. **Community Vote** — Active or upcoming vote teaser. Candidate project cards with vote percentage bars (revealed after voting). Countdown to vote close.
6. **Past Projects Gallery** — Horizontally scrollable row of the last 6 project cards: name, board, month/year, and a "Substitute This Month" link.
7. **Open Source Commitment** — GitHub org link, license info (MIT / CC BY-SA), live star/contributor count via GitHub API. Discord CTA: "Join the community on Discord →"
8. **Testimonials** — 2–3 community member quotes (placeholder at launch). Dark cards, italic body, name and US state.
9. **FAQ** — Accordion covering shipping, billing, skill level, substitutions, pause/skip, gifting, cancellation, and component replacement.
10. **Footer** — Klaviyo newsletter signup, social links (GitHub, Discord, Reddit, Instagram), legal links.

---

### 4.2 Subscription & Billing (Shopify-First)

**Core principle:** Use Shopify native features wherever they exist. Only reach for the custom app when Shopify has no equivalent capability.

#### What Shopify Handles Natively

| Feature | Shopify Tool |
|---------|-------------|
| Product listing and checkout | Shopify Storefront + Checkout |
| Recurring billing | Shopify Subscriptions (native selling plans) |
| Payment processing | Shopify Payments (Stripe-powered) |
| Customer accounts | Shopify Customer Accounts |
| Order history | Shopify Orders (in Customer Account) |
| Shipping address management | Shopify Customer Account |
| Payment method management | Shopify Customer Account |
| Failed payment dunning | Shopify built-in retry logic |
| Order confirmation emails | Shopify Email / transactional notifications |
| Cancel subscription | Shopify Customer Account (self-serve) |
| **Pause subscription** | Shopify Subscriptions Admin API (`subscriptionContractUpdate`) |
| **Skip a month** | Shopify Subscriptions Admin API (`subscriptionBillingCycleSkip`) |

#### Native Shopify Subscriptions API for Pause, Skip, and Cancel

All subscription lifecycle management is handled via the **Shopify Subscriptions Admin API** — no third-party app required. The custom app exposes a theme app extension UI inside the Shopify Customer Account that calls the custom app backend, which in turn calls the Shopify Admin API.

**Pause subscription:**
```graphql
mutation {
  subscriptionContractUpdate(
    contractId: $contractId
    input: { status: PAUSED }
  ) {
    contract { id status }
  }
}
```
- Subscriber selects "Pause" in the account portal UI
- Custom app calls `subscriptionContractUpdate` with `status: PAUSED`
- MongoDB User `subscriptionStatus` updated to `"paused"` via `subscription_contracts/update` webhook
- Voting locked while paused

**Skip next month:**
```graphql
mutation {
  subscriptionBillingCycleSkip(
    billingCycleInput: {
      contractId: $contractId
      selector: { index: $nextCycleIndex }
    }
  ) {
    billingCycle { skipped }
  }
}
```
- Subscriber selects "Skip Next Month" in the portal UI
- Custom app calls `subscriptionBillingCycleSkip` for the next upcoming cycle index
- `subscription_billing_cycles/skip` webhook fires → MongoDB marks cycle as skipped → voting locked for that cycle

**Resume from pause:**
```graphql
mutation {
  subscriptionContractUpdate(
    contractId: $contractId
    input: { status: ACTIVE }
  ) {
    contract { id status }
  }
}
```

**Cancel:**
Handled natively by Shopify Customer Account UI — no custom code needed.

**Portal UI (theme app extension):**
The custom app renders a small subscription management block inside the Shopify Customer Account page via a theme app extension. It shows current subscription status, next billing date (queried from Shopify), and action buttons for Pause, Skip, and Resume. All actions POST to the custom app backend which calls the Shopify Admin API.

#### Gift Subscriptions (Shopify + Custom App)

Shopify does not natively support gift subscriptions for recurring products. Implementation:

**Buyer flow:**
1. Navigate to `/products/gift-a-maker-box`
2. Select gift duration (1 month or 3 months) and enter recipient email at checkout
3. Complete Shopify Checkout as a one-time purchase
4. Custom app intercepts `orders/paid` webhook → generates unique gift code → stores Gift document in MongoDB → sends recipient a Klaviyo email

**Recipient flow:**
1. Receives Klaviyo email with gift code and "Claim Your Box" CTA
2. Lands on `/pages/redeem-gift` (custom Shopify page + theme app extension)
3. Creates or logs into Shopify account
4. Enters gift code — custom app validates against MongoDB
5. Custom app calls Shopify Admin API (`subscriptionContractCreate`) with billing deferred by gift duration
6. Recipient is active as a subscriber and vote-eligible

#### Subscription Flow (Standard)

```
1. Visitor clicks "Subscribe Now"
2. Shopify product page — subscription selling plan selected by default
3. Shopify Checkout — payment + US shipping address collected
4. Shopify Subscription Contract created
5. Webhook: orders/paid → Custom App
   → Create Order in MongoDB
   → Upsert User in MongoDB (link shopifyCustomerId)
   → Add cycle to voteEligibleCycles
6. Shopify sends order confirmation email
7. Each subsequent month: Shopify auto-bills → new order → webhook fires
   → MongoDB Order created → vote eligibility renewed
```

#### Webhook Events (Custom App Handles)

| Shopify Webhook Topic | Action |
|-----------------------|--------|
| `orders/paid` | Create Order in MongoDB, unlock voting for cycle |
| `orders/cancelled` | Update order status in MongoDB |
| `customers/create` | Create User document in MongoDB |
| `subscription_contracts/create` | Store contract ID on User |
| `subscription_contracts/update` | Sync status (active / paused / cancelled) |
| `subscription_billing_cycles/skip` | Mark cycle as skipped — no Order created, voting locked for that cycle |

---

### 4.3 Subscriber Self-Service (What Goes Where)

| Action | Where It Lives |
|--------|---------------|
| View order history | Shopify Customer Account |
| Update shipping address | Shopify Customer Account |
| Update payment method | Shopify Customer Account |
| Cancel subscription | Shopify Customer Account (native self-serve) |
| Pause subscription | Custom theme app extension → Shopify Admin API |
| Skip next month | Custom theme app extension → Shopify Admin API |
| Vote on next project | Custom App — `/apps/makerbox/vote` |
| Select substitution | Custom App — `/apps/makerbox/substitute` |
| View project archive | Custom App — `/apps/makerbox/projects` |
| Redeem gift code | `/pages/redeem-gift` |

---

### 4.4 Community Voting System

Each month, the community votes on a project idea for the month **after next**, giving a two-month buffer to source components and develop the software.

**Voting rules:**
- Only subscribers with an active cycle in `voteEligibleCycles` (MongoDB) may vote
- Subscribers who have skipped or paused the current cycle are not vote-eligible that month
- One vote per subscriber per voting period
- Voting window: days 1–7 of each month
- 3–5 candidate projects curated by the team (community submission is post-MVP)
- Top-voted idea wins; team retains editorial veto for feasibility

**Voting UI (theme app extension):**
- Candidate project cards: title, description, board, difficulty badge
- Single-selection vote — card border turns orange on selection; submit button glows
- After voting: live vote percentages revealed with animated trace-fill bars
- "You voted for [Project]" confirmation chip replaces the submit button
- Results announced on the 8th of each month via Klaviyo email and homepage banner
- Winning project pinned as "Coming in [Month+2]" on the homepage

---

### 4.5 Project Structure (What's in the Box)

| Item | Details |
|------|---------|
| Development board | e.g., Arduino Uno R4, ESP32-S3, Raspberry Pi Pico 2 — project-specific |
| All required components | Sensors, modules, passives, breadboard, jumper wires, etc. |
| Software access | GitHub repo link + QR code on insert card |
| Project guide | Printed quick-start card + full PDF guide (hosted on Shopify Files) |
| Open-source license | All project files released under MIT or CC BY-SA |

**Difficulty ratings:**

| Badge | Description |
|-------|-------------|
| `INTERMEDIATE` | Core audience — assumes basic breadboarding and IDE familiarity |
| `ADV. INTERMEDIATE` | Stretch project — more complex integration or custom code |

#### Project Documentation (Multi-Channel)

Each project's documentation is published across three channels simultaneously:

**1. Printed insert (in the box)**
- Quick-start card: pinout diagram, wiring overview, first-run steps
- QR code linking to the full digital guide and GitHub repo

**2. Website (hosted on DropKit)**
- Full step-by-step guide with photos, wiring diagrams, and code walkthroughs
- Hosted as a project detail page at `/apps/makerbox/projects/[slug]`
- Accessible to all visitors (not paywalled) — supports SEO and community sharing
- PDF version downloadable (hosted on Shopify Files)

**3. GitHub**
- Full source code, schematics, and BOM in the DropKit GitHub organization
- One repo per project, MIT or CC BY-SA licensed
- README mirrors the web guide structure
- Issues open for community bug reports and questions

**4. YouTube**
- Video walkthrough published for each project on launch day
- Covers unboxing, wiring, flashing, and a completed demo
- Linked from the website project page and GitHub README
- Serves double duty as marketing content and technical support

#### Component Replacement Policy

DropKit handles damaged or lost components on a **case-by-case basis via email support**.

- Subscribers email support with a description of the issue
- Owner reviews and ships replacement components at their discretion
- No formal SLA at MVP — aim to respond within 48 hours and ship within 5 business days
- Egregious misuse (e.g. repeatedly requesting replacements) may result in a nominal charge
- This policy is documented in the FAQ and Terms of Service

---

### 4.6 Substitution System

Subscribers may swap the current month's kit for any project from the **past 6 months**.

**Rules:**
- Request submitted before the 10th of the month
- One substitution per billing cycle
- Past-project stock is limited — first-come, first-served
- Price remains $40 + shipping regardless of substitution
- Skipped cycles are not eligible for substitution

**UI:** Theme app extension in the subscriber account area. Last 6 projects shown as cards with stock status (`Available` / `Low Stock` / `Sold Out`). On selection, a Substitution document is created in MongoDB, stock count is decremented, and admin is notified. UI locks after the 10th.

---

### 4.7 Gift Subscriptions

**Gift tiers (MVP):**
- 1 month — $40 + shipping
- 3 months — $120 + shipping

Shipping is charged to the gift buyer at the time of purchase based on a standard US flat rate (recipient's address confirmed at redemption; any rate difference absorbed by the business at MVP scale).

See Section 4.2 for full buyer and recipient flows.

---

## 5. User Roles

| Role | Access |
|------|--------|
| Visitor | Home page, project previews, FAQ, subscribe |
| Subscriber (active) | Voting, substitution, project archive, account management |
| Subscriber (paused/skipped) | Account management, project archive — voting locked |
| Gift recipient | Same as active subscriber for gift duration |
| Admin | Shopify Admin + custom panel: votes, projects, inventory, substitutions, gift codes |

---

## 6. Page Map (MVP)

```
Shopify-native:
  /                              → Home page (custom Dawn theme)
  /products/monthly-maker-box    → Subscribe product page
  /products/gift-a-maker-box     → Gift subscription product page
  /pages/redeem-gift             → Gift code redemption
  /account                       → Shopify Customer Account hub
  /account/orders                → Order history
  /pages/faq                     → FAQ (Shopify page with accordion section)
  /policies/terms-of-service     → Terms (Shopify built-in)
  /policies/privacy-policy       → Privacy (Shopify built-in)

Custom App (theme app extensions — render inside Shopify theme):
  /apps/makerbox/vote            → Monthly community vote
  /apps/makerbox/substitute      → Substitution selection
  /apps/makerbox/projects        → Project catalog and archive
  /apps/makerbox/projects/[slug] → Individual project detail page

Backend (not user-facing):
  /api/webhooks/shopify          → Shopify webhook handler (HMAC-verified)
  /api/gifts/redeem              → Gift code validation and subscription creation
```

---

## 7. Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Storefront | Shopify (Dawn theme, customized) | Native checkout, subscriptions, customer accounts |
| Subscriptions | Shopify Subscriptions (native) | Pause, skip, and lifecycle via Shopify Admin API — no third-party app |
| Payment processing | Shopify Payments (Stripe) | Built into Shopify — no separate account needed |
| Custom app | Node.js + Express (Shopify App) | Voting, substitutions, gift codes, webhook handler |
| Custom UI | Shopify Theme App Extensions (Liquid + Alpine.js) | Renders inside theme — no iframe |
| Database | MongoDB Atlas | Votes, substitutions, gift codes, project metadata |
| ODM | Mongoose | Schema modeling and validation |
| Email | Klaviyo (Shopify integration) | Vote results, gift redemption, transactional + marketing |
| Hosting (custom app) | Railway or Fly.io | Always-on server for webhook reliability |
| File storage | Shopify Files | Project PDFs, guides, hero images |
| Version control | GitHub | Open-source project repos and site code |

**Guiding principle:** Shopify owns customers, orders, payments, addresses, and subscription contracts. MongoDB only stores what Shopify cannot: votes, substitutions, gift codes, and project catalog metadata. Never duplicate data Shopify already owns.

---

## 8. Data Models (MongoDB — Custom Data Only)

```javascript
// User — extends Shopify Customer with app-specific fields
{
  _id: ObjectId,
  shopifyCustomerId: String,            // Shopify GID (gid://shopify/Customer/...)
  shopifySubscriptionContractId: String,
  subscriptionStatus: String,           // "active" | "paused" | "cancelled" | "gifted"
  voteEligibleCycles: [String],         // e.g. ["2026-05", "2026-06"]
  createdAt: Date,
  updatedAt: Date
}

// Project — source of truth for the project catalog
{
  _id: ObjectId,
  title: String,
  slug: String,                         // unique, URL-safe
  description: String,
  board: String,                        // e.g. "ESP32-S3", "Arduino Uno R4"
  difficulty: String,                   // "INTERMEDIATE" | "ADV. INTERMEDIATE"
  cycleMonth: Number,
  cycleYear: Number,
  stockCount: Number,                   // past-project kit inventory
  isActive: Boolean,                    // true = current month
  githubUrl: String,
  guideUrl: String,                     // Shopify Files PDF URL
  imageUrl: String,
  createdAt: Date
}

// VoteCycle — one document per monthly vote
{
  _id: ObjectId,
  cycleMonth: Number,                   // the month being voted on
  cycleYear: Number,
  candidateProjectIds: [ObjectId],      // ref: Project[]
  winnerId: ObjectId,                   // ref: Project — set after vote closes
  votingOpenAt: Date,
  votingCloseAt: Date
}

// Vote
{
  _id: ObjectId,
  userId: ObjectId,                     // ref: User
  candidateProjectId: ObjectId,         // ref: Project
  voteCycleId: ObjectId,               // ref: VoteCycle
  createdAt: Date
  // Unique index on { userId, voteCycleId }
}

// Substitution
{
  _id: ObjectId,
  userId: ObjectId,                     // ref: User
  shopifyOrderId: String,
  originalProjectId: ObjectId,          // ref: Project
  substitutedProjectId: ObjectId,       // ref: Project
  cycleMonth: Number,
  cycleYear: Number,
  status: String,                       // "pending" | "fulfilled" | "out_of_stock"
  requestedAt: Date,
  fulfilledAt: Date
}

// Gift
{
  _id: ObjectId,
  code: String,                         // unique, e.g. "MAKER-A3X9-2026"
  buyerShopifyOrderId: String,
  recipientEmail: String,
  durationMonths: Number,               // 1 or 3
  status: String,                       // "pending" | "redeemed" | "expired"
  recipientShopifyCustomerId: String,
  redeemedAt: Date,
  createdAt: Date
}
```

---

## 9. MVP Exclusions (Post-MVP Backlog)

| Feature | Notes |
|---------|-------|
| Community forum | Link to external Discord at launch |
| Community project idea submission | Team curates MVP vote candidates |
| Multi-tier plans | Single price point at launch |
| Mobile app | Responsive web covers MVP |
| Referral / affiliate program | Post-launch growth lever |
| International shipping | US only at launch |
| Digital-only subscription | No-box / software-only tier |
| Annual billing | Monthly only at launch |
| Real-time supplier inventory sync | Manual stock management at MVP scale |

---

## 10. Launch Checklist

### Legal & Compliance
- [ ] Business entity registered (LLC recommended)
- [ ] Terms of Service reviewed and published via Shopify
- [ ] Privacy Policy (CCPA-compliant) published via Shopify
- [ ] Shopify Payments identity verification complete

### Shopify Setup
- [ ] Shopify store created (Basic plan minimum)
- [ ] Shopify Payments enabled with US bank account
- [ ] Dawn theme installed and customized with design tokens
- [ ] "Monthly Maker Box" product created with subscription selling plan ($40/mo)
- [ ] "Gift a Maker Box" product created with 1-month and 3-month variants
- [ ] Shopify Customer Accounts (new) enabled
- [ ] Shopify Subscriptions selling plan configured on the product
- [ ] Pause, skip, and resume mutations tested via Shopify Admin API in development
- [ ] Shipping zones set to US only with calculated rates
- [ ] Klaviyo connected to Shopify

### Custom App
- [ ] Shopify App registered in Partner Dashboard
- [ ] Webhook subscriptions registered with HMAC verification
- [ ] MongoDB Atlas cluster provisioned (M10 minimum for production)
- [ ] All webhook handlers tested end-to-end
- [ ] Voting UI (theme app extension) built and tested
- [ ] Substitution UI built and tested
- [ ] Gift code generation, email, and redemption flow tested end-to-end
- [ ] Custom app deployed to Railway/Fly.io with secrets secured

### Operations
- [ ] First 3 months' projects designed, BOMs finalized, components ordered
- [ ] Shipping partner selected (USPS Priority Mail or ShipStation)
- [ ] Fulfillment SOP documented
- [ ] Admin notification flow working (substitutions, gift redemptions, new orders)

### Marketing
- [ ] Home page copy proofread and reviewed
- [ ] Hero images and project photography complete (dark-theme style)
- [ ] GitHub organization created with first project repo public
- [ ] Discord server created and linked from site
- [ ] Social accounts live (GitHub, Discord, Reddit, Instagram)
- [ ] Pre-launch waitlist collected via Klaviyo form
- [ ] Launch announcement email drafted

---

## 11. Success Metrics (First 90 Days)

| Metric | Target |
|--------|--------|
| Paying subscribers — end of month 1 | 50 |
| Subscriber retention month 1 → 2 | > 70% |
| Vote participation rate | > 50% of active subscribers |
| Substitution usage rate | < 20% |
| Pause/skip usage rate | < 15% (healthy churn reduction signal) |
| Gift redemption rate | > 80% within 30 days of receipt |
| Monthly churn rate | < 10% |
| Support tickets per order | < 5% |

---

*This document is a living spec. Update version number and Last Updated date with each revision.*
