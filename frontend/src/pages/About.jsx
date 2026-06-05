import React from "react";
import { Link } from "react-router-dom";
import { Cpu, Heart, Zap, Github } from "../lib/icons";
import { useDocMeta } from "../lib/useDocMeta";

export default function About() {
  useDocMeta({
    title: "About DropKit — Open hardware, built by makers",
    description: "DropKit ships a curated open-source electronics project every month. MIT and CC BY-SA, US-only, no markup tricks. Built by makers for makers.",
  });
  return (
    <section className="container py-16">
      <span className="section-label">// ABOUT</span>
      <h1 className="mt-3 font-display text-4xl md:text-6xl font-bold leading-tight">
        Built by makers,<br />
        <span className="text-circuit">for makers.</span>
      </h1>
      <p className="mt-6 text-cool text-lg max-w-2xl leading-relaxed">
        DropKit is a monthly hardware subscription for adult electronics enthusiasts. Every kit is a
        complete, open-source project — board, components, guide, code — designed to be built,
        modified, and remixed. No black boxes. No paywalls on the software.
      </p>

      <div className="mt-16 grid md:grid-cols-3 gap-6">
        <Pillar icon={Cpu} title="Technical, not toyish" body="Intermediate-to-advanced projects with real microcontrollers (ESP32, RP2040, Arduino R4) — not glue-and-stickers. You'll write code, solder, and debug." />
        <Pillar icon={Heart} title="Community-curated" body="Each month, subscribers vote on what we build next. The roadmap is collaborative by default — you build what you wanted." />
        <Pillar icon={Zap} title="Open source forever" body="Every project's firmware, schematic, and BOM lives on GitHub under MIT or CC BY-SA. Fork it, ship it, sell it. We're proud when you do." />
      </div>

      <div className="mt-20 card p-10 md:p-14 grid md:grid-cols-2 gap-8 items-center">
        <div>
          <h2 className="font-display text-2xl md:text-3xl font-bold">The honest version</h2>
          <p className="mt-4 text-cool leading-relaxed">
            We started DropKit because every existing subscription box was either for kids,
            paywalled the firmware, or shipped a junk-drawer of unconnected parts. We wanted the
            opposite: one focused project, real components, working code, and a community of people
            who'd geek out about pin-outs at midnight. That's it. That's the pitch.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a href="https://github.com/Toasterfire-come/DropKit-Projects" target="_blank" rel="noreferrer" className="btn-primary text-sm py-2 px-4">
              <Github size={14} strokeWidth={1.5} /> See our work
            </a>
            <Link to="/pages/faq" className="btn-ghost text-sm py-2 px-4">Read the FAQ</Link>
          </div>
        </div>
        <ul className="font-mono text-sm space-y-3 text-cool" data-testid="about-stats">
          <li><span className="text-circuit">$40</span> /mo + shipping</li>
          <li><span className="text-circuit">US</span> only at MVP</li>
          <li><span className="text-circuit">1</span> project per month</li>
          <li><span className="text-circuit">100%</span> open-source firmware</li>
          <li><span className="text-circuit">MIT / CC BY-SA</span> licenses</li>
          <li><span className="text-circuit">7-day</span> community voting window</li>
        </ul>
      </div>
    </section>
  );
}

function Pillar({ icon: Icon, title, body }) {
  return (
    <div className="card p-6">
      <Icon size={24} strokeWidth={1.5} className="text-circuit" />
      <h3 className="mt-4 font-display font-bold text-lg">{title}</h3>
      <p className="mt-2 text-sm text-cool leading-relaxed">{body}</p>
    </div>
  );
}
