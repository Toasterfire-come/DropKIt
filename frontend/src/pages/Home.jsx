import React, { useState, useEffect } from "react";
import api from "../lib/api";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import { Cpu, Vote as VoteIcon, Package, ArrowRight, Github, MessageCircle, ChevronDown, Zap, Search } from "lucide-react";
import { useUIMode } from "../lib/contexts";
import { captureRefFromUrl, rememberMyCode, getMyCode } from "../lib/referral";
import ReferralSuccess from "../components/ReferralSuccess";

export default function Home() {
  const { mode } = useUIMode();
  const [currentProject, setCurrentProject] = useState(null);
  const [pastProjects, setPastProjects] = useState([]);
  const [voteCycle, setVoteCycle] = useState(null);

  useEffect(() => {
    api.get("/projects/current").then((r) => setCurrentProject(r.data));
    api.get("/projects/past", { params: { limit: 6 } }).then((r) => setPastProjects(r.data));
    api.get("/votes/current").then((r) => setVoteCycle(r.data));
  }, []);

  return (
    <>
      {mode === "waitlist" ? <WaitlistHero /> : <Hero />}
      {mode === "waitlist" && <SponsorBanner />} {/* Added SponsorBanner for waitlist mode */}
      <HowItWorks />
      <CurrentProject project={currentProject} mode={mode} />
      <CommunityVote voteCycle={voteCycle} />
      <PastProjectsRow projects={pastProjects} />
      <OpenSource />
      <FAQSection />
    </>
  );
}

