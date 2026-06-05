import React, { useEffect, useState } from "react";
import { useDocMeta } from "../lib/useDocMeta";
import api from "../lib/api";
import { ChevronDown } from "../lib/icons";

export default function FAQ() {
  useDocMeta({ title: "Frequently asked — DropKit", description: "Subscription, shipping, refunds, project sourcing, and open-source license details for DropKit's monthly hardware project box." });
  const [faq, setFaq] = useState([]);
  const [open, setOpen] = useState(0);

  useEffect(() => {
    api.get("/faq").then((r) => setFaq(r.data));
  }, []);

  return (
    <section className="container py-16 max-w-3xl">
      <span className="section-label">// FAQ</span>
      <h1 className="mt-3 font-display text-4xl md:text-5xl font-bold">Frequently asked</h1>
      <ul className="mt-10 space-y-3">
        {faq.map((item, i) => {
          const isOpen = open === i;
          return (
            <li key={i} className="card overflow-hidden">
              <button onClick={() => setOpen(isOpen ? -1 : i)} className="w-full flex items-center justify-between p-5 text-left">
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
    </section>
  );
}
