import React, { useEffect, useState } from "react";
import api, { formatApiError } from "../lib/api";
import { toast } from "sonner";
import { Pause, Play, SkipForward, ExternalLink, Gift, LogOut } from "lucide-react";
import { useAuth } from "../lib/contexts";
import { useNavigate, Link } from "react-router-dom";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Separator } from "../components/ui/separator";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { cn } from "../lib/utils";

export default function Account() {
  const { user, login, logout } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(user?.name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [orders, setOrders] = useState([]);

  useEffect(() => {
    if (!user) {
      navigate("/sign-in");
      return;
    }
    setName(user.name || "");
    setEmail(user.email || "");
    setLoading(false);
    api.get("/orders").then((r) => setOrders(r.data));
  }, [user, navigate]);

  const save = async () => {
    if (!name || !email) return;
    try {
      const r = await api.patch("/users/me", { name, email });
      toast.success("Profile updated.");
      // Re-login to refresh session
      await login(email, password || r.data.password); // Use new password if changed, else old one
      setEditing(false);
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const changePassword = async () => {
    if (!password || !passwordConfirm) return;
    if (password !== passwordConfirm) {
      toast.error("Passwords do not match.");
      return;
    }
    try {
      await api.patch("/users/me/password", { password });
      toast.success("Password updated.");
      setPassword("");
      setPasswordConfirm("");
      // Re-login to refresh session
      await login(email, password);
    } catch (err) {
      toast.error(formatApiError(err));
    }
  };

  const handleLogout = async () => {
    await logout();
    toast.success("Signed out.");
    navigate("/sign-in");
  };

  if (loading) return <div className="container py-16">Loading...</div>;

  return (
    <section className="container py-16">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Account Details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    disabled={!editing}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={!editing}
                    className="mt-1"
                  />
                </div>
              </div>

              {editing && (
                <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="password">New Password</Label>
                    <Input
                      id="password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="passwordConfirm">Confirm New Password</Label>
                    <Input
                      id="passwordConfirm"
                      type="password"
                      value={passwordConfirm}
                      onChange={(e) => setPasswordConfirm(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                </div>
              )}

              <div className="mt-6 flex justify-end gap-2">
                {!editing ? (
                  <Button variant="outline" onClick={() => setEditing(true)}>
                    Edit Profile
                  </Button>
                ) : (
                  <>
                    <Button variant="outline" onClick={() => setEditing(false)}>
                      Cancel
                    </Button>
                    <Button onClick={save} disabled={!name || !email}>
                      Save Changes
                    </Button>
                  </>
                )}
              </div>
            </CardContent>
          </Card>

          <Separator className="my-8" />

          <Card>
            <CardHeader>
              <CardTitle>Order History</CardTitle>
            </CardHeader>
            <CardContent>
              {orders.length === 0 ? (
                <p className="text-cool">You haven't placed any orders yet.</p>
              ) : (
                <Table>
                  <TableCaption>A list of your recent orders.</TableCaption>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Order ID</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Total</TableHead>
                      <TableHead className="text-right">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {orders.map((order) => (
                      <TableRow key={order.id}>
                        <TableCell className="font-medium">{order.id}</TableCell>
                        <TableCell>{new Date(order.created_at).toLocaleDateString()}</TableCell>
                        <TableCell>${(order.total_price / 100).toFixed(2)}</TableCell>
                        <TableCell className="text-right">{order.status}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-8">
          <Card>
            <CardHeader>
              <CardTitle>Referral</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p>Share your referral code to get rewards!</p>
              <div className="flex items-center gap-2">
                <Input
                  readOnly
                  value={user?.referral_code || "N/A"}
                  className="font-mono text-center"
                />
                <Button
                  variant="secondary"
                  onClick={() => {
                    navigator.clipboard.writeText(user?.referral_code || "");
                    toast.success("Referral code copied!");
                  }}
                  disabled={!user?.referral_code}
                >
                  Copy
                </Button>
              </div>
              <Button asChild className="w-full">
                <Link to="/referral-status">
                  <Gift className="mr-2 h-4 w-4" />
                  View Referral Status
                </Link>
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {editing && (
                <Button variant="outline" className="w-full" onClick={changePassword}>
                  Save New Password
                </Button>
              )}
              <Button variant="outline" className="w-full" onClick={handleLogout}>
                <LogOut className="mr-2 h-4 w-4" />
                Log Out
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}
