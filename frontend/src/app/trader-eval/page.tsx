"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  api,
  type TradingAccount,
  type PayoutReq,
  type RuleViolation,
  type FraudAlertItem,
} from "@/lib/api";

type TabKey = "accounts" | "payouts" | "violations" | "fraud";

export default function TraderEvalPage() {
  const [tab, setTab] = useState<TabKey>("accounts");

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Trader Evaluation</h1>
        <p className="text-zinc-500 text-sm mt-1">Account management, payouts, violations, and fraud monitoring</p>
      </div>
      <Tabs value={tab} onValueChange={(v) => setTab(v as TabKey)}>
        <TabsList className="bg-zinc-900 border border-zinc-800">
          <TabsTrigger value="accounts" className="data-[state=active]:bg-zinc-800 text-xs">Accounts</TabsTrigger>
          <TabsTrigger value="payouts" className="data-[state=active]:bg-zinc-800 text-xs">Payouts</TabsTrigger>
          <TabsTrigger value="violations" className="data-[state=active]:bg-zinc-800 text-xs">Violations</TabsTrigger>
          <TabsTrigger value="fraud" className="data-[state=active]:bg-zinc-800 text-xs">Fraud Alerts</TabsTrigger>
        </TabsList>
      </Tabs>
      {tab === "accounts" && <AccountsTab />}
      {tab === "payouts" && <PayoutsTab />}
      {tab === "violations" && <ViolationsTab />}
      {tab === "fraud" && <FraudTab />}
    </div>
  );
}

