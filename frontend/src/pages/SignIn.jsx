import React, { useEffect, useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../lib/contexts";
import api, { formatApiError } from "../lib/api";
import { toast } from "sonner";
import { LogIn, ShoppingBag } from "lucide-react";

export default function SignIn() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = location.state?.from || "/account";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [shopifyEnabled, setShopifyEnabled] = useState(false);

  useEffect(() => {
    api.get("/launch-mode").then((r) => setShopifyEnabled(!!r.data.shopify_auth_enabled)).catch(() => {});
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      toast.success("Signed in.");
      navigate(redirectTo, { replace: true });
    } catch (err) {
      const msg = formatApiError(err);
      setError(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const shopifyLogin = async () => {
    try {
      const r = await api.get("/auth/shopify/login");
      window.location.href = r.data.redirect_url;
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  return (
    <section className="container py-20 max-w-md">
      <span className="section-label">// SIGN IN</span>
      <h1 className="mt-3 font-display text-4xl font-bold flex items-center gap-3">
        <LogIn size={30} strokeWidth={1.5} className="text-circuit" /> Welcome back
      </h1>
      <p className="mt-3 text-cool text-sm">
        Sign in to vote, manage your subscription, or redeem a gift.
      </p>

      {shopifyEnabled && (
        <button
          type="button"
          onClick={shopifyLogin}
          className="btn-primary w-full justify-center mt-8"
          data-testid="signin-shopify-btn"
        >
          <ShoppingBag size={16} strokeWidth={1.5} /> Continue with Shopify
        </button>
      )}
      {shopifyEnabled && (
        <div className="mt-6 flex items-center gap-3 text-xs font-mono uppercase tracking-widest text-cool">
          <span className="flex-1 h-px bg-[#30363D]" /> or email <span className="flex-1 h-px bg-[#30363D]" />
        </div>
      )}

      <form onSubmit={submit} className={`${shopifyEnabled ? "mt-6" : "mt-10"} space-y-4`} data-testid="signin-form">
        <Field label="Email">
          <input
            type="email" required value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input" data-testid="signin-email"
            placeholder="you@workbench.dev"
          />
        </Field>
        <Field label="Password">
          <input
            type="password" required value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input" data-testid="signin-password"
            placeholder="••••••••"
          />
        </Field>
        {error && <p className="chip chip-red inline-block">{error}</p>}
        <button type="submit" disabled={submitting} className="btn-primary w-full justify-center" data-testid="signin-submit">
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className="mt-6 text-sm text-cool">
        No account?{" "}
        <Link to="/signup" className="text-circuit hover:underline" data-testid="signin-to-signup">Create one</Link>
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
