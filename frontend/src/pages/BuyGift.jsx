import React, { useState } from "react";
import { useDocMeta } from "../lib/useDocMeta";
import { Link } from "react-router-dom";
import { Gift, ArrowRight } from "lucide-react";
import { useUIMode } from "../lib/contexts";

const TIERS = [
  { id: "gift-1", months: 1, price: 40, label: "1 month", blurb: "One drop. A taste of DropKit." },
  { id: "gift-3", months: 3, price: 120, label: "3 months", blurb: "Three projects. The full ride." },
];

export default function BuyGift() {
  useDocMeta({ title: "Gift a DropKit subscription — monthly hardware project boxes", description: "Give 3, 6, or 12 months of curated monthly electronics kits. Recipient gets a single redemption code; no recurring charge." });
  const { mode } = useUIMode();
  const [selected, setSelected] = useState(TIERS[1].id);
  const [email, setEmail] = useState("");

  if (mode !== "live") {
    return (
      <section className="container py-24 max-w-2xl text-center" data-testid="gift-waitlist-block">
        <span className="section-label">// BUY A GIFT</span>
        <h1 className="mt-3 font-display text-4xl md:text-5xl font-bold">Gifts open at launch</h1>
        <p className="mt-4 text-cool">
          Gift subscriptions go live with the rest of the store. Join the waiting list to be first in line.
        </p>
        <Link to="/" className="btn-primary mt-8 inline-flex">Join the waiting list</Link>
      </section>
    );
  }

  const tier = TIERS.find((t) => t.id === selected);
  const shopifyHandle = tier.months === 1 ? "gift-a-maker-box?variant=1mo" : "gift-a-maker-box?variant=3mo";
  // In production this would link to Shopify product variant w/ recipient email passed as line-item property
  const checkoutUrl = `/products/${shopifyHandle}&properties[gift_recipient_email]=${encodeURIComponent(email)}&properties[gift_duration_months]=${tier.months}`;

  return (
    <section className="container py-16 max-w-3xl">
      <span className="section-label">// BUY A GIFT</span>
      <h1 className="mt-3 font-display text-4xl md:text-5xl font-bold flex items-center gap-3">
        <Gift size={36} strokeWidth={1.5} className="text-circuit" /> Gift a maker
      </h1>
      <p className="mt-3 text-cool max-w-xl">
        Give the maker in your life one or three months of DropKit. They'll get a code by email and pick
        their own shipping address at redemption.
      </p>

      <h2 className="mt-12 section-label">// CHOOSE DURATION</h2>
      <div className="mt-4 grid sm:grid-cols-2 gap-4">
        {TIERS.map((t) => (
          <button
            key={t.id}
            onClick={() => setSelected(t.id)}
            data-testid={`gift-tier-${t.months}`}
            className={`card p-6 text-left transition-all duration-150 ${selected === t.id ? "!border-circuit shadow-glow" : ""}`}
          >
            <div className="flex items-baseline gap-2">
              <span className="font-display font-bold text-3xl">${t.price}</span>
              <span className="font-mono text-xs text-cool">+ shipping</span>
            </div>
            <h3 className="mt-2 font-display font-semibold text-lg">{t.label}</h3>
            <p className="mt-1 text-sm text-cool">{t.blurb}</p>
            {selected === t.id && <span className="chip chip-green mt-4 inline-block">SELECTED</span>}
          </button>
        ))}
      </div>

      <h2 className="mt-12 section-label">// RECIPIENT</h2>
      <label className="block mt-4">
        <span className="text-xs font-mono uppercase tracking-widest text-cool">Recipient email</span>
        <input
          type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder="theirbench@email.com" className="input mt-2"
          data-testid="gift-recipient-email"
        />
      </label>
      <p className="mt-2 text-xs text-cool">
        After checkout, your recipient receives a unique gift code by email and redeems it in their own account.
      </p>

      <div className="mt-10 card p-6 flex items-center justify-between flex-wrap gap-4">
        <div>
          <p className="font-mono text-xs text-cool uppercase tracking-widest">Order summary</p>
          <p className="mt-1 font-display text-xl font-bold">
            ${tier.price} · {tier.label}
          </p>
        </div>
        <a
          href={email ? checkoutUrl : "#"}
          onClick={(e) => !email && e.preventDefault()}
          className={`btn-primary ${!email ? "opacity-50 pointer-events-none" : ""}`}
          data-testid="gift-checkout-btn"
        >
          Continue to checkout <ArrowRight size={16} strokeWidth={1.5} />
        </a>
      </div>

      <p className="mt-6 text-xs text-cool">
        Checkout is powered by Shopify · payment via Shopify Payments (Stripe-secured) · 
        already received a code? <Link to="/account" className="text-circuit hover:underline">Redeem it in your account</Link>.
      </p>
    </section>
  );
}
