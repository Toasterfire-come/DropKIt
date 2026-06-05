import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { buildShareUrl } from "../lib/referral";
import { toast } from "sonner";
import { Copy, Check, Users, Zap } from "../lib/icons";
import SharePicker from "./SharePicker";

export default function ReferralSuccess({ code, compact = false }) {
  const [stats, setStats] = useState(null);
  const [copied, setCopied] = useState(false);
  const shareUrl = buildShareUrl(code);

  useEffect(() => {
    let mounted = true;
    api.get(`/waitlist/${code}/status`)
      .then((r) => mounted && setStats(r.data))
      .catch(() => {});
    return () => { mounted = false; };
  }, [code]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toast.success("Share link copied.");
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Copy failed — long-press the link to share.");
    }
  };

  const wl = stats?.waitlistReferrals ?? 0;
  const paid = stats?.paidReferrals ?? 0;
  const priority = stats?.priority;
  const free = stats?.freeMonthEarned;
  const wlPct = Math.min(100, (wl / 3) * 100);
  const paidPct = Math.min(100, (paid / 5) * 100);

  return (
    <div
      className={`${compact ? "" : "card p-6"} space-y-4`}
      data-testid="referral-success"
    >
      {!compact && (
        <div>
          <span className="chip chip-green inline-block">✓ YOU'RE ON THE LIST</span>
          <h3 className="mt-3 font-display font-bold text-xl">
            Share your link. Skip the line.
          </h3>
          <p className="mt-2 text-cool text-sm leading-relaxed">
            <span className="text-warm">3 waitlist signups</span> from your link → you jump to the top of launch.<br />
            <span className="text-warm">5 paying referrals</span> after launch → you get <span className="text-circuit">a free month on us</span>.
          </p>
        </div>
      )}

      <div className="flex items-center gap-2">
        <input
          value={shareUrl}
          readOnly
          className="input font-mono text-xs"
          data-testid="referral-link-input"
          onClick={(e) => e.currentTarget.select()}
        />
        <button
          onClick={copy}
          className="btn-primary text-sm py-2 px-3 whitespace-nowrap"
          data-testid="referral-copy-btn"
        >
          {copied ? <Check size={14} strokeWidth={2} /> : <Copy size={14} strokeWidth={1.5} />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      <div className="space-y-3">
        <ProgressRow
          icon={Users}
          label="Waitlist referrals"
          current={wl}
          target={3}
          pct={wlPct}
          unlocked={priority}
          unlockedLabel="PRIORITY UNLOCKED"
          testid="referral-progress-waitlist"
        />
        <ProgressRow
          icon={Zap}
          label="Paid referrals (after launch)"
          current={paid}
          target={5}
          pct={paidPct}
          unlocked={free}
          unlockedLabel="FREE MONTH UNLOCKED"
          testid="referral-progress-paid"
        />
      </div>

      <p className="font-mono text-[0.65rem] text-cool tracking-widest uppercase">
        YOUR CODE · <span className="text-circuit">{code}</span>
      </p>

      <div className="pt-2 border-t border-[#30363D]">
        <SharePicker code={code} />
      </div>
    </div>
  );
}

function ProgressRow({ icon: Icon, label, current, target, pct, unlocked, unlockedLabel, testid }) {
  return (
    <div data-testid={testid}>
      <div className="flex items-center justify-between text-xs font-mono">
        <span className="inline-flex items-center gap-1.5 text-cool uppercase tracking-widest">
          <Icon size={12} strokeWidth={1.5} className={unlocked ? "text-flux" : "text-circuit"} /> {label}
        </span>
        <span className={unlocked ? "text-flux" : "text-warm"}>
          {current}/{target}{unlocked ? ` · ${unlockedLabel}` : ""}
        </span>
      </div>
      <div className="trace-progress mt-1.5">
        <span style={{ width: `${pct}%`, background: unlocked ? "var(--flux)" : undefined }} />
      </div>
    </div>
  );
}
