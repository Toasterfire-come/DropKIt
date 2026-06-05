import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import ReferralSuccess from "../components/ReferralSuccess";
import { ArrowLeft } from "../lib/icons";

export default function ReferralStatus() {
  const { code } = useParams();
  const [exists, setExists] = useState(null);

  useEffect(() => {
    api.get(`/waitlist/${code}/status`)
      .then(() => setExists(true))
      .catch(() => setExists(false));
  }, [code]);

  return (
    <section className="container py-20 max-w-2xl">
      <Link to="/" className="text-cool hover:text-warm inline-flex items-center gap-1.5 text-sm" data-testid="referral-status-back">
        <ArrowLeft size={14} strokeWidth={1.5} /> Home
      </Link>
      <span className="section-label mt-6 inline-block">// REFERRAL DASHBOARD</span>
      <h1 className="mt-3 font-display text-4xl md:text-5xl font-bold">Your launch status</h1>

      {exists === null && <p className="mt-8 text-cool font-mono text-sm">Loading…</p>}

      {exists === false && (
        <div className="mt-10 card p-8" data-testid="referral-status-not-found">
          <span className="chip" style={{ borderLeftColor: "#FF4444", color: "#FF4444" }}>NOT FOUND</span>
          <p className="mt-4 text-cool text-sm">
            We couldn't find that referral code. If you signed up, check the link in your confirmation email.
          </p>
          <Link to="/" className="btn-primary mt-6 inline-flex">Join the waitlist</Link>
        </div>
      )}

      {exists && (
        <div className="mt-10">
          <ReferralSuccess code={(code || "").toUpperCase()} />
          <div className="mt-6">
            <Link to="/leaderboard" className="text-circuit text-sm hover:underline">
              See the launch leaderboard →
            </Link>
          </div>
        </div>
      )}
    </section>
  );
}
