import React, { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Wrench, ArrowLeft } from "lucide-react";
import api, { formatApiError } from "../lib/api";
import { useDocMeta } from "../lib/useDocMeta";

export default function ReplacementRequest() {
  useDocMeta({
    title: "Damaged or missing component? — DropKit support",
    description: "Submit a free replacement request for any damaged, missing, or defective component in your DropKit. Single-component micro-parcel ships same-day.",
  });
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [form, setForm] = useState({
    email: "", name: "", order_label: "", component_name: "", description: "",
  });

  const update = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.post("/replacements", form);
      setDone(true);
      toast.success("Thanks — we'll be in touch within 48 hours.");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="container py-16 max-w-2xl">
      <Link to="/" className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-cool hover:text-warm" data-testid="replacement-back-link">
        <ArrowLeft size={14} /> Back
      </Link>
      <div className="mt-6 flex items-center gap-3">
        <Wrench size={28} strokeWidth={1.5} className="text-circuit" />
        <span className="section-label">// SUPPORT</span>
      </div>
      <h1 className="mt-3 font-display text-4xl md:text-5xl font-bold">Request a replacement</h1>
      <p className="mt-3 text-cool max-w-xl text-sm">
        Damaged in transit? Missing from the box? Wrong revision? Tell us which component and we'll ship a single-component micro-parcel — no return required.
      </p>

      {done ? (
        <div className="mt-10 p-8 border border-[#30363D] bg-carbon" data-testid="replacement-success">
          <div className="font-mono text-xs text-circuit uppercase tracking-widest">Submitted</div>
          <h2 className="mt-3 font-display text-2xl font-bold">We've got it.</h2>
          <p className="mt-3 text-cool text-sm">
            We'll review and email a tracking number to <strong className="text-warm">{form.email}</strong> within 48 hours. Most replacements ship the same day.
          </p>
        </div>
      ) : (
        <form onSubmit={submit} className="mt-10 space-y-4" data-testid="replacement-form">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="block">
              <div className="text-xs font-mono uppercase tracking-widest text-cool mb-1.5">Email *</div>
              <input
                required type="email" value={form.email} onChange={update("email")}
                placeholder="you@workbench.dev" className="input"
                data-testid="replacement-email-input"
              />
            </label>
            <label className="block">
              <div className="text-xs font-mono uppercase tracking-widest text-cool mb-1.5">Name</div>
              <input
                type="text" value={form.name} onChange={update("name")}
                placeholder="Your name" className="input"
                data-testid="replacement-name-input"
              />
            </label>
          </div>
          <label className="block">
            <div className="text-xs font-mono uppercase tracking-widest text-cool mb-1.5">Order # (optional)</div>
            <input
              type="text" value={form.order_label} onChange={update("order_label")}
              placeholder="DK-1234 or Shopify confirmation #" className="input" maxLength={80}
              data-testid="replacement-order-input"
            />
          </label>
          <label className="block">
            <div className="text-xs font-mono uppercase tracking-widest text-cool mb-1.5">Component *</div>
            <input
              required type="text" value={form.component_name} onChange={update("component_name")}
              placeholder="e.g. ATECC608A secure element" className="input" maxLength={120}
              data-testid="replacement-component-input"
            />
          </label>
          <label className="block">
            <div className="text-xs font-mono uppercase tracking-widest text-cool mb-1.5">What happened? *</div>
            <textarea
              required value={form.description} onChange={update("description")}
              placeholder="The pins were bent in transit — chip won't seat in socket."
              className="input min-h-[140px] resize-y" maxLength={2000}
              data-testid="replacement-description-input"
            />
          </label>
          <button
            type="submit" disabled={submitting} className="btn-primary"
            data-testid="replacement-submit-btn"
          >
            {submitting ? "Sending..." : "Send replacement request"}
          </button>
        </form>
      )}
    </section>
  );
}
