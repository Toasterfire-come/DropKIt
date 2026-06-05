import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { toast } from "sonner";
import { X } from "../lib/icons";
import ReferralSuccess from "./ReferralSuccess";
import { rememberMyCode, getMyCode } from "../lib/referral";

export default function WaitlistModal({ open, onClose }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [refCode, setRefCode] = useState(null);

  useEffect(() => {
    if (open) {
      const existing = getMyCode();
      if (existing) setRefCode(existing);
    }
  }, [open]);

  if (!open) return null;

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const ref = (typeof window !== "undefined" && localStorage.getItem("dropkit_ref")) || undefined;
      const refSrc = (typeof window !== "undefined" && localStorage.getItem("dropkit_ref_src")) || undefined;
      const r = await api.post("/waitlist", { name, email, source: "modal", ref, ref_src: refSrc });
      toast.success(r.data.message || "You're on the list.");
      rememberMyCode(r.data.referralCode);
      setRefCode(r.data.referralCode);
    } catch {
      toast.error("Could not save your info. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="waitlist-modal-title" data-testid="waitlist-modal">
      <div className="absolute inset-0 bg-pcb/85 backdrop-blur-sm" onClick={onClose} />
      <div className="relative card !rounded-sm p-8 max-w-md w-full circuit-bg">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-cool hover:text-warm"
          data-testid="waitlist-modal-close"
        >
          <X size={20} strokeWidth={1.5} />
        </button>

        {refCode ? (
          <ReferralSuccess code={refCode} />
        ) : (
          <>
            <span className="chip chip-orange inline-block">◉ LAUNCHING SOON</span>
            <h2 id="waitlist-modal-title" className="mt-4 font-display font-bold text-3xl">Join the waitlist</h2>
            <p className="mt-3 text-cool text-sm">
              We'll email you the moment subscriptions open. Share your link after joining — refer 3 friends and you skip the line, 5 paying referrals earns you a month free.
            </p>
            <form onSubmit={submit} className="mt-6 space-y-3" data-testid="waitlist-modal-form">
              <input
                type="text" required value={name} onChange={(e) => setName(e.target.value)}
                placeholder="Your name" className="input" minLength={1} maxLength={120}
                data-testid="waitlist-modal-name"
              />
              <input
                type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                placeholder="you@workbench.dev" className="input"
                data-testid="waitlist-modal-email"
              />
              <button type="submit" disabled={submitting} className="btn-primary w-full justify-center" data-testid="waitlist-modal-submit">
                {submitting ? "Saving…" : "Join the waitlist"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
