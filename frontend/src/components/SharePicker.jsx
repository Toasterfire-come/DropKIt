import React from "react";
import { toast } from "sonner";
import { buildShareUrl } from "../lib/referral";

/* Inline brand-ish glyphs (SVG paths kept tiny to avoid extra deps).
   When a platform's icon isn't in lucide-react we draw a minimal mark. */
const XIcon = (p) => (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" {...p}>
    <path d="M18.244 2H21l-6.55 7.486L22 22h-6.86l-4.84-6.317L4.6 22H1.84l7-8L1 2h6.93l4.38 5.79L18.244 2Zm-1.2 18h1.92L6.99 4H4.94l12.104 16Z" />
  </svg>
);
const BlueskyIcon = (p) => (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" {...p}>
    <path d="M5.5 4c2.4 1.8 5 5.4 6.5 7.4 1.5-2 4.1-5.6 6.5-7.4 1.6-1.2 4-2.2 4-1V18.4c0 2.4-1.8 3.6-3.6 3.6-1.8 0-4.7-.9-6.9-3.7C9.7 21.1 6.8 22 5 22c-1.8 0-3.5-1.2-3.5-3.6V3c0-1.2 2.4-.2 4 1Z" />
  </svg>
);
const WhatsAppIcon = (p) => (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" {...p}>
    <path d="M20.52 3.48A11.94 11.94 0 0 0 12 0C5.4 0 0 5.4 0 12c0 2.1.55 4.16 1.6 5.98L0 24l6.2-1.62A11.94 11.94 0 0 0 12 24c6.6 0 12-5.4 12-12 0-3.2-1.24-6.21-3.48-8.52ZM12 22.06c-1.86 0-3.66-.5-5.23-1.43l-.38-.22-3.68.96.98-3.6-.24-.38A9.96 9.96 0 1 1 22.06 12 9.96 9.96 0 0 1 12 22.06Zm5.42-7.43c-.3-.15-1.77-.87-2.04-.97-.28-.1-.48-.15-.68.15-.2.3-.78.97-.96 1.17-.17.2-.35.22-.65.07-.3-.15-1.25-.46-2.39-1.47-.88-.78-1.48-1.74-1.65-2.04-.17-.3 0-.46.13-.61.13-.13.3-.35.45-.52.15-.17.2-.3.3-.5.1-.2.05-.37-.02-.52-.07-.15-.68-1.64-.93-2.25-.24-.58-.49-.5-.68-.51l-.58-.01a1.1 1.1 0 0 0-.8.37c-.28.3-1.07 1.05-1.07 2.55s1.1 2.95 1.25 3.16c.15.2 2.16 3.3 5.25 4.62.74.32 1.32.51 1.77.65.74.23 1.42.2 1.96.12.6-.09 1.77-.72 2.02-1.42.25-.7.25-1.3.18-1.42-.07-.13-.27-.2-.57-.35Z" />
  </svg>
);
const SmsIcon = (p) => (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}>
    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
  </svg>
);
const MailIcon = (p) => (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}>
    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
    <polyline points="22,6 12,13 2,6" />
  </svg>
);
const ShareIcon = (p) => (
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...p}>
    <circle cx="18" cy="5" r="3" />
    <circle cx="6" cy="12" r="3" />
    <circle cx="18" cy="19" r="3" />
    <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
    <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
  </svg>
);

function buildTrackedUrl(code, src) {
  const base = buildShareUrl(code);
  // Append src param without breaking the existing ?ref=
  const sep = base.includes("?") ? "&" : "?";
  return `${base}${sep}src=${encodeURIComponent(src)}`;
}

function openIntent(href) {
  // Window.open with feature string for desktop; mobile falls back to same-tab.
  const win = window.open(href, "_blank", "noopener,noreferrer,width=600,height=600");
  if (!win) window.location.href = href;
}

export default function SharePicker({ code }) {
  const message = "I just joined the DropKit waitlist — open-source hardware projects, delivered. Skip the line with my link:";

  const targets = [
    {
      id: "x",
      label: "Post on X",
      Icon: XIcon,
      onClick: () => {
        const url = buildTrackedUrl(code, "tw");
        const intent = `https://twitter.com/intent/tweet?text=${encodeURIComponent(message)}&url=${encodeURIComponent(url)}`;
        openIntent(intent);
      },
    },
    {
      id: "bsky",
      label: "Post on Bluesky",
      Icon: BlueskyIcon,
      onClick: () => {
        const url = buildTrackedUrl(code, "bsky");
        const intent = `https://bsky.app/intent/compose?text=${encodeURIComponent(`${message} ${url}`)}`;
        openIntent(intent);
      },
    },
    {
      id: "wa",
      label: "WhatsApp",
      Icon: WhatsAppIcon,
      onClick: () => {
        const url = buildTrackedUrl(code, "wa");
        const intent = `https://wa.me/?text=${encodeURIComponent(`${message} ${url}`)}`;
        openIntent(intent);
      },
    },
    {
      id: "sms",
      label: "SMS",
      Icon: SmsIcon,
      onClick: () => {
        const url = buildTrackedUrl(code, "sms");
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
        const sep = isIOS ? "&" : "?";
        window.location.href = `sms:${sep}body=${encodeURIComponent(`${message} ${url}`)}`;
      },
    },
    {
      id: "email",
      label: "Email",
      Icon: MailIcon,
      onClick: () => {
        const url = buildTrackedUrl(code, "email");
        const body = `${message}\n\n${url}`;
        window.location.href = `mailto:?subject=${encodeURIComponent("Skip the DropKit waitlist with me")}&body=${encodeURIComponent(body)}`;
      },
    },
    {
      id: "native",
      label: "Share…",
      Icon: ShareIcon,
      onClick: async () => {
        const url = buildTrackedUrl(code, "native");
        if (navigator.share) {
          try {
            await navigator.share({ title: "DropKit", text: message, url });
          } catch {
            /* user dismissed */
          }
        } else {
          try {
            await navigator.clipboard.writeText(url);
            toast.success("Link copied — paste it anywhere.");
          } catch {
            toast.error("Can't share automatically here — long-press the link above.");
          }
        }
      },
    },
  ];

  return (
    <div data-testid="share-picker" className="space-y-2">
      <p className="text-xs font-mono uppercase tracking-widest text-cool">SHARE TO</p>
      <div className="flex flex-wrap gap-2">
        {targets.map(({ id, label, Icon, onClick }) => (
          <button
            key={id}
            type="button"
            onClick={onClick}
            className="btn-ghost text-xs py-2 px-3 inline-flex items-center gap-1.5"
            data-testid={`share-${id}`}
            aria-label={label}
            title={label}
          >
            <Icon /> <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
