// Tiny helper to read/store the referral code across the app.
const KEY = "dropkit_ref";        // who referred ME (for attribution)
const SRC_KEY = "dropkit_ref_src";
const MY_CODE_KEY = "dropkit_my_code"; // MY OWN code after I joined the waitlist

export function captureRefFromUrl() {
  if (typeof window === "undefined") return null;
  try {
    const params = new URLSearchParams(window.location.search);
    const r = params.get("ref");
    const s = params.get("src");
    if (r && /^[A-Z0-9]{4,12}$/i.test(r.trim())) {
      const code = r.trim().toUpperCase();
      localStorage.setItem(KEY, code);
      if (s && /^[a-z0-9_-]{1,16}$/i.test(s.trim())) {
        localStorage.setItem(SRC_KEY, s.trim().toLowerCase());
      }
      return code;
    }
  } catch {
    /* ignore */
  }
  return localStorage.getItem(KEY);
}

export function getRef() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(KEY);
}

export function getRefSrc() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(SRC_KEY);
}

export function buildShareUrl(code) {
  if (typeof window === "undefined") return `?ref=${code}`;
  const origin = window.location.origin;
  return `${origin}/?ref=${code}`;
}

export function rememberMyCode(code) {
  if (typeof window === "undefined" || !code) return;
  try {
    localStorage.setItem(MY_CODE_KEY, code);
    window.dispatchEvent(new CustomEvent("dropkit:waitlist-joined", { detail: { code } }));
  } catch { /* ignore */ }
}

export function getMyCode() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(MY_CODE_KEY);
}

export function forgetMyCode() {
  if (typeof window === "undefined") return;
  try { localStorage.removeItem(MY_CODE_KEY); } catch { /* ignore */ }
}
