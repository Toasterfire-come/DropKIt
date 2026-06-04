import React, { useEffect, useState, useCallback } from "react";
import api, { formatApiError } from "../lib/api";
import { toast } from "sonner";
import { Pause, Play, SkipForward, ExternalLink, Gift, LogOut, MapPin } from "lucide-react";
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

const STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"];

function StatusBadge({ status }) {
  const colors = {
    active: "bg-flux/20 text-flux border-flux/40",
    paused: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
    cancelled: "bg-red-500/20 text-red-400 border-red-500/40",
    inactive: "bg-cool/20 text-cool border-cool/40",
  };
  return (
    <span className={`chip ${colors[status] || colors.inactive}`}>
      {status ? status.charAt(0).toUpperCase() + status.slice(1) : "Inactive"}
    </span>
  );
}

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

  // Subscription state
  const [sub, setSub] = useState(null);
  const [subLoading, setSubLoading] = useState(false);
  const [showAddressForm, setShowAddressForm] = useState(false);
  const [addr, setAddr] = useState({ street1: "", street2: "", city: "", state: "CA", zip: "", phone: "" });

  const loadSubscription = useCallback(async () => {
    try {
      const r = await api.get("/subscription");
      setSub(r.data);
      if (r.data?.shipping_address) {
        setAddr(r.data.shipping_address);
      }
    } catch {
      // Not subscribed — that's fine
    }
  }, []);

  useEffect(() => {
    if (!user) {
      navigate("/sign-in");
      return;
    }
    setName(user.name || "");
    setEmail(user.email || "");
    setLoading(false);
    api.get("/orders").then((r) => setOrders(r.data));
    loadSubscription();
  }, [user, navigate, loadSubscription]);

  const save = async () => {
    if (!name || !email) return;
    try {
      const r = await api.patch("/users/me", { name, email });
      toast.success("Profile updated.");
      await login(email, password || r.data.password);
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

  // ── Subscription actions ──
  const subAction = async (action, label) => {
    setSubLoading(true);
    try {
      const r = await api.post(`/subscription/${action}`);
      setSub((prev) => ({ ...prev, status: r.data.status }));
      toast.success(`Subscription ${label}.`);
      loadSubscription();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSubLoading(false);
    }
  };

  const saveAddress = async (e) => {
    e.preventDefault();
    setSubLoading(true);
    try {
      const r = await api.put("/subscription/address", addr);
      setSub((prev) => ({ ...prev, shipping_address: r.data.shipping_address }));
      toast.success("Shipping address updated.");
      setShowAddressForm(false);
      loadSubscription();
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSubLoading(false);
    }
  };

  if (loading) return <div className="container py-16">Loading...</div>;

  return (
    <section className="container py-16">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          {/* ── Profile ── */}
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

          {/* ── Subscription ── */}
          {sub && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Subscription</CardTitle>
                  <StatusBadge status={sub.status} />
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-cool">Plan</span>
                    <p className="font-semibold">{sub.plan}</p>
                  </div>
                  <div>
                    <span className="text-cool">Price</span>
                    <p className="font-semibold">${(sub.price_cents / 100).toFixed(2)}/mo</p>
                  </div>
                  {sub.next_billing_date && (
                    <div>
                      <span className="text-cool">Next billing</span>
                      <p className="font-semibold">{new Date(sub.next_billing_date).toLocaleDateString()}</p>
                    </div>
                  )}
                  {sub.stripe_customer_id && (
                    <div>
                      <span className="text-cool">Payment</span>
                      <p className="font-semibold text-flux">Stripe connected</p>
                    </div>
                  )}
                </div>

                {/* Shipping address */}
                <Separator />
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-semibold flex items-center gap-2">
                      <MapPin size={14} className="text-cool" /> Shipping Address
                    </span>
                    <Button variant="ghost" size="sm" onClick={() => setShowAddressForm(!showAddressForm)}>
                      {showAddressForm ? "Cancel" : "Edit"}
                    </Button>
                  </div>
                  {showAddressForm ? (
                    <form onSubmit={saveAddress} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div className="sm:col-span-2">
                        <Label>Street</Label>
                        <Input value={addr.street1} onChange={(e) => setAddr({...addr, street1: e.target.value})} required className="mt-1" />
                      </div>
                      <div className="sm:col-span-2">
                        <Label>Apt / Suite</Label>
                        <Input value={addr.street2} onChange={(e) => setAddr({...addr, street2: e.target.value})} className="mt-1" />
                      </div>
                      <div>
                        <Label>City</Label>
                        <Input value={addr.city} onChange={(e) => setAddr({...addr, city: e.target.value})} required className="mt-1" />
                      </div>
                      <div>
                        <Label>State</Label>
                        <select value={addr.state} onChange={(e) => setAddr({...addr, state: e.target.value})} className="input mt-1">
                          {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                        </select>
                      </div>
                      <div>
                        <Label>ZIP</Label>
                        <Input value={addr.zip} onChange={(e) => setAddr({...addr, zip: e.target.value})} required className="mt-1" />
                      </div>
                      <div>
                        <Label>Phone</Label>
                        <Input value={addr.phone} onChange={(e) => setAddr({...addr, phone: e.target.value})} className="mt-1" />
                      </div>
                      <div className="sm:col-span-2 flex justify-end">
                        <Button type="submit" disabled={subLoading}>Save Address</Button>
                      </div>
                    </form>
                  ) : sub.shipping_address ? (
                    <p className="text-sm text-cool">
                      {sub.shipping_address.street1}
                      {sub.shipping_address.street2 ? `, ${sub.shipping_address.street2}` : ""}
                      <br />
                      {sub.shipping_address.city}, {sub.shipping_address.state} {sub.shipping_address.zip}
                    </p>
                  ) : (
                    <p className="text-sm text-cool">No shipping address set.</p>
                  )}
                </div>

                {/* Action buttons */}
                <Separator />
                <div className="flex flex-wrap gap-2">
                  {sub.status === "active" && (
                    <Button variant="outline" size="sm" disabled={subLoading}
                      onClick={() => subAction("pause", "paused")}>
                      <Pause size={14} className="mr-1" /> Pause
                    </Button>
                  )}
                  {sub.status === "paused" && (
                    <Button variant="outline" size="sm" disabled={subLoading}
                      onClick={() => subAction("resume", "resumed")}>
                      <Play size={14} className="mr-1" /> Resume
                    </Button>
                  )}
                  {(sub.status === "active" || sub.status === "paused") && (
                    <Button variant="outline" size="sm" disabled={subLoading}
                      onClick={() => subAction("cancel", "cancelled")}
                      className="text-red-400 border-red-400/30 hover:bg-red-500/10">
                      <SkipForward size={14} className="mr-1" /> Cancel at period end
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* ── Orders ── */}
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
                        <TableCell className="font-medium">{order.id.slice(0, 8)}...</TableCell>
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