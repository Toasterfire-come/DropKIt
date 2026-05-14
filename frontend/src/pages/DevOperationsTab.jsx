import React, { useEffect, useState, useCallback, useRef } from "react";
import api, { formatApiError } from "../lib/api";
import { toast } from "sonner";
import {
  Activity, Truck, Printer, FileText, Users, Wrench, AlertTriangle,
  PlayCircle, Radio, Loader2,
} from "lucide-react";
import OrderDetail from "./DevOrderDetail"; // Assuming OrderDetail is in the same directory

/* ---------------------------------------- Today's queue (Item 4) */
function TodaysQueue() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setBusy(true);
    try { setData((await api.get("/dev/ops/queue/today")).data); }
    catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  if (!data) return <div className="text-cool font-mono text-xs">Loading queue…</div>;

  const cards = [
    { label: "Needs label", value: data.needs_label, alert: data.needs_label > 0, testId: "queue-needs-label" },
    { label: "Labels printed", value: data.labels_printed, testId: "queue-labels-printed" },
    { label: "Fulfilled today", value: data.fulfilled_today, testId: "queue-fulfilled-today" },
    { label: "Overdue (>24h)", value: data.overdue, alert: data.overdue > 0, testId: "queue-overdue" },
    { label: "Pending substitutions", value: data.pending_substitutions, testId: "queue-pending-subs" },
    { label: "Pending replacements", value: data.pending_replacements, alert: data.pending_replacements > 0, testId: "queue-pending-replacements" },
    { label: "Active subscribers", value: data.active_subscribers, testId: "queue-active-subs" },
    { label: "Waitlist · 24h", value: data.waitlist_24h, testId: "queue-waitlist-24h" },
  ];
  return (
    <div data-testid="todays-queue">
      <div className="flex items-center justify-between">
        <div className="section-label">// today</div>
        <button onClick={refresh} disabled={busy} className="btn-ghost text-xs py-1.5 px-3" data-testid="queue-refresh">
          {busy ? <Loader2 size={12} className="animate-spin" /> : "↻"} Refresh
        </button>
      </div>
      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
        {cards.map((c) => (
          <div key={c.label} data-testid={c.testId} className={`p-4 border ${c.alert ? "border-circuit bg-carbon" : "border-[#30363D] bg-carbon"}`}>
            <div className="text-xs font-mono uppercase tracking-widest text-cool">{c.label}</div>
            <div className={`mt-2 font-display text-3xl font-bold ${c.alert ? "text-circuit" : "text-warm"}`}>{c.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------------------------------------- Batch labels (Items 1+2) */
function BatchLabels() {
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState(null);

  const run = async (includeSlip) => {
    setBusy(true);
    try {
      const r = await api.post("/dev/ops/labels/batch", { include_pack_slip: includeSlip });
      setLast(r.data);
      toast.success(`Batch ready: ${r.data.succeeded.length} labels (${(r.data.pdf_size_bytes / 1024).toFixed(1)} KB)`);
      if (r.data.pdf_base64) {
        // Trigger download in browser
        const blob = new Blob([Uint8Array.from(atob(r.data.pdf_base64), (c) => c.charCodeAt(0))], { type: "application/pdf" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = `dropkit-batch-${Date.now()}.pdf`; a.click();
        setTimeout(() => URL.revokeObjectURL(url), 5000);
      }
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="batch-labels-section">
      <div className="section-label">// batch</div>
      <p className="mt-2 text-cool text-sm max-w-xl">
        Generates a single PDF with every unfulfilled order's shipping label, each followed by a pack slip with QR-coded fulfillment shortcut.
      </p>
      <div className="mt-4 flex flex-wrap gap-3">
        <button onClick={() => run(true)} disabled={busy} className="btn-primary inline-flex items-center gap-2" data-testid="batch-with-slip">
          {busy ? <Loader2 size={14} className="animate-spin" /> : <Printer size={14} />} Print labels + pack slips
        </button>
        <button onClick={() => run(false)} disabled={busy} className="btn-ghost inline-flex items-center gap-2" data-testid="batch-labels-only">
          <Truck size={14} /> Labels only
        </button>
      </div>
      {last && (
        <div className="mt-4 p-3 border border-[#30363D] bg-carbon font-mono text-xs text-cool" data-testid="batch-last-result">
          {last.succeeded.length} label(s) · {last.failed.length} failed · {(last.pdf_size_bytes / 1024).toFixed(1)} KB
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------- Replacements (Item 13) */
function Replacements() {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { setItems((await api.get("/dev/ops/replacements")).data); }
    catch (e) { toast.error(formatApiError(e)); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const approve = async (id) => {
    const tracking_code = prompt("Tracking number (or leave blank for PENDING):") || "";
    setBusy(true);
    try {
      await api.post(`/dev/ops/replacements/${id}/approve`, { tracking_code, tracking_carrier: "USPS" });
      toast.success("Approved + customer emailed");
      await load();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="replacements-section">
      <div className="section-label">// replacements queue</div>
      {items.length === 0 ? (
        <div className="mt-4 text-cool font-mono text-xs">No replacement requests.</div>
      ) : (
        <div className="mt-4 space-y-2">
          {items.map((r) => (
            <div key={r.id} data-testid={`replacement-${r.id}`} className="p-4 border border-[#30363D] bg-carbon flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="font-mono text-xs text-cool">{r.email} · {r.order_label || "no order #"}</div>
                <div className="mt-1 font-semibold">{r.component_name}</div>
                <div className="mt-1 text-sm text-cool truncate">{r.description}</div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <span className={`chip text-xs ${r.status === "approved" ? "chip-green" : "chip-orange"}`}>{r.status}</span>
                {r.status === "pending" && (
                  <button onClick={() => approve(r.id)} disabled={busy} className="btn-primary text-xs py-1.5 px-3" data-testid={`replacement-approve-${r.id}`}>Approve + ship</button>
                )}
                {r.tracking_code && (
                  <a href={r.tracking_url} target="_blank" rel="noreferrer" className="text-xs font-mono text-circuit hover:underline">{r.tracking_code}</a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------- Cohorts (Item 12) */
function Cohorts() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    setBusy(true);
    try { setData((await api.get("/dev/ops/cohorts")).data); }
    catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };
  useEffect(() => { refresh(); }, []);

  if (!data) return <div className="text-cool font-mono text-xs">Loading cohorts…</div>;
  return (
    <div data-testid="cohorts-section">
      <div className="flex items-center gap-3">
        <Users size={14} className="text-circuit" />
        <div className="section-label">// cohorts</div>
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-sm font-mono">
          <thead className="text-cool text-xs uppercase tracking-widest">
            <tr><th className="text-left py-2 px-3">Cohort</th><th className="text-right py-2 px-3">Active</th><th className="text-right py-2 px-3">Paused</th><th className="text-right py-2 px-3">Cancelled</th><th className="text-right py-2 px-3">Inactive</th><th className="text-right py-2 px-3">Total</th><th className="text-right py-2 px-3">Retention</th></tr>
          </thead>
          <tbody>
            {(data.cohorts || []).map((c) => (
              <tr key={c.cohort} className="border-t border-[#30363D]" data-testid={`cohort-${c.cohort}`}>
                <td className="py-2 px-3">{c.cohort}</td>
                <td className="text-right py-2 px-3 text-flux">{c.active}</td>
                <td className="text-right py-2 px-3">{c.paused}</td>
                <td className="text-right py-2 px-3">{c.cancelled}</td>
                <td className="text-right py-2 px-3 text-cool">{c.inactive}</td>
                <td className="text-right py-2 px-3">{c.total}</td>
                <td className={`text-right py-2 px-3 font-bold ${c.retention_pct >= 80 ? "text-circuit" : ""}`}>{c.retention_pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button onClick={refresh} disabled={busy} className="mt-3 btn-ghost text-xs py-1.5 px-3" data-testid="cohorts-refresh">
        {busy ? <Loader2 size={12} className="animate-spin" /> : "↻"} Refresh
      </button>
    </div>
  );
}

/* ---------------------------------------- Tax nexus (Item 15) */
function TaxNexus() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    setBusy(true);
    try { setData((await api.get("/dev/ops/tax-nexus")).data); }
    catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };
  useEffect(() => { refresh(); }, []);

  if (!data) return <div className="text-cool font-mono text-xs">Loading tax nexus…</div>;
  return (
    <div data-testid="tax-nexus-section">
      <div className="flex items-center gap-3">
        <AlertTriangle size={14} className="text-circuit" />
        <div className="section-label">// sales-tax nexus · {data.year}</div>
      </div>
      {(data.rows || []).length === 0 ? (
        <p className="mt-2 text-cool font-mono text-xs">No nexus states crossed this year.</p>
      ) : (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm font-mono">
            <thead className="text-cool text-xs uppercase tracking-widest">
              <tr><th className="text-left py-2 px-3">State</th><th className="text-right py-2 px-3">YTD revenue</th><th className="text-right py-2 px-3">Orders</th><th className="text-right py-2 px-3">% threshold</th></tr>
            </thead>
            <tbody>
              {data.rows.map((r) => (
                <tr key={r.state} className="border-t border-[#30363D]">
                  <td className="py-2 px-3">{r.state}</td>
                  <td className="text-right py-2 px-3">${(r.revenue_cents / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  <td className="text-right py-2 px-3">{r.orders}</td>
                  <td className={`text-right py-2 px-3 ${r.pct_of_threshold >= 80 ? "text-circuit font-bold" : ""}`}>{r.pct_of_threshold}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <button onClick={refresh} disabled={busy} className="mt-3 btn-ghost text-xs py-1.5 px-3" data-testid="tax-nexus-refresh">
        {busy ? "Checking…" : "Re-check + alert if crossing"}
      </button>
    </div>
  );
}

/* ---------------------------------------- Cycle close (Item 11) */
function CycleClose() {
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState(null);
  const close = async () => {
    if (!window.confirm("Close the current cycle? This generates POs for low stock and emails you the summary.")) return;
    setBusy(true);
    try {
      const r = await api.post("/dev/ops/cycle/close");
      setLast(r.data);
      toast.success(`Cycle ${r.data.cycle_label} closed.`);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };
  return (
    <div data-testid="cycle-close-section">
      <div className="section-label">// cycle close</div>
      <p className="mt-2 text-cool text-sm max-w-xl">
        Snapshot the month: orders shipped, revenue, churn, projected next month. Auto-generates POs for any inventory item below threshold. Emails you the summary.
      </p>
      <button onClick={close} disabled={busy} className="mt-3 btn-primary inline-flex items-center gap-2" data-testid="cycle-close-btn">
        {busy ? <Loader2 size={14} className="animate-spin" /> : <PlayCircle size={14} />} Close current cycle
      </button>
      {last && (
        <pre className="mt-3 p-3 border border-[#30363D] bg-carbon font-mono text-xs text-cool overflow-x-auto" data-testid="cycle-close-result">
{JSON.stringify(last, null, 2)}
        </pre>
      )}
    </div>
  );
}

/* ---------------------------------------- Live shop-floor feed (Item 14) */
function ShopFloor() {
  const [events, setEvents] = useState([]);
  const [connected, setConnected] = useState(false);
  const evtSrc = useRef(null);

  useEffect(() => {
    // Use relative URL with fallback for local development
    const url = `${process.env.REACT_APP_BACKEND_URL || ""}/api/dev/ops/feed`;
    const es = new EventSource(url, { withCredentials: true });
    evtSrc.current = es;
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    const handler = (e) => {
      try {
        const data = JSON.Parse(e.data || "{}");
        setEvents((prev) => [{ type: e.type, data, _key: Date.now() + Math.random() }, ...prev].slice(0, 30));
      } catch { /* ignore */ }
    };
    ["ready", "labels.batch", "order.fulfilled", "substitutions.approved", "cycle.closed", "replacement.approved"].forEach((t) => es.addEventListener(t, handler));
    return () => { es.close(); };
  }, []);

  return (
    <div data-testid="shop-floor-section">
      <div className="flex items-center gap-2">
        <Radio size={14} className={connected ? "text-flux" : "text-cool"} />
        <div className="section-label">// shop floor · {connected ? "live" : "connecting"}</div>
      </div>
      {events.length === 0 ? (
        <div className="mt-3 text-cool font-mono text-xs">No events yet. Trigger any /dev/ops action to see it stream here.</div>
      ) : (
        <ul className="mt-3 space-y-1 font-mono text-xs">
          {events.map((ev) => (
            <li key={ev._key} className="p-2 border border-[#30363D] bg-carbon flex items-start gap-3">
              <span className="text-circuit shrink-0">{ev.type}</span>
              <span className="text-cool truncate">{JSON.stringify(ev.data.payload)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/* =================================== combined Operations tab */
export default function OperationsTab() {
  return (
    <div className="space-y-10">
      <TodaysQueue />
      <div className="grid md:grid-cols-2 gap-10">
        <BatchLabels />
        <CycleClose />
      </div>
      <Replacements />
      <div className="grid md:grid-cols-2 gap-10">
        <Cohorts />
        <TaxNexus />
      </div>
      <ShopFloor />
    </div>
  );
}
