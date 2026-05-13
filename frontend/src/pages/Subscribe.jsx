import React, { useState } from "react";
import { useDocMeta } from "../lib/useDocMeta";
import { Link } from "react-router-dom";
import api, { formatApiError } from "../lib/api";
import { toast } from "sonner";
import { ArrowRight, Truck, Zap } from "lucide-react";
import { useUIMode } from "../lib/contexts";

const STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"];

export default function Subscribe() {
  useDocMeta({ title: "Subscribe to DropKit — $40/mo monthly hardware kits", description: "One curated open-source electronics project shipped every month. Cancel anytime. Free shipping in the US. $40/month." });
  const { mode } = useUIMode();
  const [form, setForm] = useState({
    email: "", name: "", street1: "", street2: "",
    city: "", state: "CA", zip: "", phone: "",
  });
  const [quote, setQuote] = useState(null);
  const [choice, setChoice] = useState("cheapest");
  const [loading, setLoading] = useState(false);

  if (mode !== "live") {
    return (
      <section className="container py-24 max-w-2xl text-center" data-testid="subscribe-waitlist-block">
        <span className="section-label">// SUBSCRIBE</span>
        <h1 className="mt-3 font-display text-4xl md:text-5xl font-bold">Subscriptions open soon</h1>
        <p className="mt-4 text-cool">
          Subscriptions and gifts go live at launch. Click "Join Waitlist" in the header to be first in line.
        </p>
        <Link to="/" className="btn-primary mt-8 inline-flex">Back home</Link>
      </section>
    );
  }

  const change = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const getQuote = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const r = await api.post("/checkout/quote", {
        email: form.email,
        address: {
          name: form.name || undefined,
          street1: form.street1, street2: form.street2 || undefined,
          city: form.city, state: form.state, zip: form.zip,
          country: "US", phone: form.phone || undefined,
        },
      });
      setQuote(r.data);
      // Auto-scroll to quote
      setTimeout(() => document.getElementById("quote-section")?.scrollIntoView({ behavior: "smooth" }), 100);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const goToCheckout = async () => {
    setLoading(true);
    try {
      const r = await api.post("/checkout/start", {
        quote_id: quote.quote_id, rate_choice: choice,
      });
      // In production this navigates to Shopify checkout; in placeholder mode we toast.
      if (r.data.placeholder_shopify) {
        toast.success("Redirecting to checkout (placeholder Shopify) — would land on the live store with rate + tax pre-applied.");
      }
      window.location.href = r.data.redirect_url;
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="container py-16">
      <span className="section-label">// SUBSCRIBE</span>
      <h1 className="mt-3 font-display text-4xl md:text-6xl font-bold leading-tight">
        One project,<br /><span className="text-circuit">every month.</span>
      </h1>
      <p className="mt-6 text-cool max-w-2xl text-lg">
        Enter your shipping address — we'll show you live rates and tax in real time, then take you to checkout.
      </p>

      <form onSubmit={getQuote} className="mt-12 grid md:grid-cols-2 gap-6 max-w-4xl" data-testid="subscribe-form">
        <Field label="Email" full>
          <input type="email" required name="email" value={form.email} onChange={change}
            placeholder="you@workbench.dev" className="input" data-testid="sub-email" />
        </Field>
        <Field label="Recipient name (optional)">
          <input name="name" value={form.name} onChange={change} className="input" data-testid="sub-name" />
        </Field>
        <Field label="Phone (optional)">
          <input name="phone" value={form.phone} onChange={change} className="input" data-testid="sub-phone" />
        </Field>
        <Field label="Street address" full>
          <input required name="street1" value={form.street1} onChange={change} className="input" data-testid="sub-street1" placeholder="123 Main St" />
        </Field>
        <Field label="Apt / Suite (optional)" full>
          <input name="street2" value={form.street2} onChange={change} className="input" data-testid="sub-street2" />
        </Field>
        <Field label="City">
          <input required name="city" value={form.city} onChange={change} className="input" data-testid="sub-city" />
        </Field>
        <Field label="State">
          <select required name="state" value={form.state} onChange={change} className="input" data-testid="sub-state">
            {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="ZIP">
          <input required name="zip" value={form.zip} onChange={change} className="input" data-testid="sub-zip" placeholder="94103" />
        </Field>
        <div className="md:col-span-2 flex items-center gap-4 mt-2">
          <button type="submit" disabled={loading} className="btn-primary" data-testid="sub-get-quote">
            {loading ? "Calculating…" : "See live rates"} <ArrowRight size={16} strokeWidth={1.5} />
          </button>
          <span className="font-mono text-xs text-cool">
            <span className="text-warm">$40</span>/mo subscription · shipping &amp; tax calculated next
          </span>
        </div>
      </form>

      {quote && (
        <section id="quote-section" className="mt-16 max-w-4xl" data-testid="quote-section">
          <span className="section-label">// PICK A SHIPPING SPEED</span>
          <h2 className="mt-3 font-display text-3xl font-bold">Live rates from {quote.options.cheapest.rate.carrier}</h2>
          <p className="mt-2 text-cool text-sm">
            We default to the cheapest option from your carrier. Upgrade to priority for faster delivery.
          </p>

          <div className="mt-8 grid sm:grid-cols-2 gap-4">
            <RateCard
              type="cheapest" icon={Truck} title="Cheapest"
              rate={quote.options.cheapest} selected={choice === "cheapest"} onSelect={() => setChoice("cheapest")}
            />
            <RateCard
              type="priority" icon={Zap} title="Priority"
              rate={quote.options.priority} selected={choice === "priority"} onSelect={() => setChoice("priority")}
            />
          </div>

          <div className="mt-8 card p-6 grid sm:grid-cols-2 gap-6 items-center">
            <dl className="font-mono text-sm space-y-2 text-cool">
              <Row label="Subscription" value={`$${(quote.subscription_cents / 100).toFixed(2)}`} />
              <Row label="Shipping" value={`$${((quote.options[choice].shipping_cents) / 100).toFixed(2)}`} />
              <Row label="Tax" value={quote.placeholder_tax ? "calculated at checkout" : `$${(quote.options[choice].tax_cents / 100).toFixed(2)}`} />
              <Row label="Total today" value={`$${(quote.options[choice].total_cents / 100).toFixed(2)}`} bold />
            </dl>
            <div className="text-right">
              <button onClick={goToCheckout} disabled={loading} className="btn-primary w-full justify-center" data-testid="sub-checkout-btn">
                {loading ? "…" : "Continue to checkout"} <ArrowRight size={16} strokeWidth={1.5} />
              </button>
              <p className="mt-3 text-xs text-cool">Powered by Shopify Checkout · Stripe-secured</p>
            </div>
          </div>
        </section>
      )}
    </section>
  );
}

function Field({ label, full, children }) {
  return (
    <label className={`block ${full ? "md:col-span-2" : ""}`}>
      <span className="text-xs font-mono uppercase tracking-widest text-cool">{label}</span>
      <div className="mt-2">{children}</div>
    </label>
  );
}

function RateCard({ type, icon: Icon, title, rate, selected, onSelect }) {
  return (
    <button
      type="button" onClick={onSelect}
      data-testid={`rate-${type}`}
      className={`card p-6 text-left transition-all duration-150 ${selected ? "!border-circuit shadow-glow" : ""}`}
    >
      <div className="flex items-center justify-between">
        <Icon size={22} strokeWidth={1.5} className="text-circuit" />
        {selected && <span className="chip chip-green">SELECTED</span>}
      </div>
      <h3 className="mt-4 font-display font-bold text-xl">{title}</h3>
      <p className="mt-1 font-mono text-sm text-cool">{rate.rate.carrier} · {rate.rate.service}</p>
      <p className="mt-3 font-display font-bold text-2xl">${(rate.shipping_cents / 100).toFixed(2)}</p>
      <p className="font-mono text-xs text-cool mt-1">
        {rate.rate.delivery_days ? `${rate.rate.delivery_days} day${rate.rate.delivery_days === 1 ? "" : "s"}` : "estimated"}
      </p>
    </button>
  );
}

function Row({ label, value, bold }) {
  return (
    <div className={`flex items-baseline justify-between ${bold ? "pt-2 mt-2 border-t border-[#30363D]" : ""}`}>
      <dt className="uppercase tracking-widest text-xs">{label}</dt>
      <dd className={`text-warm ${bold ? "font-bold text-lg" : ""}`}>{value}</dd>
    </div>
  );
}
