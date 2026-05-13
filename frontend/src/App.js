import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, UIModeProvider, useAuth } from "./lib/contexts";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Vote from "./pages/Vote";
import ProjectCatalog from "./pages/ProjectCatalog";
import ProjectDetail from "./pages/ProjectDetail";
import Account from "./pages/Account";
import FAQ from "./pages/FAQ";
import About from "./pages/About";
import Subscribe from "./pages/Subscribe";
import BuyGift from "./pages/BuyGift";
import SignIn from "./pages/SignIn";
import SignUp from "./pages/SignUp";
import Dev from "./pages/Dev";
import NotFound from "./pages/NotFound";
import ReferralStatus from "./pages/ReferralStatus";
import Leaderboard from "./pages/Leaderboard";
import ReplacementRequest from "./pages/ReplacementRequest";
import { captureRefFromUrl } from "./lib/referral";

function Protected({ children, role }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/signin" replace />;
  if (role && user.role !== role) return <Navigate to="/" replace />;
  return children;
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
              <Route path="leaderboard" element={<Leaderboard />} />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </UIModeProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