// ==================== Accounts ====================
function AccountsTab() {
  const [accounts, setAccounts] = useState<TradingAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const load = () => {
    api.listAccounts().then(setAccounts).catch((e) => setError(e.message)).finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setCreating(true);
    try {
      const f = new FormData(e.currentTarget);
      await api.createAccount({
        user_email: f.get("email") as string,
        account_type: f.get("type") as string,
        plan: f.get("plan") as string,
        starting_balance: Number(f.get("balance")),
      });
      e.currentTarget.reset();
      setDialogOpen(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally { setCreating(false); }
  };

  const statusColor = (s: string) => {
    switch (s) {
      case "active": return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "passed": return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "failed": return "bg-red-500/10 text-red-400 border-red-500/20";
      case "suspended": return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      default: return "border-zinc-700 text-zinc-300";
    }
  };

  return (
    <>
      <div className="flex justify-between items-center">
        <p className="text-sm text-zinc-500">{accounts.length} accounts</p>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger render={<Button />}>New Account</DialogTrigger>
          <DialogContent className="bg-zinc-900 border-zinc-800">
            <DialogHeader><DialogTitle>Create Trading Account</DialogTitle></DialogHeader>
            <form onSubmit={handleCreate} className="space-y-3">
              <Input name="email" type="email" placeholder="Trader email" required className="bg-zinc-800 border-zinc-700" />
              <select name="type" required className="w-full rounded-md bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-zinc-100">
                <option value="challenge">Challenge</option>
                <option value="verification">Verification</option>
                <option value="funded">Funded</option>
              </select>
              <Input name="plan" placeholder="Plan (e.g. 50k_standard)" required className="bg-zinc-800 border-zinc-700" />
              <Input name="balance" type="number" step="0.01" placeholder="Starting balance" required className="bg-zinc-800 border-zinc-700" />
              <Button type="submit" className="w-full" disabled={creating}>{creating ? "Creating..." : "Create"}</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>
      {error && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-transparent">
                <TableHead className="text-zinc-500">Email</TableHead>
                <TableHead className="text-zinc-500">Type</TableHead>
                <TableHead className="text-zinc-500">Plan</TableHead>
                <TableHead className="text-zinc-500">Status</TableHead>
                <TableHead className="text-zinc-500">Balance</TableHead>
                <TableHead className="text-zinc-500">P&L %</TableHead>
                <TableHead className="text-zinc-500">Days</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={7} className="text-center text-zinc-600">Loading...</TableCell></TableRow>
              ) : accounts.length === 0 ? (
                <TableRow><TableCell colSpan={7} className="text-center text-zinc-600">No accounts</TableCell></TableRow>
              ) : accounts.map((a) => {
                const pnlPct = a.starting_balance > 0 ? ((a.current_balance - a.starting_balance) / a.starting_balance * 100) : 0;
                return (
                  <TableRow key={a.id} className="border-zinc-800">
                    <TableCell className="text-zinc-200 text-sm">{a.user_email}</TableCell>
                    <TableCell><Badge variant="outline" className="border-zinc-700 text-zinc-300 text-xs">{a.account_type}</Badge></TableCell>
                    <TableCell className="text-zinc-400 text-sm">{a.plan}</TableCell>
                    <TableCell><Badge className={statusColor(a.status)}>{a.status}</Badge></TableCell>
                    <TableCell className="text-zinc-300 font-mono text-sm">${Number(a.current_balance).toLocaleString()}</TableCell>
                    <TableCell className={`font-mono text-sm ${pnlPct >= 0 ? "text-emerald-400" : "text-red-400"}`}>{pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(2)}%</TableCell>
                    <TableCell className="text-zinc-500 text-sm">{a.trading_days}/{a.min_trading_days}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </>
  );
}

// ==================== Payouts ====================
function PayoutsTab() {
  const [payouts, setPayouts] = useState<PayoutReq[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => { api.listPayouts().then(setPayouts).catch((e) => setError(e.message)).finally(() => setLoading(false)); };
  useEffect(() => { load(); }, []);

  const handleDecide = async (id: string, decision: "approved" | "rejected") => {
    try { await api.decidePayout(id, decision); load(); } catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
  };

  const statusColor = (s: string) => {
    switch (s) {
      case "approved": case "paid": return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "rejected": return "bg-red-500/10 text-red-400 border-red-500/20";
      case "pending": return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      default: return "border-zinc-700 text-zinc-300";
    }
  };

  return (
    <>
      {error && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-transparent">
                <TableHead className="text-zinc-500">Account</TableHead>
                <TableHead className="text-zinc-500">Amount</TableHead>
                <TableHead className="text-zinc-500">Method</TableHead>
                <TableHead className="text-zinc-500">Status</TableHead>
                <TableHead className="text-zinc-500">Requested</TableHead>
                <TableHead className="text-zinc-500">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={6} className="text-center text-zinc-600">Loading...</TableCell></TableRow>
              ) : payouts.length === 0 ? (
                <TableRow><TableCell colSpan={6} className="text-center text-zinc-600">No payouts</TableCell></TableRow>
              ) : payouts.map((p) => (
                <TableRow key={p.id} className="border-zinc-800">
                  <TableCell className="text-zinc-400 text-sm">{p.account_id.slice(0, 8)}...</TableCell>
                  <TableCell className="text-zinc-200 font-mono text-sm">${Number(p.amount).toLocaleString()}</TableCell>
                  <TableCell className="text-zinc-400 text-sm">{p.method}</TableCell>
                  <TableCell><Badge className={statusColor(p.status)}>{p.status}</Badge></TableCell>
                  <TableCell className="text-zinc-500 text-xs">{new Date(p.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    {p.status === "pending" && (
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" className="border-emerald-600 text-emerald-400 hover:bg-emerald-950 text-xs" onClick={() => handleDecide(p.id, "approved")}>Approve</Button>
                        <Button size="sm" variant="outline" className="border-red-600 text-red-400 hover:bg-red-950 text-xs" onClick={() => handleDecide(p.id, "rejected")}>Reject</Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </>
  );
}

// ==================== Violations ====================
function ViolationsTab() {
  const [violations, setViolations] = useState<RuleViolation[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.listViolations().then(setViolations).finally(() => setLoading(false)); }, []);

  const sevColor = (s: string) => {
    switch (s) {
      case "fatal": return "bg-red-500/10 text-red-400 border-red-500/20";
      case "critical": return "bg-orange-500/10 text-orange-400 border-orange-500/20";
      default: return "bg-amber-500/10 text-amber-400 border-amber-500/20";
    }
  };

  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow className="border-zinc-800 hover:bg-transparent">
              <TableHead className="text-zinc-500">Account</TableHead>
              <TableHead className="text-zinc-500">Rule</TableHead>
              <TableHead className="text-zinc-500">Description</TableHead>
              <TableHead className="text-zinc-500">Severity</TableHead>
              <TableHead className="text-zinc-500">Action</TableHead>
              <TableHead className="text-zinc-500">When</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={6} className="text-center text-zinc-600">Loading...</TableCell></TableRow>
            ) : violations.length === 0 ? (
              <TableRow><TableCell colSpan={6} className="text-center text-zinc-600">No violations</TableCell></TableRow>
            ) : violations.map((v) => (
              <TableRow key={v.id} className="border-zinc-800">
                <TableCell className="text-zinc-400 text-sm">{v.account_id.slice(0, 8)}...</TableCell>
                <TableCell><Badge variant="outline" className="border-zinc-700 text-zinc-300 text-xs">{v.rule_type.replace(/_/g, " ")}</Badge></TableCell>
                <TableCell className="text-zinc-400 text-sm max-w-sm truncate">{v.description}</TableCell>
                <TableCell><Badge className={sevColor(v.severity)}>{v.severity}</Badge></TableCell>
                <TableCell className="text-zinc-500 text-xs">{v.auto_action?.replace(/_/g, " ") || "-"}</TableCell>
                <TableCell className="text-zinc-500 text-xs">{new Date(v.detected_at).toLocaleString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

// ==================== Fraud Alerts ====================
function FraudTab() {
  const [alerts, setAlerts] = useState<FraudAlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.listFraudAlerts().then(setAlerts).finally(() => setLoading(false)); }, []);

  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow className="border-zinc-800 hover:bg-transparent">
              <TableHead className="text-zinc-500">Account</TableHead>
              <TableHead className="text-zinc-500">Type</TableHead>
              <TableHead className="text-zinc-500">Risk</TableHead>
              <TableHead className="text-zinc-500">Description</TableHead>
              <TableHead className="text-zinc-500">Status</TableHead>
              <TableHead className="text-zinc-500">When</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={6} className="text-center text-zinc-600">Loading...</TableCell></TableRow>
            ) : alerts.length === 0 ? (
              <TableRow><TableCell colSpan={6} className="text-center text-zinc-600">No fraud alerts</TableCell></TableRow>
            ) : alerts.map((a) => (
              <TableRow key={a.id} className="border-zinc-800">
                <TableCell className="text-zinc-400 text-sm">{a.account_id.slice(0, 8)}...</TableCell>
                <TableCell><Badge variant="outline" className="border-zinc-700 text-zinc-300 text-xs">{a.alert_type.replace(/_/g, " ")}</Badge></TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${a.risk_score >= 0.7 ? "bg-red-500" : a.risk_score >= 0.4 ? "bg-amber-500" : "bg-emerald-500"}`} />
                    <span className="text-zinc-300 text-sm">{(a.risk_score * 100).toFixed(0)}%</span>
                  </div>
                </TableCell>
                <TableCell className="text-zinc-400 text-sm max-w-sm truncate">{a.description}</TableCell>
                <TableCell><Badge className={a.status === "open" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" : "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"}>{a.status}</Badge></TableCell>
                <TableCell className="text-zinc-500 text-xs">{new Date(a.created_at).toLocaleString()}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
