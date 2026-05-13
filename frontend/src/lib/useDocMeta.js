import { useEffect } from "react";

/**
 * Per-page <title> + meta description for SEO. Updates document.title
 * and the <meta name="description"> tag on mount. Restores on unmount.
 *
 * Usage:
 *   useDocMeta({ title: "About — DropKit", description: "..." });
 */
export function useDocMeta({ title, description } = {}) {
  useEffect(() => {
    const prevTitle = document.title;
    const descEl = document.querySelector('meta[name="description"]');
    const prevDesc = descEl ? descEl.getAttribute("content") : null;
    const ogTitleEl = document.querySelector('meta[property="og:title"]');
    const prevOgTitle = ogTitleEl ? ogTitleEl.getAttribute("content") : null;
    const ogDescEl = document.querySelector('meta[property="og:description"]');
    const prevOgDesc = ogDescEl ? ogDescEl.getAttribute("content") : null;
    const twTitleEl = document.querySelector('meta[name="twitter:title"]');
    const prevTwTitle = twTitleEl ? twTitleEl.getAttribute("content") : null;

    if (title) {
      document.title = title;
      ogTitleEl && ogTitleEl.setAttribute("content", title);
      twTitleEl && twTitleEl.setAttribute("content", title);
    }
    if (description && descEl) {
      descEl.setAttribute("content", description);
      ogDescEl && ogDescEl.setAttribute("content", description);
    }

    return () => {
      document.title = prevTitle;
      if (descEl && prevDesc != null) descEl.setAttribute("content", prevDesc);
      if (ogTitleEl && prevOgTitle != null) ogTitleEl.setAttribute("content", prevOgTitle);
      if (ogDescEl && prevOgDesc != null) ogDescEl.setAttribute("content", prevOgDesc);
      if (twTitleEl && prevTwTitle != null) twTitleEl.setAttribute("content", prevTwTitle);
    };
  }, [title, description]);
}
