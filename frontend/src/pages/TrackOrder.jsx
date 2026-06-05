import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import { Package, Truck, CheckCircle2, Clock } from "../lib/icons";

const STATUS_ICONS = {
  completed: CheckCircle2,
  in_progress: Truck,
  pending: Clock,
};

function Timeline({ events }) {
  return (
    <div className="relative pl-8 before:content-[''] before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-px before:bg-[#30363D]">
      {events.map((ev, i) => {
        const Icon = STATUS_ICONS[ev.status] || Clock;
        const colors = ev.status === "completed"
          ? "text-flux border-flux/40"
          : ev.status === "in_progress"
          ? "text-circuit border-circuit/40"
          : "text-cool border-cool/40";
        return (
          <div key={i} className="relative pb-8 last:pb-0">
            <div className={`absolute -left-[22px] w-9 h-9 rounded-full border-2 bg-pcb flex items-center justify-center ${colors}`}>
              <Icon size={14} strokeWidth={2} />
            </div>
            <div>
              <p className="font-semibold text-warm">{ev.event}</p>
              {ev.date && (
                <p className="text-xs text-cool font-mono mt-0.5">
                  {new Date(ev.date).toLocaleDateString("en-US", {
                    weekday: "short", month: "short", day: "numeric", year: "numeric",
                  })}
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function TrackOrder() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    api.get(`/track/${token}`)
      .then((r) => setData(r.data))
      .catch((err) => {
        setError(err.response?.status === 404 ? "Order not found" : "Could not load tracking");
      })
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <section className="container py-16 max-w-2xl">
      <div className="flex items-center gap-3 mb-2">
        <Package size={24} strokeWidth={1.5} className="text-circuit" />
        <span className="section-label">// TRACK YOUR KIT</span>
      </div>

      {loading && <p className="text-cool mt-8">Loading tracking info...</p>}

      {error && (
        <div className="card p-10 mt-8 text-center">
          <p className="text-cool text-lg">{error}</p>
          <p className="text-sm text-cool mt-3">
            Check the link in your email or{" "}
            <Link to="/help/replacement" className="text-circuit hover:underline">contact us</Link>.
          </p>
        </div>
      )}

      {data && (
        <>
          <h1 className="mt-3 font-display text-3xl md:text-4xl font-bold">
            {data.project_title}
          </h1>
          <p className="mt-2 text-cool">
            {data.recipient_name ? `for ${data.recipient_name}` : ""}
          </p>

          {/* Status badge */}
          <div className="mt-6 flex flex-wrap gap-3 items-center">
            <span className={`chip ${
              data.status === "fulfilled" ? "chip-green" :
              data.status === "paid" ? "chip-orange" : "chip"
            }`}>
              {data.status?.charAt(0).toUpperCase() + data.status?.slice(1) || "Pending"}
            </span>
            {data.kitting_status && data.kitting_status !== "shipped" && (
              <span className="chip font-mono">
                {data.kitting_status === "paid" ? "Awaiting pick" :
                 data.kitting_status === "kitting" ? "Being packed" :
                 data.kitting_status === "packed" ? "Labeled" : data.kitting_status}
              </span>
            )}
          </div>

          {/* Tracking number */}
          {data.shipment?.tracking_code && (
            <div className="card p-5 mt-8 flex items-center gap-4">
              <Truck size={22} strokeWidth={1.5} className="text-circuit flex-shrink-0" />
              <div>
                <p className="font-semibold">
                  {data.shipment.carrier} — {data.shipment.service}
                </p>
                <p className="font-mono text-sm text-cool mt-0.5">
                  {data.shipment.tracking_code}
                </p>
                <a
                  href={`https://t.17track.net/en#nums=${data.shipment.tracking_code}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-circuit text-sm hover:underline inline-flex items-center gap-1 mt-1"
                >
                  Track on 17Track &rarr;
                </a>
              </div>
            </div>
          )}

          {/* Timeline */}
          {data.timeline && data.timeline.length > 0 && (
            <div className="card p-8 mt-8">
              <h2 className="font-display font-bold text-xl mb-6">Timeline</h2>
              <Timeline events={data.timeline} />
            </div>
          )}

          {/* Help */}
          <div className="mt-10 p-6 border border-[#30363D] rounded-sm text-center">
            <p className="text-cool text-sm">
              Something wrong?{" "}
              <Link to="/help/replacement" className="text-circuit hover:underline">
                Request a replacement
              </Link>
              {" "}or{" "}
              <Link to="/pages/faq" className="text-circuit hover:underline">
                visit FAQ
              </Link>.
            </p>
          </div>
        </>
      )}
    </section>
  );
}