/* ------------------------------------------------- Waitlist Hero */
function WaitlistHero() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [refCode, setRefCode] = useState(null);
  const [showLookup, setShowLookup] = useState(false);
  const [referrerFirstName, setReferrerFirstName] = useState(null);

  useEffect(() => {
    const inviter = captureRefFromUrl();
    // Auto-display dashboard for returning users who already joined on this device
    const existing = getMyCode();
    if (existing) setRefCode(existing);
    // Conversion lift: personalise the hero for referred visitors
    if (inviter && !existing) {
      api.get(`/waitlist/${inviter}/status`)
        .then((r) => {
          const full = (r.data && r.data.name) || "";
          const first = full.trim().split(/\s+/)[0];
          if (first) setReferrerFirstName(first);
        })
        .catch(() => { /* unknown code — leave default copy */ });
    }
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const ref = (typeof window !== "undefined" && localStorage.getItem("dropkit_ref")) || undefined;
      const refSrc = (typeof window !== "undefined" && localStorage.getItem("dropkit_ref_src")) || undefined;
      const r = await api.post("/waitlist", { name, email, source: "home_hero", ref, ref_src: refSrc });
      toast.success(r.data.message || "You're on the list.");
      rememberMyCode(r.data.referralCode);
      setRefCode(r.data.referralCode);
    } catch (err) {
      toast.error("Could not save your info. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const onLookupFound = (code) => {
    rememberMyCode(code);
    setRefCode(code);
    setShowLookup(false);
  };

  const useDifferentEmail = () => {
    forgetMyCode();
    setRefCode(null);
    setName("");
    setEmail("");
  };

  return (
    <section className="circuit-bg relative overflow-hidden border-b border-[#30363D]" data-testid="hero-section">
      <div className="container py-24 md:py-32 grid md:grid-cols-12 gap-10 items-center">
        <div className="md:col-span-7 reveal">
          <span className="chip chip-orange mb-6 pulse-glow inline-block" data-testid="hero-launching-badge">
            ◉ SHIPPING SOON
          </span>
          {referrerFirstName ? (
            <h1 className="font-display font-bold text-5xl md:text-7xl leading-[1.02] tracking-tight" data-testid="hero-personalised">
              <span className="text-circuit">{referrerFirstName}</span> thinks<br />
              you'd love this.
            </h1>
          ) : (
            <h1 className="font-display font-bold text-5xl md:text-7xl leading-[1.02] tracking-tight">
              Hardware projects,<br />
              <span className="text-circuit">delivered.</span>
            </h1>
          )}
          <p className="mt-6 text-lg text-cool max-w-xl leading-relaxed">
            {referrerFirstName ? (
              <>A curated open-source electronics project, every month. {referrerFirstName}'s on the list — you'll skip ahead of everyone after them when you join below.</>
            ) : (
              <>A curated open-source electronics project, every month. Microcontroller, all
              components, full guide, and a community vote on what comes next.</>
            )}
          </p>

          {refCode ? (
            <div className="mt-10 max-w-md space-y-3" data-testid="waitlist-success">
              <ReferralSuccess code={refCode} />
              <button onClick={useDifferentEmail} className="text-xs font-mono text-cool hover:text-warm" data-testid="waitlist-use-different">
                ↳ use a different email
              </button>
            </div>
          ) : showLookup ? (
            <LookupForm onFound={onLookupFound} onBack={() => setShowLookup(false)} />
          ) : (
            <>
              <form onSubmit={submit} className="mt-10 max-w-md space-y-3" data-testid="waitlist-form">
                <input
                  type="text" required value={name} onChange={(e) => setName(e.target.value)}
                  placeholder="Your name" minLength={1} maxLength={120}
                  className="input" data-testid="waitlist-name-input"
                />
                <div className="flex gap-2">
                  <input
                    type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@workbench.dev"
                    className="input" data-testid="waitlist-email-input"
                  />
                  <button type="submit" disabled={submitting} className="btn-primary whitespace-nowrap" data-testid="waitlist-submit-btn">
                    {submitting ? "..." : "Join the waitlist"}
                  </button>
                </div>
              </form>
              <button
                type="button"
                onClick={() => setShowLookup(true)}
                className="mt-4 inline-flex items-center gap-1.5 text-xs font-mono uppercase tracking-widest text-cool hover:text-warm"
                data-testid="waitlist-find-link-btn"
              >
                <Search size={12} strokeWidth={1.5} /> Already joined? Find my share link
              </button>
            </>
          )}

          <div className="mt-6 flex items-center gap-4 text-xs font-mono text-cool">
            <span className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-flux rounded-full pulse-glow" /> US ONLY · MVP</span>
            <span>OPEN SOURCE · MIT/CC BY-SA</span>
          </div>
        </div>
        <div className="md:col-span-5 hidden md:block reveal reveal-delay-2">
          <BoardArt />
        </div>
      </div>
    </section>
  );
}

function LookupForm({ onFound, onBack }) {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await api.post("/waitlist/lookup", { email });
      if (r.data.found) {
        toast.success("Found your link.");
        onFound(r.data.referralCode);
      } else {
        toast.error("That email isn't on the list yet — join above.");
      }
    } catch {
      toast.error("Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="mt-10 max-w-md space-y-3" data-testid="waitlist-lookup-form">
      <p className="font-mono text-xs uppercase tracking-widest text-cool">// FIND MY SHARE LINK</p>
      <div className="flex gap-2">
        <input
          type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
          placeholder="email you signed up with"
          className="input" data-testid="waitlist-lookup-email"
        />
        <button type="submit" disabled={busy} className="btn-primary whitespace-nowrap" data-testid="waitlist-lookup-submit">
          {busy ? "..." : "Find it"}
        </button>
      </div>
      <button type="button" onClick={onBack} className="text-xs font-mono text-cool hover:text-warm" data-testid="waitlist-lookup-back">
        ← back to join the waitlist
      </button>
    </form>
  );
}

/* ---------------------------------------- Live Hero */
function Hero() {
  return (
    <section className="circuit-bg relative overflow-hidden border-b border-[#30363D]" id="subscribe" data-testid="hero-section">
      <div className="container py-24 md:py-32 grid md:grid-cols-12 gap-10 items-center">
        <div className="md:col-span-7 reveal">
          <span className="chip chip-green inline-block">◉ NOW SHIPPING</span>
          <h1 className="font-display font-bold text-5xl md:text-7xl leading-[1.02] tracking-tight">
            Build something<br />
            <span className="text-circuit">real this month.</span>
          </h1>
          <p className="mt-6 text-lg text-cool max-w-xl leading-relaxed">
            A monthly open-source hardware project — board, components, guide. Vote on what we
            build next. Built for makers, by makers.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link to="/subscribe" className="btn-primary" data-testid="hero-subscribe-btn">
              Subscribe Now <ArrowRight size={18} strokeWidth={1.5} />
            </Link>
            <Link to="/gift" className="btn-ghost" data-testid="hero-gift-btn">
              Buy a gift
            </Link>
            <span className="font-mono text-sm text-cool ml-1">
              <span className="text-warm text-xl font-bold">$40</span>
              <span className="text-cool">/mo + shipping</span>
            </span>
          </div>
        </div>
        <div className="md:col-span-5 hidden md:block reveal reveal-delay-2">
          <BoardArt />
        </div>
      </div>
    </section>
  );
}

function BoardArt() {
  return (
    <div className="relative aspect-square max-w-md mx-auto">
      <svg viewBox="0 0 400 400" className="w-full h-full">
        <defs>
          <linearGradient id="g1" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#161B22" />
            <stop offset="1" stopColor="#0D1117" />
          </linearGradient>
        </defs>
        <rect x="40" y="40" width="320" height="320" rx="3" fill="url(#g1)" stroke="#30363D" />
        <g stroke="#E8510A" strokeWidth="1.2" fill="none" opacity="0.9">
          <path d="M40 100 L120 100 L120 160 L240 160 L240 260 L360 260" />
          <path d="M40 200 L80 200 L80 320 L200 320" />
          <path d="M280 40 L280 120 L340 120 L340 220" />
        </g>
        {[[120, 100], [120, 160], [240, 160], [240, 260], [80, 200], [80, 320], [200, 320], [280, 120], [340, 120], [340, 220]].map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r="4" fill="#E8510A" />
        ))}
        <rect x="160" y="170" width="100" height="80" fill="#21262D" stroke="#E8510A" strokeWidth="1.5" />
        <text x="210" y="216" textAnchor="middle" fill="#E8510A" fontFamily="JetBrains Mono" fontSize="11" fontWeight="700">DROPKIT</text>
        <text x="210" y="232" textAnchor="middle" fill="#8B949E" fontFamily="JetBrains Mono" fontSize="8">v1.0.0</text>
        {[170, 190, 210, 230, 250].map((y) => (
          <g key={y}>
            <line x1="160" y1={y - 5} x2="150" y2={y - 5} stroke="#E8510A" strokeWidth="1" />
            <line x1="260" y1={y - 5} x2="270" y2={y - 5} stroke="#E8510A" strokeWidth="1" />
          </g>
        ))}
        <circle cx="320" cy="80" r="6" fill="#39D353">
          <animate attributeName="opacity" values="0.4;1;0.4" dur="1.6s" repeatCount="indefinite" />
        </circle>
      </svg>
    </div>
  );
}

