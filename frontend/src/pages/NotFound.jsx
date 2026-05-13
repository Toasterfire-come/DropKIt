import React from "react";
import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section className="container py-24 text-center">
      <span className="font-mono text-circuit text-sm">// 404</span>
      <h1 className="mt-4 font-display text-5xl font-bold">Trace not found</h1>
      <p className="mt-4 text-cool">That route has no continuity to ground.</p>
      <Link to="/" className="btn-primary mt-8 inline-flex">
        Return home
      </Link>
    </section>
  );
}
