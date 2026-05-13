import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../lib/api";
import { Github, FileText, Youtube, ArrowLeft } from "lucide-react";
import { useDocMeta } from "../lib/useDocMeta";

export default function ProjectDetail() {
  const { slug } = useParams();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useDocMeta({
    title: project ? `${project.title} — DropKit project` : "Project — DropKit",
    description: project
      ? `${project.title}: ${(project.description || "").slice(0, 155)}`
      : "Open-source hardware project from DropKit's monthly maker box.",
  });
  useEffect(() => {
    api
      .get(`/projects/${slug}`)
      .then((r) => setProject(r.data))
      .catch(() => setError("Project not found"))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <Wrapper><p className="text-cool font-mono">Loading…</p></Wrapper>;
  if (error || !project)
    return (
      <Wrapper>
        <p className="text-cool">{error || "Not found"}.</p>
        <Link to="/apps/makerbox/projects" className="btn-ghost mt-6 text-sm py-2 px-4">
          <ArrowLeft size={14} strokeWidth={1.5} /> Back to archive
        </Link>
      </Wrapper>
    );

  return (
    <Wrapper>
      <Link to="/apps/makerbox/projects" className="text-cool text-sm hover:text-warm inline-flex items-center gap-1 mb-8">
        <ArrowLeft size={14} strokeWidth={1.5} /> Archive
      </Link>
      <div className="flex items-center gap-2 flex-wrap mb-4">
        <span className="chip chip-orange">{project.difficulty}</span>
        <span className="chip font-mono">{project.board}</span>
        <span className="chip">
          {String(project.cycleMonth).padStart(2, "0")}/{project.cycleYear}
        </span>
        {project.isActive && <span className="chip chip-green">CURRENT</span>}
      </div>
      <h1 className="font-display font-bold text-4xl md:text-5xl">{project.title}</h1>
      <p className="mt-4 text-cool max-w-2xl leading-relaxed">{project.description}</p>

      <div className="mt-8 flex flex-wrap gap-3">
        {project.githubUrl && (
          <a href={project.githubUrl} target="_blank" rel="noreferrer" className="btn-primary text-sm py-2 px-4">
            <Github size={14} strokeWidth={1.5} /> GitHub
          </a>
        )}
        {project.guideUrl && (
          <a href={project.guideUrl} target="_blank" rel="noreferrer" className="btn-ghost text-sm py-2 px-4">
            <FileText size={14} strokeWidth={1.5} /> PDF guide
          </a>
        )}
        {project.youtubeUrl && (
          <a href={project.youtubeUrl} target="_blank" rel="noreferrer" className="btn-ghost text-sm py-2 px-4">
            <Youtube size={14} strokeWidth={1.5} /> Video walkthrough
          </a>
        )}
      </div>

      {project.componentsPreview?.length > 0 && (
        <section className="mt-12">
          <h2 className="font-display font-bold text-2xl">In the box</h2>
          <ul className="mt-5 grid sm:grid-cols-2 gap-2 font-mono text-sm">
            {project.componentsPreview.map((c) => (
              <li key={c} className="card px-4 py-2.5">
                <span className="text-circuit">→</span> {c}
              </li>
            ))}
          </ul>
        </section>
      )}

      {project.guideContent && (
        <section className="mt-12 card p-8 prose-invert max-w-none">
          <h2 className="font-display font-bold text-2xl">Guide</h2>
          <pre className="mt-4 whitespace-pre-wrap font-sans text-warm leading-relaxed text-sm">
            {project.guideContent}
          </pre>
        </section>
      )}
    </Wrapper>
  );
}

function Wrapper({ children }) {
  return <section className="container py-16">{children}</section>;
}