function HowItWorks() {
  const steps = [
    { num: "01", icon: VoteIcon, title: "Vote", desc: "Subscribers vote each month on the project two months ahead." },
    { num: "02", icon: Cpu, title: "Build", desc: "We source, kit, and write the guide for the winning project." },
    { num: "03", icon: Package, title: "Receive", desc: "A complete kit lands on your doorstep. Solder, code, learn." },
  ];
  return (
    <section className="py-20 border-b border-[#30363D]">
      <div className="container">
        <span className="section-label">// PROCESS</span>
        <h2 className="mt-3 font-display text-3xl md:text-4xl font-bold">How it works</h2>
        <div className="mt-12 grid md:grid-cols-3 gap-8 relative">
          {steps.map((s, i) => (
            <div key={s.num} className="reveal" style={{ animationDelay: `${100 + i * 100}ms` }}>
              <div className="flex items-center gap-4">
                <span className="step-num">{s.num}</span>
                <s.icon size={22} strokeWidth={1.5} className="text-circuit" />
              </div>
              <h3 className="mt-5 font-display text-xl font-semibold">{s.title}</h3>
              <p className="mt-2 text-cool leading-relaxed text-sm">{s.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function CurrentProject({ project, mode }) {
  return (
    <section className="py-20 border-b border-[#30363D]">
      <div className="container">
        <span className="section-label">// THIS MONTH</span>
        <div className="mt-3 flex items-end justify-between flex-wrap gap-3">
          <h2 className="font-display text-3xl md:text-4xl font-bold">Current project</h2>
          <Link to="/apps/makerbox/projects" className="text-circuit text-sm hover:underline inline-flex items-center gap-1" data-testid="current-project-view-all">
            View archive <ArrowRight size={14} strokeWidth={1.5} />
          </Link>
        </div>
        <div className="mt-10">
          {project ? (
            <ProjectCard project={project} featured />
          ) : (
            <EmptyProjectState mode={mode} />
          )}
        </div>
      </div>
    </section>
  );
}

function EmptyProjectState({ mode }) {
  return (
    <div className="card p-10 md:p-14 grid md:grid-cols-2 gap-8 items-center" data-testid="current-project-empty">
      <div>
        <span className="chip mb-4 inline-block" style={{ borderLeftColor: "#8B949E", color: "#8B949E" }}>KIT TBA</span>
        <h3 className="font-display text-2xl md:text-3xl font-bold">The first DropKit lands soon.</h3>
        <p className="mt-4 text-cool leading-relaxed">
          We're finalizing the inaugural project — board selection, BOM, and guide. {mode === "live" ? "Subscribe early to get it on day one and vote on month two." : "Drop your name and email above and we'll let you know the moment it's live."}
        </p>
        {mode === "live" && (
          <div className="mt-6 flex flex-wrap gap-3">
            <Link to="/subscribe" className="btn-primary">Subscribe Now</Link>
            <Link to="/gift" className="btn-ghost">Buy a gift</Link>
          </div>
        )}
      </div>
      <div className="relative h-56 md:h-72">
        <BoardArt />
      </div>
    </div>
  );
}

export function ProjectCard({ project, featured = false }) {
  return (
    <article className={`card p-6 ${featured ? "md:p-10 md:grid md:grid-cols-5 gap-8 items-center" : "flex flex-col"}`} data-testid={`project-card-${project.slug}`}>
      <div className={`${featured ? "md:col-span-2" : ""} aspect-[4/3] mb-5 md:mb-0 bg-graphite border border-[#30363D] flex items-center justify-center overflow-hidden`}>
        {project.imageUrl ? <img src={project.imageUrl} alt={project.title} className="w-full h-full object-cover" /> : <Cpu size={48} strokeWidth={1} className="text-cool" />}
      </div>
      <div className={`${featured ? "md:col-span-3" : ""}`}>
        <div className="flex items-center gap-2 mb-3 flex-wrap">
          <span className="chip chip-orange">{project.difficulty}</span>
          <span className="chip font-mono">{project.board}</span>
          <span className="chip">{String(project.cycleMonth).padStart(2, "0")}/{project.cycleYear}</span>
        </div>
        <h3 className="font-display font-bold text-xl md:text-2xl">{project.title}</h3>
        <p className="mt-3 text-cool leading-relaxed text-sm">{project.description}</p>
        {project.componentsPreview?.length > 0 && (
          <ul className="mt-4 font-mono text-xs text-cool space-y-1">
            {project.componentsPreview.slice(0, 5).map((c) => <li key={c}>{`> ${c}`}</li>)}
          </ul>
        )}
        <div className="mt-6 flex flex-wrap gap-3">
          <Link to={`/apps/makerbox/projects/${project.slug}`} className="btn-primary text-sm py-2 px-4">
            View guide <ArrowRight size={14} strokeWidth={1.5} />
          </Link>
          {project.githubUrl && (
            <a href={project.githubUrl} target="_blank" rel="noreferrer" className="btn-ghost text-sm py-2 px-4">
              <Github size={14} strokeWidth={1.5} /> GitHub
            </a>
          )}
        </div>
      </div>
    </article>
  );
}

function CommunityVote({ voteCycle }) {
  const { mode } = useUIMode();
  return (
    <section className="py-20 border-b border-[#30363D]">
      <div className="container">
        <span className="section-label">// COMMUNITY VOTE</span>
        <h2 className="mt-3 font-display text-3xl md:text-4xl font-bold">You pick what we build next.</h2>
        {!voteCycle ? (
          <div className="card p-10 mt-10 text-center" data-testid="vote-empty">
            <p className="text-cool">
              {mode === "live" ? "The first community vote opens after launch. Subscribe to get a vote each month." : "Voting opens once we launch. Join the waitlist to get a vote your first month."}
            </p>
          </div>
        ) : (
          <div className="mt-10 grid md:grid-cols-3 gap-6">
            {(voteCycle.candidates || []).map((c) => (
              <VoteCard key={c.id} candidate={c} totalVotes={voteCycle.totalVotes || 0} count={voteCycle.results?.[c.id] || 0} />
            ))}
            {(!voteCycle.candidates || voteCycle.candidates.length === 0) && (
              <div className="md:col-span-3 card p-8 text-center text-cool">Candidates being curated.</div>
            )}
          </div>
        )}
        <div className="mt-6 text-right">
          <Link to="/apps/makerbox/vote" className="text-circuit text-sm hover:underline inline-flex items-center gap-1">
            Go to vote page <ArrowRight size={14} strokeWidth={1.5} />
          </Link>
        </div>
      </div>
    </section>
  );
}

function VoteCard({ candidate, totalVotes, count }) {
  const pct = totalVotes > 0 ? Math.round((count / totalVotes) * 100) : 0;
  return (
    <div className="card p-6" data-testid={`vote-card-${candidate.slug}`}>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="chip chip-orange">{candidate.difficulty}</span>
        <span className="chip font-mono">{candidate.board}</span>
      </div>
      <h3 className="mt-4 font-display font-bold text-lg">{candidate.title}</h3>
      <p className="mt-2 text-sm text-cool line-clamp-3">{candidate.description}</p>
      <div className="mt-5">
        <div className="trace-progress"><span style={{ width: `${pct}%` }} /></div>
        <div className="mt-2 flex justify-between font-mono text-xs text-cool">
          <span>{pct}%</span><span>{count} votes</span>
        </div>
      </div>
    </div>
  );
}

function PastProjectsRow({ projects }) {
  // Always render at least 5 placeholder slots for upcoming projects.
  const placeholders = Math.max(0, 5 - projects.length);
  return (
    <section className="py-20 border-b border-[#30363D]">
      <div className="container">
        <span className="section-label">// ARCHIVE</span>
        <div className="mt-3 flex items-end justify-between flex-wrap gap-3">
          <h2 className="font-display text-3xl md:text-4xl font-bold">Past projects</h2>
          <p className="text-cool text-sm">Subscribers can substitute the current kit for any of the last 6.</p>
        </div>
        <div className="scroll-row mt-10" data-testid="past-projects-row">
          {projects.map((p) => (
            <div key={p.id} className="w-80"><ProjectCard project={p} /></div>
          ))}
          {Array.from({ length: placeholders }).map((_, i) => (
            <div key={`placeholder-${i}`} className="w-80"><WaitingSlot index={i} /></div>
          ))}
        </div>
      </div>
    </section>
  );
}

function WaitingSlot({ index }) {
  return (
    <article
      className="card p-6 flex flex-col items-center justify-center text-center min-h-[300px] border-dashed"
      data-testid={`past-project-waiting-${index}`}
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

function OpenSource() {
  return (
    <section className="py-20 border-b border-[#30363D]">
      <div className="container grid md:grid-cols-2 gap-12 items-center">
        <div>
          <span className="section-label">// OPEN SOURCE</span>
          <h2 className="mt-3 font-display text-3xl md:text-4xl font-bold">Every project, free to fork.</h2>
          <p className="mt-4 text-cool leading-relaxed">
            All schematics, firmware, and BOMs are published on GitHub under MIT or CC BY-SA. Read, build, modify, ship.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a href="https://github.com/Toasterfire-come/DropKit-Projects" target="_blank" rel="noreferrer" className="btn-primary">
              <Github size={16} strokeWidth={1.5} /> View GitHub
            </a>
            <a href="https://discord.gg/QZgJssxK" target="_blank" rel="noreferrer" className="btn-ghost">
              <MessageCircle size={16} strokeWidth={1.5} /> Join Discord
            </a>
          </div>
        </div>
        <div className="card p-8 font-mono text-sm leading-relaxed">
          <div className="text-cool">$ git clone <span className="text-warm">github.com/Toasterfire-come/<span className="text-circuit">SafeKeyVault</span></span></div>
          <div className="text-cool">$ cd SafeKeyVault && make flash</div>
          <div className="text-flux">→ flashed in 2.4s · all good</div>
          <div className="mt-6 pt-6 border-t border-[#30363D] flex justify-between text-xs text-cool">
            <span>LICENSE: <span className="text-warm">MIT / CC BY-SA</span></span>
            <span className="inline-flex items-center gap-1.5"><Zap size={12} strokeWidth={1.5} className="text-circuit" /> 100% open</span>
          </div>
        </div>
      </div>
    </section>
  );
}

function Testimonials_REMOVED() { return null; }

function FAQSection() {
  const [faq, setFaq] = useState([]);
  const [open, setOpen] = useState(0);

  useEffect(() => { api.get("/faq").then((r) => setFaq(r.data)); }, []);

  return (
    <section className="py-20">
      <div className="container max-w-3xl">
        <span className="section-label">// FAQ</span>
        <h2 className="mt-3 font-display text-3xl md:text-4xl font-bold">Common questions</h2>
        <ul className="mt-10 space-y-3" data-testid="faq-list">
          {faq.map((item, i) => {
            const isOpen = open === i;
            return (
              <li key={i} className="card overflow-hidden" data-testid={`faq-item-${i}`}>
                <button onClick={() => setOpen(isOpen ? -1 : i)} className="w-full flex items-center justify-between p-5 text-left transition-colors" data-testid={`faq-toggle-${i}`}>
                  <span className="font-medium">{item.q}</span>
                  <ChevronDown size={18} strokeWidth={1.5} className={`text-cool transition-transform duration-300 ${isOpen ? "rotate-180 text-circuit" : ""}`} />
                </button>
                <div className={`overflow-hidden transition-all duration-300 ${isOpen ? "max-h-96" : "max-h-0"}`}>
                  <p className="px-5 pb-5 text-cool leading-relaxed text-sm">{item.a}</p>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </section>
  );
}

/* ---------------------------------------- Sponsor Banner */
function SponsorBanner() {
  // Hard-coded at $0 — update manually when sponsorship is secured
  const progress = 0;
  const targetAmount = 2000;
  const progressPercentage = (progress / targetAmount) * 100;

  return (
    <section className="bg-[#161B22] py-6 border-b border-[#30363D] text-center" data-testid="sponsor-banner">
      <div className="container">
        <div className="mb-4">
          <span className="font-display font-bold text-xl md:text-2xl">Sponsors & Partners Go Here</span>
        </div>
        <div className="relative h-12 w-full max-w-3xl mx-auto mb-4 rounded-full overflow-hidden bg-graphite">
          <div
            className="h-full bg-circuit transition-all duration-700 ease-out"
            style={{ width: `${progressPercentage}%` }}
            data-testid="sponsor-progress-bar"
          ></div>
          <span className="absolute inset-0 flex items-center justify-center text-sm font-bold text-white" data-testid="sponsor-progress-text">
            $0 / $2000
          </span>
        </div>
        <div className="max-w-3xl mx-auto text-left space-y-2 text-sm text-cool">
          <p className="font-mono text-xs uppercase tracking-widest text-warm">// FUNDING INFO</p>
          <p>
            We are <strong className="text-warm">not raising money from our community</strong> — only through
            sponsorships and partnerships. This <strong className="text-warm">$2,000 goal</strong> will go toward
            3D printers, camera equipment, packaging, and official business registration.
          </p>
          <p>
            Once we reach our goal, we will open pre-orders to the waitlist.
          </p>
        </div>
      </div>
    </section>
  );
}
