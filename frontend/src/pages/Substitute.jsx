import React, { useEffect, useState } from "react";
import api from "../lib/api";
import { toast } from "sonner";
import { Replace } from "../lib/icons";

export default function Substitute() {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submittingId, setSubmittingId] = useState(null);

  useEffect(() => {
    api
      .get("/substitutions/options")
      .then((r) => setOptions(r.data))
      .catch(() => toast.error("Could not load options. Subscribers only."))
      .finally(() => setLoading(false));
  }, []);

  const submit = async (project) => {
    setSubmittingId(project.id);
    try {
      await api.post("/substitutions", {
        originalProjectId: "current",
        substitutedProjectId: project.id,
      });
      toast.success(`Substitution requested: ${project.title}`);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Substitution failed");
    } finally {
      setSubmittingId(null);
    }
  };

  return (
    <section className="container py-16">
      <header className="mb-10">
        <span className="section-label">// SUBSTITUTE</span>
        <h1 className="mt-3 font-display text-4xl md:text-5xl font-bold">Swap this month's kit</h1>
        <p className="mt-3 text-cool text-sm max-w-2xl">
          Pick from the past 6 months of past projects (stock allowing). One substitution per cycle, before the 10th.
        </p>
      </header>

      {loading ? (
        <p className="text-cool font-mono">Loading…</p>
      ) : options.length === 0 ? (
        <div className="card p-10 text-center" data-testid="substitute-empty">
          <Replace size={28} strokeWidth={1.5} className="text-circuit mx-auto" />
          <p className="mt-4 text-cool max-w-md mx-auto">
            No past projects available yet. After a few more drops, you'll be able to substitute into any of the last 6 months.
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-3 gap-6">
          {options.map((p) => (
            <div key={p.id} className="card p-6" data-testid={`substitute-card-${p.slug}`}>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="chip chip-orange">{p.difficulty}</span>
                <span className="chip font-mono">{p.board}</span>
                <span className={`chip ${p.stockCount > 10 ? "chip-green" : p.stockCount > 0 ? "chip-orange" : "chip-red"}`}>
                  {p.stockCount > 10 ? "AVAILABLE" : p.stockCount > 0 ? "LOW STOCK" : "SOLD OUT"}
                </span>
              </div>
              <h3 className="mt-4 font-display font-bold text-lg">{p.title}</h3>
              <p className="mt-2 text-sm text-cool">{p.description}</p>
              <button
                onClick={() => submit(p)}
                disabled={p.stockCount <= 0 || submittingId === p.id}
                className="btn-primary mt-5 text-sm py-2 px-4"
                data-testid={`substitute-select-${p.slug}`}
              >
                {submittingId === p.id ? "Submitting…" : "Substitute this month"}
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
