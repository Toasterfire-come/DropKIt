import React, { useEffect, useState } from "react";
import { useDocMeta } from "../lib/useDocMeta";
import api, { formatApiError } from "../lib/api";
import { toast } from "sonner";
import { Cpu, Github, ArrowRight, Repeat, Check } from "../lib/icons";
import { Link } from "react-router-dom";
import { useAuth, useUIMode } from "../lib/contexts";

export default function ProjectCatalog() {
  useDocMeta({ title: "Project archive — DropKit", description: "Every DropKit project, past and upcoming. Open-source schematics, full BOM, and build guides for each monthly kit." });
  const { user } = useAuth();
  const { mode } = useUIMode();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [subOptions, setSubOptions] = useState(null); // null = not loaded, []=loaded
  const [currentProject, setCurrentProject] = useState(null);
  const [substitutedTo, setSubstitutedTo] = useState(null);

  useEffect(() => {
    api.get("/projects").then((r) => setProjects(r.data)).finally(() => setLoading(false));
    api.get("/projects/current").then((r) => setCurrentProject(r.data)).catch(() => {});
  }, []);

  // Only logged-in subscribers (or dev) see sub options
  const canSubstitute = !!user && (user.role === "dev" || user.subscriptionStatus === "active");

  useEffect(() => {
    if (!canSubstitute) return;
    api.get("/substitutions/options")
      .then((r) => setSubOptions(r.data || []))
      .catch(() => setSubOptions([]));
  }, [canSubstitute]);

  const subOptionIds = new Set((subOptions || []).map((p) => p.id));
  const subOptionById = Object.fromEntries((subOptions || []).map((p) => [p.id, p]));

  const submitSubstitution = async (project) => {
    if (!currentProject) {
      toast.error("No active project to substitute.");
      return;
    }
    try {
      await api.post("/substitutions", {
        originalProjectId: currentProject.id,
        substitutedProjectId: project.id,
      });
      toast.success(`Locked in: ${project.title} ships this month.`);
      setSubstitutedTo(project.id);
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const current = projects.filter((p) => p.isActive);
  const past = projects.filter((p) => !p.isActive);
  const currentSection = [...current, ...past.slice(0, 6 - current.length)];
  const allOthers = past.slice(Math.max(0, 6 - current.length));

  return (
    <section className="container py-16">
      <span className="section-label">// ARCHIVE</span>
      <h1 className="mt-3 font-display text-4xl md:text-5xl font-bold">Project archive</h1>
      <p className="mt-3 text-cool text-sm max-w-2xl">
        Every DropKit project, past and present. All open source. All available to read, fork, and build.
      </p>

      {/* Subscriber-only substitution panel */}
      {canSubstitute && (
        <div className="mt-10 card p-6 md:p-8" data-testid="substitute-panel">
          <div className="flex items-start justify-between flex-wrap gap-3">
            <div>
              <span className="chip chip-orange inline-block"><Repeat size={12} strokeWidth={1.5} /> SUBSCRIBER PERK</span>
              <h2 className="mt-3 font-display text-2xl md:text-3xl font-bold">Swap this month's kit</h2>
              <p className="mt-2 text-cool text-sm max-w-2xl">
                Don't want this month's project? Pick any in-stock past kit instead. One swap per cycle, requested before the 10th.
              </p>
            </div>
            {currentProject && (
              <div className="text-right font-mono text-xs text-cool">
                <div>CURRENT KIT</div>
                <div className="text-warm">{currentProject.title}</div>
              </div>
            )}
          </div>
          {subOptions === null ? (
            <p className="mt-6 text-cool font-mono text-sm">Loading available kits…</p>
          ) : subOptions.length === 0 ? (
            <p className="mt-6 text-cool text-sm">No past kits are currently available for substitution. Check back next cycle.</p>
          ) : (
            <p className="mt-6 text-cool text-sm font-mono">{subOptions.length} kit{subOptions.length === 1 ? "" : "s"} available — eligible cards below have a <span className="text-circuit">Substitute</span> button.</p>
          )}
        </div>
      )}

      {!user && mode === "live" && (
        <p className="mt-6 text-sm text-cool">
          Subscribers can swap the current kit for any in-stock past kit.{" "}
          <Link to="/signin" className="text-circuit hover:underline">Sign in</Link> to use this.
        </p>
      )}

      {loading ? (
        <p className="mt-12 text-cool font-mono">Loading…</p>
      ) : (
        <>
          <section className="mt-14" data-testid="current-projects-section">
            <div className="flex items-end justify-between flex-wrap gap-2">
              <h2 className="font-display font-bold text-2xl md:text-3xl">Current projects</h2>
              <span className="font-mono text-xs text-cool">{currentSection.length} of 6</span>
            </div>
            <div className="mt-6 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {currentSection.map((p) => (
                <CatalogCard
                  key={p.id}
                  project={p}
                  canSubstitute={canSubstitute && !p.isActive && subOptionIds.has(p.id) && substitutedTo === null}
                  subMeta={subOptionById[p.id]}
                  substitutedTo={substitutedTo === p.id}
                  onSubstitute={() => submitSubstitution(p)}
                />
              ))}
              {Array.from({ length: Math.max(0, 6 - currentSection.length) }).map((_, i) => (
                <EmptySlot key={`slot-${i}`} />
              ))}
            </div>
          </section>

          <section className="mt-20" data-testid="all-projects-section">
            <div className="flex items-end justify-between flex-wrap gap-2">
              <h2 className="font-display font-bold text-2xl md:text-3xl">All projects</h2>
              <span className="font-mono text-xs text-cool">{allOthers.length}</span>
            </div>
            {allOthers.length === 0 ? (
              <div className="mt-6 grid sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="all-projects-empty">
                {Array.from({ length: 5 }).map((_, i) => (
                  <WaitingSlot key={`waiting-${i}`} index={i} />
                ))}
              </div>
            ) : (
              <div className="mt-6 grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
                {allOthers.map((p) => (
                  <CatalogCard
                    key={p.id}
                    project={p}
                    canSubstitute={canSubstitute && subOptionIds.has(p.id) && substitutedTo === null}
                    subMeta={subOptionById[p.id]}
                    substitutedTo={substitutedTo === p.id}
                    onSubstitute={() => submitSubstitution(p)}
                  />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </section>
  );
}

function CatalogCard({ project, canSubstitute, subMeta, substitutedTo, onSubstitute }) {
  return (
    <article className="card p-6 flex flex-col" data-testid={`project-card-${project.slug}`}>
      <div className="aspect-[4/3] mb-5 bg-graphite border border-[#30363D] flex items-center justify-center overflow-hidden">
        {project.imageUrl
          ? <img src={project.imageUrl} alt={project.title} className="w-full h-full object-cover" />
          : <Cpu size={48} strokeWidth={1} className="text-cool" />}
      </div>
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className="chip chip-orange">{project.difficulty}</span>
        <span className="chip font-mono">{project.board}</span>
        <span className="chip">{String(project.cycleMonth).padStart(2, "0")}/{project.cycleYear}</span>
        {project.isActive && <span className="chip chip-green">ACTIVE</span>}
        {subMeta?.sixthMonth && <span className="chip" style={{ borderLeftColor: "#FF4444", color: "#FF4444" }}>FINAL MONTH</span>}
      </div>
      <h3 className="font-display font-bold text-xl">{project.title}</h3>
      <p className="mt-3 text-cool leading-relaxed text-sm line-clamp-3">{project.description}</p>
      <div className="mt-auto pt-5 flex flex-wrap gap-2">
        <Link to={`/apps/makerbox/projects/${project.slug}`} className="btn-ghost text-sm py-2 px-3" data-testid={`card-view-${project.slug}`}>
          View guide <ArrowRight size={14} strokeWidth={1.5} />
        </Link>
        {project.githubUrl && (
          <a href={project.githubUrl} target="_blank" rel="noreferrer" className="btn-ghost text-sm py-2 px-3" data-testid={`card-github-${project.slug}`}>
            <Github size={14} strokeWidth={1.5} />
          </a>
        )}
        {substitutedTo ? (
          <span className="chip chip-green ml-auto" data-testid={`card-substituted-${project.slug}`}>
            <Check size={12} strokeWidth={2} /> SUBSTITUTED
          </span>
        ) : canSubstitute ? (
          <button
            onClick={onSubstitute}
            className="btn-primary text-sm py-2 px-3 ml-auto"
            data-testid={`card-substitute-${project.slug}`}
          >
            <Repeat size={14} strokeWidth={1.5} /> Substitute
          </button>
        ) : null}
      </div>
    </article>
  );
}

function EmptySlot() {
  return (
    <div className="card p-6 flex flex-col items-center justify-center text-center min-h-[260px] border-dashed" data-testid="project-empty-slot">
      <span className="chip mb-3 inline-block" style={{ borderLeftColor: "#8B949E", color: "#8B949E" }}>
        UPCOMING
      </span>
      <p className="text-cool text-sm">Waiting for next project.</p>
    </div>
  );
}

function WaitingSlot({ index }) {
  return (
    <article
      className="card p-6 flex flex-col items-center justify-center text-center min-h-[280px] border-dashed"
      data-testid={`waiting-slot-${index}`}
    >
      <span className="chip mb-4 inline-block" style={{ borderLeftColor: "#8B949E", color: "#8B949E" }}>
        UPCOMING
      </span>
      <Cpu size={36} strokeWidth={1} className="text-cool opacity-50" />
      <p className="mt-4 font-display font-bold text-lg">Waiting for next project</p>
      <p className="mt-2 text-cool text-xs font-mono uppercase tracking-widest">
        SLOT {String(index + 1).padStart(2, "0")} · TBA
      </p>
    </article>
  );
}
