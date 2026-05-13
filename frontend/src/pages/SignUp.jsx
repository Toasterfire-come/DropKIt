import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/contexts";
import { formatApiError } from "../lib/api";
import { toast } from "sonner";
import { UserPlus } from "lucide-react";

export default function SignUp() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [form, setForm] = useState({ email: "", password: "", name: "" });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const onChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    if (form.password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setSubmitting(true);
    try {
      await register(form.email, form.password, form.name || null);
      toast.success("Account created — taking you to checkout.");
      navigate("/subscribe", { replace: true });
    } catch (err) {
      const msg = formatApiError(err);
      setError(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="container py-20 max-w-md">
      <span className="section-label">// CREATE ACCOUNT</span>
      <h1 className="mt-3 font-display text-4xl font-bold flex items-center gap-3">
        <UserPlus size={30} strokeWidth={1.5} className="text-circuit" /> Join DropKit
      </h1>
      <p className="mt-3 text-cool text-sm">
        Your account is linked to Shopify for ordering, voting, and gift redemption — all in one identity.
      </p>

      <form onSubmit={submit} className="mt-10 space-y-4" data-testid="signup-form">
        <Field label="Name (optional)">
          <input name="name" value={form.name} onChange={onChange} className="input" data-testid="signup-name" placeholder="Your name" />
        </Field>
        <Field label="Email">
          <input
            type="email" required name="email" value={form.email} onChange={onChange}
            className="input" data-testid="signup-email" placeholder="you@workbench.dev"
          />
        </Field>
        <Field label="Password">
          <input
            type="password" required minLength={8} name="password" value={form.password} onChange={onChange}
            className="input" data-testid="signup-password" placeholder="At least 8 characters"
          />
        </Field>
        {error && <p className="chip chip-red inline-block">{error}</p>}
        <button type="submit" disabled={submitting} className="btn-primary w-full justify-center" data-testid="signup-submit">
          {submitting ? "Creating…" : "Create account"}
        </button>
      </form>

      <p className="mt-6 text-sm text-cool">
        Already have one?{" "}
        <Link to="/signin" className="text-circuit hover:underline" data-testid="signup-to-signin">Sign in</Link>
      </p>
    </section>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-xs font-mono uppercase tracking-widest text-cool">{label}</span>
      <div className="mt-2">{children}</div>
    </label>
  );
}
