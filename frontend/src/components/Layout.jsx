import React, { useEffect, useState } from "react";
import { Outlet, Link, NavLink, useNavigate } from "react-router-dom";
import { Cpu, Github, Instagram, Youtube, LogOut, User, Settings, Share2 } from "lucide-react";
import { useAuth, useUIMode } from "../lib/contexts";
import WaitlistModal from "./WaitlistModal";
import { getMyCode } from "../lib/referral";

export default function Layout() {
  const [waitlistOpen, setWaitlistOpen] = useState(false);
  return (
    <div className="min-h-screen flex flex-col bg-pcb text-warm">
      <Header onOpenWaitlist={() => setWaitlistOpen(true)} />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
      <WaitlistModal open={waitlistOpen} onClose={() => setWaitlistOpen(false)} />
    </div>
  );
}

function Header({ onOpenWaitlist }) {
  const { user, logout } = useAuth();
  const { mode } = useUIMode();
  const [menuOpen, setMenuOpen] = useState(false);
  const [myCode, setMyCode] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    setMyCode(getMyCode());
    // Listen for storage changes so the pill appears as soon as a join happens
    const sync = () => setMyCode(getMyCode());
    window.addEventListener("storage", sync);
    window.addEventListener("dropkit:waitlist-joined", sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("dropkit:waitlist-joined", sync);
    };
  }, []);

  const navItems = [
    { to: "/apps/makerbox/projects", label: "Projects" },
    { to: "/apps/makerbox/vote", label: "Vote" },
    { to: "/about", label: "About" },
    { to: "/pages/faq", label: "FAQ" },
  ];

  return (
    <header className="sticky top-0 z-40 border-b border-[#30363D] bg-pcb/85 backdrop-blur-md">
      <div className="container flex items-center justify-between h-16">
        <Link to="/" className="flex items-center gap-2.5 font-display font-bold text-xl tracking-tight" data-testid="header-logo">
          <Cpu size={22} strokeWidth={1.5} className="text-circuit" />
          <span>Drop<span className="text-circuit">Kit</span></span>
        </Link>

        <nav className="hidden md:flex items-center gap-7">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              data-testid={`nav-${item.label.toLowerCase().replace(/ /g, "-")}`}
              className={({ isActive }) =>
                `text-sm tracking-wide transition-colors duration-150 ${
                  isActive ? "text-circuit" : "text-cool hover:text-warm"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          {user ? (
            <div className="relative">
              <button
                onClick={() => setMenuOpen((o) => !o)}
                data-testid="header-user-menu-btn"
                className="flex items-center gap-2 text-sm text-warm hover:text-circuit transition-colors px-3 py-2"
              >
                <User size={16} strokeWidth={1.5} />
                <span className="hidden sm:inline max-w-[140px] truncate">{user.email}</span>
                {user.role === "dev" && <span className="chip chip-orange !py-0.5 !text-[0.6rem]">DEV</span>}
              </button>
              {menuOpen && (
                <div
                  className="absolute right-0 mt-2 w-56 card !rounded-sm p-2 z-50"
                  onClick={() => setMenuOpen(false)}
                  data-testid="header-user-menu"
                >
                  <Link to="/account" className="block px-3 py-2 text-sm hover:bg-graphite text-warm" data-testid="menu-account">
                    Account
                  </Link>
                  {user.role === "dev" && (
                    <Link to="/dev" className="block px-3 py-2 text-sm hover:bg-graphite text-warm inline-flex items-center gap-2 w-full" data-testid="menu-dev">
                      <Settings size={14} strokeWidth={1.5} /> Dev panel
                    </Link>
                  )}
                  <button
                    onClick={async () => {
                      await logout();
                      navigate("/");
                    }}
                    className="block w-full text-left px-3 py-2 text-sm hover:bg-graphite text-warm"
                    data-testid="menu-logout"
                  >
                    <span className="inline-flex items-center gap-2"><LogOut size={14} strokeWidth={1.5} /> Sign out</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              {mode === "waitlist" ? (
                myCode ? (
                  <button
                    onClick={onOpenWaitlist}
                    className="btn-primary text-sm py-2 px-4 inline-flex items-center gap-1.5"
                    data-testid="header-my-share-link"
                    title={`Your code: ${myCode}`}
                  >
                    <Share2 size={14} strokeWidth={1.5} /> My share link
                  </button>
                ) : (
                  <button
                    onClick={onOpenWaitlist}
                    className="btn-primary text-sm py-2 px-4"
                    data-testid="header-join-waitlist"
                  >
                    Join Waitlist
                  </button>
                )
              ) : (
                <Link to="/subscribe" className="btn-primary text-sm py-2 px-4" data-testid="header-subscribe-btn">
                  Subscribe
                </Link>
              )}
            </>
          )}
          {mode === "live" && user && (
            <Link to="/subscribe" className="hidden lg:inline-flex btn-ghost text-sm py-2 px-4" data-testid="header-subscribe-link">
              Subscribe
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

function Footer() {
  const { mode } = useUIMode();
  return (
    <footer className="border-t border-[#30363D] mt-24">
      <div className="container py-14 grid md:grid-cols-4 gap-10">
        <div className="md:col-span-2">
          <Link to="/" className="flex items-center gap-2 font-display font-bold text-lg">
            <Cpu size={20} strokeWidth={1.5} className="text-circuit" />
            Drop<span className="text-circuit">Kit</span>
          </Link>
          <p className="mt-4 text-cool max-w-md leading-relaxed text-sm">
            Open-source hardware projects, delivered monthly. Built by makers, for makers.
          </p>
          <FooterNewsletter />
        </div>
        <FooterCol
          title="Product"
          links={[
            { to: "/apps/makerbox/projects", label: "Projects" },
            { to: "/apps/makerbox/vote", label: "Community Vote" },
            ...(mode === "live" ? [{ to: "/subscribe", label: "Subscribe" }, { to: "/gift", label: "Buy a gift" }] : []),
            { to: "/about", label: "About" },
          ]}
        />
        <FooterCol
          title="Community"
          links={[
            { to: "/leaderboard", label: "Leaderboard" },
            { href: "https://github.com/Toasterfire-come/DropKit-Projects", label: "GitHub", external: true, icon: Github },
            { href: "https://discord.gg/QZgJssxK", label: "Discord", external: true },
            { href: "https://www.instagram.com/dropkit.marketing/", label: "Instagram", external: true, icon: Instagram },
            { href: "https://www.tiktok.com/@dropkitmarketing", label: "TikTok", external: true },
            { href: "https://www.youtube.com/@DropKit-marketing", label: "YouTube", external: true, icon: Youtube },
            { to: "/pages/faq", label: "FAQ" },
            { to: "/help/replacement", label: "Damaged or missing?" },
          ]}
        />
      </div>
      <div className="border-t border-[#30363D]">
        <div className="container py-6 flex flex-col md:flex-row items-center justify-between text-xs text-cool gap-3">
          <span className="font-mono">© {new Date().getFullYear()} DROPKIT · MIT / CC BY-SA</span>
          <div className="flex gap-5">
            <a href="/policies/terms-of-service" className="hover:text-warm transition-colors">Terms</a>
            <a href="/policies/privacy-policy" className="hover:text-warm transition-colors">Privacy</a>
            <a href="https://github.com/Toasterfire-come/DropKit-Projects" target="_blank" rel="noreferrer" className="hover:text-warm transition-colors inline-flex items-center gap-1">
              <Github size={14} strokeWidth={1.5} /> Source
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}

function FooterCol({ title, links }) {
  return (
    <div>
      <h4 className="font-mono uppercase tracking-widest text-xs text-circuit mb-4">{title}</h4>
      <ul className="space-y-2.5 text-sm">
        {links.map((l) => {
          const Inner = (
            <span className="inline-flex items-center gap-1.5">
              {l.icon ? <l.icon size={13} strokeWidth={1.5} /> : null}
              {l.label}
            </span>
          );
          return l.external ? (
            <li key={l.label}>
              <a href={l.href} target="_blank" rel="noreferrer" className="text-cool hover:text-warm transition-colors">
                {Inner}
              </a>
            </li>
          ) : (
            <li key={l.label}>
              <Link to={l.to} className="text-cool hover:text-warm transition-colors">{Inner}</Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function FooterNewsletter() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [refCode, setRefCode] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!email || !name) return;
    setSubmitting(true);
    try {
      const { default: api } = await import("../lib/api");
      const ref = (typeof window !== "undefined" && localStorage.getItem("dropkit_ref")) || undefined;
      const refSrc = (typeof window !== "undefined" && localStorage.getItem("dropkit_ref_src")) || undefined;
      const r = await api.post("/waitlist", { name, email, source: "footer", ref, ref_src: refSrc });
      const { rememberMyCode } = await import("../lib/referral");
      rememberMyCode(r.data.referralCode);
      setRefCode(r.data.referralCode);
    } catch {
      // ignore — keep UX gentle in footer
    } finally {
      setSubmitting(false);
    }
  };

  if (refCode) {
    return (
      <div className="mt-6 max-w-sm" data-testid="footer-newsletter-success">
        <ReferralSuccessLazy code={refCode} compact />
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="mt-6 space-y-2 max-w-sm" data-testid="footer-newsletter-form">
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Your name"
        required
        minLength={1}
        maxLength={120}
        className="input text-sm"
        data-testid="footer-newsletter-name"
      />
      <div className="flex gap-2">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@workbench.dev"
          required
          className="input text-sm"
          data-testid="footer-newsletter-input"
        />
        <button type="submit" disabled={submitting} className="btn-primary text-sm py-2 px-4 whitespace-nowrap" data-testid="footer-newsletter-btn">
          {submitting ? "…" : "Join"}
        </button>
      </div>
    </form>
  );
}

// Lazy import to avoid making Layout a hub for ReferralSuccess on initial render.
const ReferralSuccessLazy = React.lazy(() => import("./ReferralSuccess"));
