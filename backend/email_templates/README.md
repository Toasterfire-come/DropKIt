# DropKit — Email flows (Gmail API)

DropKit sends every lifecycle email through the **dev user's connected
Gmail account** via the official Gmail API. No third-party ESP. No
double-opt-in flow setup. The dev clicks one button in `/dev` →
"Connect Gmail" → grants `gmail.send` scope → from then on every
event-driven email goes out as a real Gmail message from that mailbox.

## Why Gmail

- Single integration. No Klaviyo / SendGrid / Mailchimp account to manage.
- The dev's reply-to is automatically the founder's inbox.
- Gmail's "Sent" folder is the audit trail.
- Free up to 1,000 sends / day per Workspace user (250 for free Gmail).
- Same connection powers `/dev` one-click email blasts, low-stock alerts,
  and tracking-number emails on fulfillment — one OAuth grant, every flow.

---

## Connecting Gmail (one-time, ~30 seconds)

1. Create a Google Cloud project → enable **Gmail API** + **People API**.
2. Configure an **OAuth consent screen** (External, in-house testing scope
   is fine until you have >100 daily senders, which you won't).
3. Create an **OAuth Client → Web application**. Set the authorised
   redirect URI to `https://<your-domain>/api/dev/gmail/callback`.
4. Paste the Client ID + Client Secret into `backend/.env`:

   ```env
   GMAIL_CLIENT_ID=...
   GMAIL_CLIENT_SECRET=...
   GMAIL_REDIRECT_URI=https://<your-domain>/api/dev/gmail/callback
   ```

5. Restart backend. Log in as the dev user, open `/dev`, click
   **Connect Gmail**, grant access.
6. From that moment, every event below sends a real email.

---

## Event → trigger → template map

The 12 lifecycle events live in [`email_service.py`](../email_service.py).
Each fires *fire-and-forget* from the matching route — failures log to
`backend.err.log` but never block the user-facing response.

| # | Event helper | Fires from (backend) | Template file | Idempotency key |
|---|---|---|---|---|
| 1 | `mailer.waitlist_joined` | `POST /api/waitlist` (every new email) | `01_waitlist_joined.html` | `waitlist:<code>` |
| 2 | `mailer.referrer_notify_new_signup` | Same route, when payload has a valid `ref` | `02_referral_joined.html` | `refjoin:<email>:<count>` |
| 3 | `mailer.priority_unlocked` | Same route, when referrer crosses 3 waitlist refs | `03_priority_unlocked.html` | `priority:<code>` |
| 4 | `mailer.free_month_earned` | `POST /webhooks/shopify` orders/paid — referrer hits 5 paid refs and is themselves active | `04_free_month_earned.html` | `reward:<discount_code>` |
| 5 | `mailer.subscription_welcome` | Same webhook — first transition to `active` | `05_subscription_welcome.html` | `welcome:<order_id>` |
| 6 | `mailer.vote_opened` | `POST /api/admin/broadcasts/vote-opened` | `06_vote_opened.html` | `vote_open:<email>:<cycle>` |
| 7 | `mailer.vote_results` | `POST /api/admin/broadcasts/vote-results` | `07_vote_results.html` | `vote_result:<email>:<cycle>` |
| 8 | `mailer.substitution_confirmed` | `POST /api/substitutions` | `08_substitution_confirmed.html` | `sub:<email>:<cycle>` |
| 9 | `mailer.gift_purchased` | `POST /webhooks/shopify` orders/paid — line is a gift product | `09_gift_purchased.html` | `gift_buy:<order_id>` |
| 10 | `mailer.gift_code_issued` | Same webhook — recipient email | `10_gift_code_issued.html` | `gift_code:<code>` |
| 11 | `mailer.gift_redeemed` | `POST /api/gifts/redeem` | `11_gift_redeemed.html` | `gift_redeem:<code>` |
| 12 | `mailer.launch_announcement` | `POST /api/admin/broadcasts/launch-announcement` | `12_launch_announcement.html` | `launch:<email>` |

Every successful send is logged to the MongoDB collection `email_log`
with `unique_id` — re-firing the same event for the same user is a no-op.

---

## Template syntax

The templates were originally written for Klaviyo's `{{ event.* }}` /
`{{ person.* }}` style. `email_service._render()` strips the dotted prefix
and substitutes against the event-properties dict, so `{{ event.first_name }}`
and `{{ first_name }}` both resolve to the same value. You can write new
templates in either style.

Layout is `_layout.html` — every template body slot in there replaces the
`{% block body %}{% endblock %}` marker. Inline-styled, table-based,
email-client safe.

---

## Sender identity

The `From:` header is set to whatever Gmail account the dev connected. If
the founder connects `hello@dropkit.io`, every recipient sees that
address. If you want a different display name, set it in Gmail itself —
Settings → Accounts → "Send mail as".

---

## Local dev (no Gmail connected)

When `GMAIL_CLIENT_ID` is a placeholder OR no token row exists in
`gmail_tokens`, every `mailer.*` call logs to `email_log` with
`result.placeholder = true` and is otherwise a no-op. The rest of the
flow (waitlist save, referral credit, voting) still runs.

---

## Send-volume & deliverability tips

- Workspace accounts: 2,000 sends/day, 100 recipients/message. We send
  one recipient per message, so the soft cap is 2,000 recipients/day.
- For the launch-announcement blast (~1k waitlist signups expected at
  launch), spread sends across two days, or upgrade to Google Workspace
  Business Standard before flipping `LAUNCH_MODE=live`.
- Set up SPF + DKIM for your sending domain before launch. Gmail's
  reputation system penalises new senders with no DNS auth.
- One-click unsubscribe: the layout already includes a `{{ unsubscribe_link }}`
  token. Wire it to a `/api/email/unsubscribe?email=...&token=...` route
  when you need RFC 8058 compliance for >5k/day sends.
