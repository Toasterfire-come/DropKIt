import React, { useEffect, useState } from "react";
import api, { formatApiError } from "../lib/api";
import { toast } from "sonner";
import { useUIMode, useAuth } from "../lib/contexts";
import { useSearchParams } from "react-router-dom";
import {
  Settings, ToggleLeft, ToggleRight, RefreshCw, Activity,
  Mail, Package, Truck, ExternalLink, Send, Link2, Trash2, Printer, QrCode,
  CheckCircle2,
} from "../lib/icons";
import OperationsTab from "./DevOperationsTab";

const TABS = [
  { id: "controls", label: "Controls", icon: Settings },
  { id: "ops", label: "Operations", icon: Activity },
  { id: "email", label: "Email blast", icon: Mail },
  { id: "orders", label: "Orders", icon: Package },
];

export default function Dev() {
  const { user } = useAuth();
  const [tab, setTab] = useState("controls");
  const [params] = useSearchParams();

  useEffect(() => {
    if (params.get("gmail") === "connected") {
      toast.success("Gmail connected.");
      setTab("email");
    }
  }, [params]);

  return (
    <section className="container py-16">
      <div className="flex items-center gap-3">
        <Settings size={28} strokeWidth={1.5} className="text-circuit" />
        <span className="section-label">// DEV PANEL</span>
      </div>
      <h1 className="mt-3 font-display text-4xl md:text-5xl font-bold">Site controls</h1>
      <p className="mt-3 text-cool max-w-2xl text-sm">
        Signed in as <span className="text-warm font-mono">{user?.email}</span> · role <span className="chip chip-orange !py-0.5">DEV</span>
      </p>

      <nav className="mt-10 flex gap-2 flex-wrap border-b border-[#30363D]">
        {TABS.map((t) => (
          <button
            key={t.id} onClick={() => setTab(t.id)}
            data-testid={`dev-tab-${t.id}`}
            className={`px-4 py-2.5 text-sm font-mono uppercase tracking-widest border-b-2 -mb-px transition-colors inline-flex items-center gap-2 ${
              tab === t.id ? "border-circuit text-circuit" : "border-transparent text-cool hover:text-warm"
            }`}
          >
            <t.icon size={14} strokeWidth={1.5} /> {t.label}
          </button>
        ))}
      </nav>

      <div className="mt-10">
        {tab === "controls" && <ControlsTab />}
        {tab === "ops" && <OperationsTab />}
        {tab === "email" && <EmailTab />}
        {tab === "orders" && <OrdersTab />}
      </div>
    </section>
  );
}

