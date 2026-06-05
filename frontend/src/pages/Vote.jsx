import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { toast } from "sonner";
import { Vote as VoteIcon, Check } from "../lib/icons";

export default function Vote() {
  const [cycle, setCycle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [voted, setVoted] = useState(false);

  const load = async () => {
    try {
      const r = await api.get("/votes/current");
      setCycle(r.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const submitVote = async () => {
    if (!selected) return;
    setSubmitting(true);
    try {
      await api.post("/votes", { candidateProjectId: selected });
      toast.success("Vote recorded.");
      setVoted(true);
      await load();
    } catch (err) {
      const msg = err?.response?.data?.detail || "Vote failed — sign in via your account.";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <CenterMsg msg="Loading…" />;
  if (!cycle)
    return (
      <Wrapper>
        <EmptyVoteState />
      </Wrapper>
    );

  const total = cycle.totalVotes || 0;

  return (
    <Wrapper>
      <header className="mb-10">
        <span className="section-label">// VOTE</span>
        <h1 className="mt-3 font-display text-4xl md:text-5xl font-bold">
          Pick the {cycle.cycleYear}-{String(cycle.cycleMonth).padStart(2, "0")} project
        </h1>
        <p className="mt-3 text-cool text-sm">
          Voting closes {new Date(cycle.votingCloseAt).toLocaleString()}. One vote per subscriber.
        </p>
      </header>

      {(cycle.candidates || []).length === 0 ? (
        <div className="card p-10 text-center text-cool" data-testid="vote-no-candidates">
          Candidates being curated. Check back soon.
        </div>
      ) : (
        <div className="grid md:grid-cols-3 gap-6">
          {cycle.candidates.map((c) => {
            const count = cycle.results?.[c.id] || 0;
            const pct = total > 0 ? Math.round((count / total) * 100) : 0;
            const isSelected = selected === c.id;
            return (
              <button
                key={c.id}
                onClick={() => !voted && setSelected(c.id)}
                disabled={voted}
                data-testid={`vote-option-${c.slug}`}
                className={`text-left card p-6 transition-all duration-150 ${
                  isSelected ? "!border-circuit shadow-glow" : ""
                } ${voted ? "cursor-default" : "cursor-pointer"}`}
              >
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="chip chip-orange">{c.difficulty}</span>
                  <span className="chip font-mono">{c.board}</span>
                </div>
                <h3 className="mt-4 font-display font-bold text-lg">{c.title}</h3>
                <p className="mt-2 text-sm text-cool">{c.description}</p>
                {voted && (
                  <div className="mt-5">
                    <div className="trace-progress">
                      <span style={{ width: `${pct}%` }} />
                    </div>
                    <div className="mt-2 flex justify-between font-mono text-xs text-cool">
                      <span>{pct}%</span>
                      <span>{count} votes</span>
                    </div>
                  </div>
                )}
              </button>
            );
          })}
        </div>
      )}

      {!voted ? (
        <div className="mt-10">
          <button
            onClick={submitVote}
            disabled={!selected || submitting}
            className="btn-primary"
            data-testid="vote-submit-btn"
          >
            <VoteIcon size={18} strokeWidth={1.5} />
            {submitting ? "Submitting…" : "Submit vote"}
          </button>
        </div>
      ) : (
        <div className="mt-10 chip chip-green inline-flex items-center gap-2" data-testid="vote-confirmation">
          <Check size={14} strokeWidth={2} /> VOTE RECORDED
        </div>
      )}
    </Wrapper>
  );
}

function EmptyVoteState() {
  return (
    <div className="text-center py-16">
      <VoteIcon size={36} strokeWidth={1.5} className="text-circuit mx-auto" />
      <h1 className="mt-5 font-display text-3xl md:text-4xl font-bold">No vote open right now</h1>
      <p className="mt-3 text-cool max-w-md mx-auto">
        Voting opens on the 1st of each month and closes on the 7th. Subscribe to get a vote each cycle.
      </p>
    </div>
  );
}

function Wrapper({ children }) {
  return <section className="container py-16">{children}</section>;
}
function CenterMsg({ msg }) {
  return (
    <Wrapper>
      <p className="text-cool font-mono">{msg}</p>
    </Wrapper>
  );
}
