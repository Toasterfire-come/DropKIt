import React, { useEffect, useState } from "react";
import { useDocMeta } from "../lib/useDocMeta";
import { Link } from "react-router-dom";
import api from "../lib/api";
import { Trophy, Zap, Users } from "../lib/icons";

export default function Leaderboard() {
  useDocMeta({ title: "Launch leaderboard — DropKit waitlist referrals", description: "The makers with the most waitlist referrals and earliest priority shipping when DropKit launches." });
  const [rows, setRows] = useState(null);

  useEffect(() => {
    api.get("/leaderboard").then((r) => setRows(r.data.rows || [])).catch(() => setRows([]));
  }, []);

  return (
    <section className="container py-16 max-w-3xl">
      <span className="section-label">// COMMUNITY</span>
      <h1 className="mt-3 font-display text-4xl md:text-5xl font-bold flex items-center gap-3">
        <Trophy size={34} strokeWidth={1.5} className="text-circuit" /> Launch leaderboard
      </h1>
      <p className="mt-3 text-cool max-w-2xl text-sm">
        Top makers helping us launch. <span className="text-warm">3 referrals</span> earns priority access.{" "}
        <span className="text-warm">5 paid referrals</span> earns the referrer a month on the house.
      </p>

      {rows === null ? (
        <p className="mt-12 text-cool font-mono text-sm">Loading…</p>
      ) : rows.length === 0 ? (
        <div className="card p-10 mt-12 text-center" data-testid="leaderboard-empty">
          <p className="text-cool text-sm">
            The leaderboard is empty for now. Be the first — join the waitlist and share your link.
          </p>
          <Link to="/" className="btn-primary mt-6 inline-flex">Join the waitlist</Link>
        </div>
      ) : (
        <ol className="mt-10 space-y-2" data-testid="leaderboard-rows">
          {rows.map((r, i) => (
            <li
              key={i}
              className="card flex items-center gap-5 p-4"
              data-testid={`leaderboard-row-${i}`}
            >
              <span className={`font-mono font-bold text-xl w-10 text-center ${i < 3 ? "text-circuit" : "text-cool"}`}>
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="flex-1 font-display font-semibold text-lg">{r.name}</span>
              <span className="inline-flex items-center gap-1.5 font-mono text-sm text-cool" title="Waitlist referrals">
                <Users size={14} strokeWidth={1.5} /> <span className="text-warm">{r.waitlistReferrals}</span>
              </span>
              <span className="inline-flex items-center gap-1.5 font-mono text-sm text-cool" title="Paid referrals">
                <Zap size={14} strokeWidth={1.5} className="text-flux" /> <span className="text-warm">{r.paidReferrals}</span>
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