// =================================================== Controls tab
function ControlsTab() {
  const { mode, setRemoteMode } = useUIMode();
  const [stats, setStats] = useState(null);
  const [busy, setBusy] = useState(false);

  const loadStats = async () => {
    try {
      const r = await api.get("/dev/stats");
      setStats(r.data);
    } catch (err) { toast.error(formatApiError(err)); }
  };

  useEffect(() => { loadStats(); }, []);

  const toggle = async () => {
    setBusy(true);
    try {
      const next = mode === "live" ? "waitlist" : "live";
      await setRemoteMode(next);
      toast.success(`UI mode → ${next}`);
      await loadStats();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const isLive = mode === "live";

  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="card p-8" data-testid="dev-ui-mode-card">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <p className="section-label">// UI MODE</p>
            <h2 className="mt-2 font-display font-bold text-2xl">Subscriptions &amp; gifts {isLive ? "ON" : "OFF"}</h2>
            <p className="mt-2 text-sm text-cool max-w-md">
              {isLive
                ? "Hero shows full subscribe CTA · gift CTAs visible · Subscribe button in header."
                : "Waitlist mode — header shows 'Join Waitlist' modal, subscribe and gift CTAs hidden across the site."}
            </p>
          </div>
          <button
            onClick={toggle} disabled={busy}
            data-testid="dev-toggle-ui-mode"
            className={`inline-flex items-center gap-3 px-5 py-3 rounded-sm border transition-colors ${
              isLive ? "border-flux text-flux" : "border-cool text-cool"
            } hover:bg-graphite`}
          >
            {isLive ? <ToggleRight size={28} strokeWidth={1.5} /> : <ToggleLeft size={28} strokeWidth={1.5} />}
            <span className="font-mono text-sm tracking-widest uppercase">{isLive ? "Live" : "Waitlist"}</span>
          </button>
        </div>
      </div>

      <div className="card p-8" data-testid="dev-stats-card">
        <div className="flex items-center justify-between mb-5">
          <p className="section-label inline-flex items-center gap-2"><Activity size={14} strokeWidth={1.5} /> // STATS</p>
          <button onClick={loadStats} className="text-cool hover:text-warm" data-testid="dev-refresh-stats">
            <RefreshCw size={16} strokeWidth={1.5} />
          </button>
        </div>
        {!stats ? <p className="text-cool font-mono">Loading…</p> : (
          <dl className="grid grid-cols-2 gap-y-3 gap-x-6 font-mono text-sm">
            <Stat label="Users" value={stats.users} />
            <Stat label="Waitlist" value={stats.waitlist} />
            <Stat label="Projects" value={stats.projects} />
            <Stat label="Active project" value={stats.active_project} />
            <Stat label="Gifts" value={stats.gifts} />
            <Stat label="Redeemed" value={stats.gifts_redeemed} />
            <Stat label="Substitutions" value={stats.substitutions} />
            <Stat label="Vote cycles" value={stats.vote_cycles} />
          </dl>
        )}
      </div>

      {stats && (
        <div className="card p-8 md:col-span-2" data-testid="dev-subscribers-card">
          <p className="section-label">// SUBSCRIBERS</p>
          <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-6 font-mono text-sm">
            <Stat label="Active now" value={stats.active_subscribers ?? 0} />
            <Stat label="Avg monthly growth" value={`+${stats.avg_monthly_growth ?? 0}`} />
            <Stat label="Projected next month" value={stats.projected_next_month ?? 0} />
          </div>
          <p className="mt-4 text-xs text-cool">
            Projection = active subscribers + average new accounts/month over the last 3 months.
          </p>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="flex items-baseline justify-between">
      <dt className="text-cool uppercase tracking-widest text-xs">{label}</dt>
      <dd className="text-warm text-xl font-bold">{value}</dd>
    </div>
  );
}

// =================================================== Email tab
function EmailTab() {
  const [status, setStatus] = useState(null);
  const [subject, setSubject] = useState("DropKit — we're live");
  const [html, setHtml] = useState("<p>Hi maker,</p><p>DropKit is live. Subscribe at <a href=\"https://dropkit.dev\">dropkit.dev</a>.</p>");
  const [testTo, setTestTo] = useState("");
  const [sending, setSending] = useState(false);
  const [recent, setRecent] = useState([]);

  const load = async () => {
    try {
      const [s, b] = await Promise.all([
        api.get("/dev/gmail/status"),
        api.get("/dev/email/blasts"),
      ]);
      setStatus(s.data);
      setRecent(b.data);
    } catch (err) { toast.error(formatApiError(err)); }
  };

  useEffect(() => { load(); }, []);

  const connect = async () => {
    try {
      const r = await api.post("/dev/gmail/connect");
      window.location.href = r.data.auth_url;
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const disconnect = async () => {
    try {
      await api.post("/dev/gmail/disconnect");
      toast.success("Gmail disconnected.");
      setStatus({ connected: false });
    } catch (err) { toast.error(formatApiError(err)); }
  };

  const send = async (audience, test = false) => {
    setSending(true);
    try {
      const r = await api.post("/dev/email/blast", {
        subject, html, audience,
        test_to: test ? testTo : undefined,
      });
      if (r.data.placeholder) {
        toast.success(`Placeholder mode: ${r.data.skipped} recipient(s) would be emailed.`);
      } else {
        toast.success(`Sent: ${r.data.sent} · failed: ${r.data.failed}`);
      }
      await load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setSending(false); }
  };

  return (
    <div className="grid lg:grid-cols-3 gap-6">
      <div className="card p-6 lg:col-span-1" data-testid="dev-gmail-card">
        <p className="section-label inline-flex items-center gap-2"><Link2 size={14} strokeWidth={1.5} /> // GMAIL</p>
        {!status ? <p className="mt-4 text-cool font-mono">Loading…</p>
          : status.connected ? (
            <>
              <p className="mt-4 text-sm">Connected as</p>
              <p className="font-mono text-warm">{status.email || "—"}</p>
              <span className="chip chip-green mt-4 inline-block">CONNECTED</span>
              <button onClick={disconnect} className="btn-ghost mt-6 text-sm py-2 px-4" data-testid="dev-gmail-disconnect">
                <Trash2 size={14} strokeWidth={1.5} /> Disconnect
              </button>
            </>
          ) : (
            <>
              <p className="mt-4 text-sm text-cool">Connect a Gmail account to send waitlist blasts directly from your inbox.</p>
              <button onClick={connect} className="btn-primary mt-6 text-sm py-2 px-4" data-testid="dev-gmail-connect">
                <Link2 size={14} strokeWidth={1.5} /> Connect Gmail
              </button>
              <p className="mt-3 text-xs text-cool">OAuth via Google · requires Gmail send scope only.</p>
            </>
          )}
      </div>

      <div className="card p-6 lg:col-span-2" data-testid="dev-blast-card">
        <p className="section-label">// COMPOSE BLAST</p>
        <div className="mt-4 space-y-4">
          <label className="block">
            <span className="text-xs font-mono uppercase tracking-widest text-cool">Subject</span>
            <input value={subject} onChange={(e) => setSubject(e.target.value)} className="input mt-2" data-testid="dev-blast-subject" />
          </label>
          <label className="block">
            <span className="text-xs font-mono uppercase tracking-widest text-cool">HTML body</span>
            <textarea value={html} onChange={(e) => setHtml(e.target.value)} rows={8} className="input mt-2 font-mono text-sm" data-testid="dev-blast-html" />
          </label>
          <label className="block">
            <span className="text-xs font-mono uppercase tracking-widest text-cool">Test email (optional)</span>
            <input type="email" value={testTo} onChange={(e) => setTestTo(e.target.value)} placeholder="you@yourdomain.com" className="input mt-2" data-testid="dev-blast-test-to" />
          </label>

          <div className="flex flex-wrap gap-3 pt-2">
            <button onClick={() => send("waitlist", true)} disabled={sending || !testTo} className="btn-ghost text-sm py-2 px-4" data-testid="dev-blast-send-test">
              <Send size={14} strokeWidth={1.5} /> Send test
            </button>
            <button onClick={() => send("waitlist", false)} disabled={sending} className="btn-primary text-sm py-2 px-4" data-testid="dev-blast-send-waitlist">
              <Send size={14} strokeWidth={1.5} /> Send to entire waitlist
            </button>
          </div>
        </div>

        {recent.length > 0 && (
          <div className="mt-8 pt-6 border-t border-[#30363D]">
            <p className="section-label">// RECENT</p>
            <ul className="mt-4 space-y-2 text-sm">
              {recent.map((b) => (
                <li key={b.id} className="flex items-center justify-between font-mono text-xs">
                  <span className="text-warm truncate max-w-[60%]">{b.subject}</span>
                  <span className="text-cool">
                    {new Date(b.created_at).toLocaleString()} · {b.sent}/{b.total} sent
                    {b.placeholder && <span className="ml-2 chip chip-orange !py-0">PLACEHOLDER</span>}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

// =================================================== Orders tab
function OrdersTab() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(null);

  const load = async () => {
    try {
      const r = await api.get("/dev/orders");
      setOrders(r.data);
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  if (active) return <OrderDetail orderId={active} onClose={() => setActive(null)} />;

  return (
    <div>
      <div className="flex items-end justify-between flex-wrap gap-3">
        <p className="section-label inline-flex items-center gap-2"><Package size={14} strokeWidth={1.5} /> // ORDERS ({orders.length})</p>
        <button onClick={load} className="text-cool hover:text-warm" data-testid="dev-orders-refresh">
          <RefreshCw size={16} strokeWidth={1.5} />
        </button>
      </div>

      {loading ? <p className="mt-6 text-cool font-mono">Loading…</p>
        : orders.length === 0 ? (
          <div className="card p-10 mt-6 text-center" data-testid="dev-orders-empty">
            <p className="text-cool">No orders yet. They'll appear here once the Shopify <span className="font-mono">orders/paid</span> webhook fires.</p>
          </div>
        ) : (
          <ul className="mt-6 space-y-2" data-testid="dev-orders-list">
            {orders.map((o) => (
              <li key={o.id}>
                <button
                  onClick={() => setActive(o.id)}
                  data-testid={`dev-order-${o.id}`}
                  className="w-full card p-5 flex items-center justify-between text-left hover:!border-circuit transition-colors"
                >
                  <div>
                    <p className="font-mono text-sm text-warm">{o.shopifyOrderId || o.id}</p>
                    <p className="font-mono text-xs text-cool mt-1">{o.shopifyCustomerId || "—"}</p>
                  </div>
                  <div className="text-right">
                    {o.totalPrice && <p className="font-mono">${o.totalPrice}</p>}
                    <p className="font-mono text-xs text-cool">{o.createdAt && new Date(o.createdAt).toLocaleDateString()}</p>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
    </div>
  );
}

function OrderDetail({ orderId, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [rates, setRates] = useState(null);
  const [label, setLabel] = useState(null);
  const [selectedRate, setSelectedRate] = useState(null);
  const [busy, setBusy] = useState(false);
  const [fulfilling, setFulfilling] = useState(false);
  const [buyerEmail, setBuyerEmail] = useState("");
  const [buyerName, setBuyerName] = useState("");
  const [address, setAddress] = useState({
    name: "", street1: "", city: "", state: "CA", zip: "", country: "US", phone: "",
  });

  const load = async () => {
    try {
      const r = await api.get(`/dev/orders/${orderId}`);
      setData(r.data);
      if (r.data.shipment) setLabel(r.data.shipment);
      if (r.data.user?.email) setBuyerEmail(r.data.user.email);
      if (r.data.user?.name) setBuyerName(r.data.user.name);
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [orderId]);

  const getRates = async () => {
    setBusy(true);
    try {
      const r = await api.post("/dev/shipping/quote", { order_id: orderId, address });
      setRates(r.data);
      setSelectedRate(r.data.cheapest?.id);
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const buy = async () => {
    if (!rates || !selectedRate) return;
    setBusy(true);
    try {
      const r = await api.post("/dev/shipping/labels", {
        order_id: orderId, shipment_id: rates.shipment_id, rate_id: selectedRate,
      });
      setLabel(r.data);
      toast.success("Label purchased.");
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const fulfill = async () => {
    if (!buyerEmail) { toast.error("Buyer email is required."); return; }
    setFulfilling(true);
    try {
      const r = await api.post(`/dev/orders/${orderId}/fulfill`, {
        order_id: orderId, buyer_email: buyerEmail, buyer_name: buyerName || null,
      });
      const emailRes = r.data.email || {};
      if (emailRes.placeholder) {
        toast.success("Order marked fulfilled · email skipped (Gmail in placeholder mode).");
      } else if (emailRes.sent >= 1) {
        toast.success(`Order marked fulfilled · tracking email sent to ${buyerEmail}.`);
      } else if (emailRes.skipped) {
        toast.success("Order marked fulfilled · email skipped (Gmail not connected).");
      } else {
        toast.success("Order marked fulfilled.");
      }
      await load();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setFulfilling(false); }
  };

  if (loading) return <p className="text-cool font-mono">Loading…</p>;
  if (!data) return null;
  const { order, user, current_project } = data;
  const isFulfilled = order.status === "fulfilled";

  return (
    <div data-testid="dev-order-detail">
      <button onClick={onClose} className="text-cool hover:text-warm text-sm inline-flex items-center gap-1 mb-6" data-testid="dev-order-back">
        ← Back to orders
      </button>

      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h2 className="font-display text-3xl font-bold">Order {order.shopifyOrderId || order.id}</h2>
          <p className="mt-2 text-cool font-mono text-sm">{order.shopifyCustomerId}</p>
        </div>
        {isFulfilled && (
          <span className="chip chip-green inline-flex items-center gap-2" data-testid="dev-order-fulfilled-badge">
            <CheckCircle2 size={14} strokeWidth={2} /> FULFILLED
          </span>
        )}
      </div>

      <div className="mt-8 grid lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <p className="section-label">// PRODUCT IN BOX</p>
          {current_project ? (
            <>
              <h3 className="mt-3 font-display font-bold text-xl">{current_project.title}</h3>
              <p className="mt-1 font-mono text-xs text-cool">{current_project.board} · {current_project.difficulty}</p>
              {current_project.componentsPreview?.length > 0 && (
                <ul className="mt-4 font-mono text-xs text-cool space-y-1">
                  {current_project.componentsPreview.map((c) => <li key={c}>{`> ${c}`}</li>)}
                </ul>
              )}
            </>
          ) : <p className="mt-3 text-cool text-sm">No active project — create one via admin API first.</p>}
        </div>

        <div className="card p-6">
          <p className="section-label">// CUSTOMER</p>
          {user ? (
            <>
              <p className="mt-3 font-mono text-warm">{user.email || "—"}</p>
              <p className="mt-1 font-mono text-xs text-cool">{user.shopifyCustomerId}</p>
              <p className="mt-3 text-xs text-cool">Status: <span className="text-warm">{user.subscriptionStatus}</span></p>
            </>
          ) : <p className="mt-3 text-cool text-sm">No linked user record.</p>}
        </div>
      </div>

      {!label ? (
        <div className="mt-8 card p-6" data-testid="dev-order-shipping">
          <p className="section-label inline-flex items-center gap-2"><Truck size={14} strokeWidth={1.5} /> // GENERATE LABEL</p>
          <p className="mt-2 text-sm text-cool">Enter the shipping address (Shopify ship-to). We'll pull the cheapest rate + a priority option from the same carrier.</p>

          <div className="mt-4 grid sm:grid-cols-2 gap-3">
            <input placeholder="Name" value={address.name} onChange={(e) => setAddress({ ...address, name: e.target.value })} className="input" data-testid="dev-ship-name" />
            <input placeholder="Phone" value={address.phone} onChange={(e) => setAddress({ ...address, phone: e.target.value })} className="input" />
            <input placeholder="Street" value={address.street1} onChange={(e) => setAddress({ ...address, street1: e.target.value })} className="input sm:col-span-2" data-testid="dev-ship-street1" />
            <input placeholder="City" value={address.city} onChange={(e) => setAddress({ ...address, city: e.target.value })} className="input" data-testid="dev-ship-city" />
            <input placeholder="State" value={address.state} onChange={(e) => setAddress({ ...address, state: e.target.value })} className="input" />
            <input placeholder="ZIP" value={address.zip} onChange={(e) => setAddress({ ...address, zip: e.target.value })} className="input sm:col-span-2" data-testid="dev-ship-zip" />
          </div>

          <button onClick={getRates} disabled={busy || !address.street1 || !address.zip} className="btn-primary mt-4 text-sm py-2 px-4" data-testid="dev-ship-quote-btn">
            {busy ? "Getting rates…" : "Get rates"}
          </button>

          {rates && (
            <div className="mt-6 space-y-2">
              {[rates.cheapest, rates.priority].filter((r, i, a) => a.findIndex((x) => x.id === r.id) === i).map((r) => (
                <label key={r.id} className={`card p-4 flex items-center justify-between cursor-pointer transition-colors ${selectedRate === r.id ? "!border-circuit" : ""}`} data-testid={`dev-ship-rate-${r.id}`}>
                  <span className="flex items-center gap-3">
                    <input type="radio" checked={selectedRate === r.id} onChange={() => setSelectedRate(r.id)} className="accent-[#E8510A]" />
                    <span>
                      <span className="font-display font-semibold">{r.carrier} {r.service}</span>
                      <span className="font-mono text-xs text-cool ml-2">{r.delivery_days ? `${r.delivery_days}d` : ""}</span>
                    </span>
                  </span>
                  <span className="font-mono">${r.rate.toFixed(2)}</span>
                </label>
              ))}
              <button onClick={buy} disabled={busy || !selectedRate} className="btn-primary mt-2 text-sm py-2 px-4" data-testid="dev-ship-buy-btn">
                {busy ? "Buying…" : "Buy label"}
              </button>
              {rates.placeholder && <p className="text-xs text-cool mt-2">Placeholder mode — rates are simulated; replace EASYPOST_API_KEY to go live.</p>}
            </div>
          )}
        </div>
      ) : (
        <div className="mt-8 card p-6" data-testid="dev-order-label">
          <p className="section-label inline-flex items-center gap-2"><Truck size={14} strokeWidth={1.5} /> // LABEL READY</p>
          <p className="mt-3 font-mono text-warm">{label.carrier} {label.service}</p>
          <p className="mt-1 font-mono text-xs text-cool">{label.tracking_code}</p>
          {label.placeholder && <span className="chip chip-orange mt-3 inline-block">PLACEHOLDER LABEL</span>}

          <div className="mt-6 grid sm:grid-cols-3 gap-3">
            <LabelDownload href={label.label_pdf_url} icon={Printer} title="PDF" subtitle="Normal printer · 4×6 or letter" testId="label-pdf" />
            <LabelDownload href={label.label_zpl_url} icon={Printer} title="ZPL" subtitle="Label printer · Zebra / Rollo" testId="label-zpl" />
            <LabelDownload href={label.label_qr_url} icon={QrCode} title="QR / PNG" subtitle="Scan-to-print" testId="label-qr" />
          </div>
        </div>
      )}

      {label && !isFulfilled && (
        <div className="mt-6 card p-6" data-testid="dev-order-fulfill">
          <p className="section-label inline-flex items-center gap-2"><CheckCircle2 size={14} strokeWidth={1.5} /> // MARK FULFILLED + EMAIL TRACKING</p>
          <p className="mt-2 text-sm text-cool">
            One click marks the order fulfilled, pushes the tracking number to Shopify, and emails
            the buyer "Your DropKit is on the way" via your connected Gmail.
          </p>
          <div className="mt-4 grid sm:grid-cols-2 gap-3">
            <label className="block">
              <span className="text-xs font-mono uppercase tracking-widest text-cool">Buyer email</span>
              <input type="email" required value={buyerEmail} onChange={(e) => setBuyerEmail(e.target.value)} className="input mt-2" data-testid="dev-fulfill-email" />
            </label>
            <label className="block">
              <span className="text-xs font-mono uppercase tracking-widest text-cool">Buyer name (optional)</span>
              <input value={buyerName} onChange={(e) => setBuyerName(e.target.value)} className="input mt-2" data-testid="dev-fulfill-name" />
            </label>
          </div>
          <button onClick={fulfill} disabled={fulfilling || !buyerEmail} className="btn-primary mt-5 text-sm py-2 px-4" data-testid="dev-fulfill-btn">
            <CheckCircle2 size={14} strokeWidth={1.5} /> {fulfilling ? "Fulfilling…" : "Mark fulfilled + email tracking"}
          </button>
        </div>
      )}

      {isFulfilled && (
        <div className="mt-6 card p-6" data-testid="dev-order-fulfilled-summary">
          <p className="section-label inline-flex items-center gap-2 text-flux"><CheckCircle2 size={14} strokeWidth={1.5} /> // FULFILLED</p>
          <p className="mt-3 font-mono text-sm text-warm">{order.tracking_code}</p>
          {order.tracking_url && (
            <a href={order.tracking_url} target="_blank" rel="noreferrer" className="mt-2 text-circuit text-sm hover:underline inline-flex items-center gap-1">
              Track shipment <ExternalLink size={12} strokeWidth={1.5} />
            </a>
          )}
          {order.fulfilledAt && (
            <p className="mt-3 text-xs text-cool font-mono">
              fulfilled_at: {new Date(order.fulfilledAt).toLocaleString()}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function LabelDownload({ href, icon: Icon, title, subtitle, testId }) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className="card p-5 hover:!border-circuit transition-colors block" data-testid={testId}>
      <Icon size={20} strokeWidth={1.5} className="text-circuit" />
      <p className="mt-3 font-display font-bold">{title}</p>
      <p className="mt-1 text-xs text-cool">{subtitle}</p>
      <p className="mt-3 text-xs text-circuit inline-flex items-center gap-1">Download <ExternalLink size={11} strokeWidth={1.5} /></p>
    </a>
  );
}
