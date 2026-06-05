import React, { Suspense, lazy, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, UIModeProvider, useAuth } from "./lib/contexts";
import { captureRefFromUrl } from "./lib/referral";

// ── Route-level code splitting ──
// Loaded only when the user navigates to that route, not on initial page load.
const Layout = lazy(() => import("./components/Layout"));
const Home = lazy(() => import("./pages/Home"));
const Vote = lazy(() => import("./pages/Vote"));
const ProjectCatalog = lazy(() => import("./pages/ProjectCatalog"));
const ProjectDetail = lazy(() => import("./pages/ProjectDetail"));
const Account = lazy(() => import("./pages/Account"));
const FAQ = lazy(() => import("./pages/FAQ"));
const About = lazy(() => import("./pages/About"));
const Subscribe = lazy(() => import("./pages/Subscribe"));
const BuyGift = lazy(() => import("./pages/BuyGift"));
const SignIn = lazy(() => import("./pages/SignIn"));
const SignUp = lazy(() => import("./pages/SignUp"));
const Dev = lazy(() => import("./pages/Dev"));
const NotFound = lazy(() => import("./pages/NotFound"));
const ReferralStatus = lazy(() => import("./pages/ReferralStatus"));
const Leaderboard = lazy(() => import("./pages/Leaderboard"));
const ReplacementRequest = lazy(() => import("./pages/ReplacementRequest"));
const TrackOrder = lazy(() => import("./pages/TrackOrder"));

function Protected({ children, role }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/signin" replace />;
  if (role && user.role !== role) return <Navigate to="/" replace />;
  return children;
}

function PageFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-pcb">
      <div className="font-mono text-xs text-cool animate-pulse">loading…</div>
    </div>
  );
}

export default function App() {
  useEffect(() => { captureRefFromUrl(); }, []);
  return (
    <BrowserRouter>
      <AuthProvider>
        <UIModeProvider>
          <Toaster
            theme="dark"
            position="bottom-right"
            toastOptions={{
              style: {
                background: "#161B22",
                border: "1px solid #30363D",
                color: "#F0F0EE",
                borderRadius: "2px",
              },
            }}
          />
          <Suspense fallback={<PageFallback />}>
            <Routes>
              <Route element={<Layout />}>
                <Route index element={<Home />} />
                <Route path="about" element={<About />} />
                <Route path="subscribe" element={<Subscribe />} />
                <Route path="gift" element={<BuyGift />} />
                <Route path="signin" element={<SignIn />} />
                <Route path="signup" element={<SignUp />} />

                <Route path="apps/makerbox/vote" element={<Protected><Vote /></Protected>} />
                <Route path="apps/makerbox/substitute" element={<Navigate to="/apps/makerbox/projects" replace />} />
                <Route path="apps/makerbox/projects" element={<ProjectCatalog />} />
                <Route path="apps/makerbox/projects/:slug" element={<ProjectDetail />} />

                <Route path="account" element={<Protected><Account /></Protected>} />
                <Route path="dev" element={<Protected role="dev"><Dev /></Protected>} />

                <Route path="pages/faq" element={<FAQ />} />
                <Route path="help/replacement" element={<ReplacementRequest />} />
                <Route path="r/:code" element={<ReferralStatus />} />
                <Route path="track/:token" element={<TrackOrder />} />
                <Route path="leaderboard" element={<Leaderboard />} />
                <Route path="*" element={<NotFound />} />
              </Route>
            </Routes>
          </Suspense>
        </UIModeProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}