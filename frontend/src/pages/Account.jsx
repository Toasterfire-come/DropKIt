import React, { useEffect, useState } from "react";
import api, { formatApiError } from "../lib/api";
import { toast } from "sonner";
import { Pause, Play, SkipForward, ExternalLink, Gift, LogOut } from "lucide-react";
import { useAuth } from "../lib/contexts";
import { useNavigate, Link } from "react-router-dom";

export default function Account() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(null);

  const load = async () => {
    try {
      const r = await api.get("/account/subscription");
      setStatus(r.data);
    } catch {
      setStatus({ status: "inactive", canVote: false, voteEligibleCycles: [] });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const act = async (action) => {
    setActing(action);
    try {
      await api.post("/account/subscription", { action });
      toast.success(`${action} request submitted`);
      await load();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setActing(null);
    }
  };

  const onLogout = async () => {
    await logout();
    navigate("/");
  };

  return (
    <section className="container py-16">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <span className="section-label">// ACCOUNT</span>
          <h1 className="mt-3 font-display text-4xl md:text-5xl font-bold">Your DropKit</h1>
          <p className="mt-3 text-cool text-sm">
            Signed in as <span className="text-warm font-mono">{user?.email}</span>
            {user?.shopifyCustomerId && (
              <span className="chip chip-green ml-3 !py-0.5">SHOPIFY LINKED</span>
            )}
          </p>
        </div>
        <button onClick={onLogout} className="btn-ghost text-sm py-2 px-4" data-testid="account-logout-btn">
          <LogOut size={14} strokeWidth={1.5} /> Sign out
        </button>
      </div>

      <div className="mt-12 grid lg:grid-cols-3 gap-6">
        <SubscriptionCard status={status} loading={loading} acting={acting} act={act} />
        <RedeemGiftCard />
      </div>

      <div className="mt-10 grid md:grid-cols-3 gap-3">
        <Link to="/apps/makerbox/vote" className="card p-5 hover:!border-circuit transition-colors" data-testid="account-link-vote">
          <p className="font-mono text-xs text-cool uppercase tracking-widest">// VOTE</p>
          <p className="mt-2 font-display font-semibold">Pick next month's project</p>
        </Link>
        <Link to="/apps/makerbox/substitute" className="card p-5 hover:!border-circuit transition-colors" data-testid="account-link-substitute">
          <p className="font-mono text-xs text-cool uppercase tracking-widest">// SUBSTITUTE</p>
          <p className="mt-2 font-display font-semibold">Swap this month's kit</p>
        </Link>
        <a href="/account/orders" className="card p-5 hover:!border-circuit transition-colors" data-testid="account-link-orders">
          <p className="font-mono text-xs text-cool uppercase tracking-widest">// ORDERS</p>
          <p className="mt-2 font-display font-semibold inline-flex items-center gap-2">Shopify order history <ExternalLink size={14} strokeWidth={1.5} /></p>
        </a>
      </div>
    </section>
  );
}

function SubscriptionCard({ status, loading, acting, act }) {
  return (
    <div className="card p-8 lg:col-span-2" data-testid="account-subscription-card">
      <p className="section-label">// SUBSCRIPTION</p>
      {loading ? (
        <p className="mt-6 text-cool font-mono">Loading…</p>
      ) : !status || status.status === "inactive" ? (
        <div className="mt-4">
          <h2 className="font-display text-2xl font-bold">No active subscription</h2>
          <p className="mt-2 text-sm text-cool">
            Start your monthly DropKit from the subscribe page. Once your first order processes, you'll get vote eligibility automatically.
          </p>
          <Link to="/subscribe" className="btn-primary mt-6 inline-flex text-sm py-2 px-4" data-testid="account-subscribe-cta">
            Subscribe now
          </Link>
        </div>
      ) : (
        <>
          <div className="mt-4 flex items-center justify-between flex-wrap gap-4">
            <div>
              <span className="text-xs font-mono uppercase tracking-widest text-cool">Status</span>
              <div className="mt-1.5 inline-flex">
                <span className={`chip ${
                  status.status === "active" ? "chip-green" :
                  status.status === "paused" ? "chip-orange" : "chip-red"
                }`}>{status.status}</span>
              </div>
            </div>
            {status.nextBillingDate && (
              <div className="text-right">
                <span className="text-xs font-mono uppercase tracking-widest text-cool">Next bill</span>
                <div className="font-mono mt-1">{new Date(status.nextBillingDate).toLocaleDateString()}</div>
              </div>
            )}
          </div>

          <div className="mt-8 grid sm:grid-cols-3 gap-3">
            {status.status === "active" && (
              <>
                <button onClick={() => act("pause")} disabled={acting !== null}
                  className="btn-ghost text-sm py-2 px-4 justify-center" data-testid="account-pause-btn">
                  <Pause size={14} strokeWidth={1.5} /> Pause
                </button>
                <button onClick={() => act("skip")} disabled={acting !== null}
                  className="btn-ghost text-sm py-2 px-4 justify-center" data-testid="account-skip-btn">
                  <SkipForward size={14} strokeWidth={1.5} /> Skip next
                </button>
              </>
            )}
            {status.status === "paused" && (
              <button onClick={() => act("resume")} disabled={acting !== null}
                className="btn-primary text-sm py-2 px-4 justify-center" data-testid="account-resume-btn">
                <Play size={14} strokeWidth={1.5} /> Resume
              </button>
            )}
            <a href="/account" className="btn-ghost text-sm py-2 px-4 justify-center" data-testid="account-cancel-link">
              <ExternalLink size={14} strokeWidth={1.5} /> Cancel (Shopify)
            </a>
          </div>
        </>
      )}
    </div>
  );
}

function RedeemGiftCard() {
  const [code, setCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [redeemed, setRedeemed] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const r = await api.post("/gifts/redeem", { code: code.trim() });
      setRedeemed(r.data);
      toast.success("Gift redeemed.");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card p-8" data-testid="account-redeem-gift-card">
      <p className="section-label inline-flex items-center gap-2"><Gift size={14} strokeWidth={1.5} /> // REDEEM GIFT</p>
      {!redeemed ? (
        <form onSubmit={submit} className="mt-4 space-y-4" data-testid="account-redeem-form">
          <p className="text-sm text-cool">Have a gift code? Redeem it here to activate your subscription.</p>
          <input
            value={code} onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="MAKER-XXXX-2026" className="input font-mono text-sm"
            data-testid="account-redeem-code-input" required
          />
          <button type="submit" disabled={submitting} className="btn-primary w-full justify-center text-sm py-2 px-4" data-testid="account-redeem-submit">
            {submitting ? "Validating…" : "Redeem code"}
          </button>
        </form>
      ) : (
        <div className="mt-4" data-testid="account-redeem-success">
          <span className="chip chip-green">REDEEMED</span>
          <p className="mt-3 text-sm text-cool">
            Your <span className="text-warm">{redeemed.durationMonths}-month</span> gift is active.
          </p>
        </div>
      )}
    </div>
  );
}
