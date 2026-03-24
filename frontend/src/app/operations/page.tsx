"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type Agent, type CollabHandoff, type DashboardStats, type AgentInbox } from "@/lib/api";

export default function OperationsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [handoffs, setHandoffs] = useState<CollabHandoff[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [inboxes, setInboxes] = useState<Record<string, AgentInbox>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.listAgents(),
      api.listHandoffs({ status: "pending" }),
      api.getStats(),
    ]).then(([a, h, s]) => {
      setAgents(a);
      setHandoffs(h);
      setStats(s);
      // Load inboxes for each agent
      Promise.all(a.map((agent) => api.getAgentInbox(agent.id).then((inbox) => ({ id: agent.id, inbox })))).then((results) => {
        const map: Record<string, AgentInbox> = {};
        results.forEach((r) => { map[r.id] = r.inbox; });
        setInboxes(map);
      });
    }).finally(() => setLoading(false));
  }, []);

  const handleResolve = async (id: string, status: "accepted" | "completed") => {
    await api.resolveHandoff(id, status);
    setHandoffs((prev) => prev.filter((h) => h.id !== id));
  };

  if (loading) return <div className="p-8 text-zinc-500 text-sm">Loading operations...</div>;

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Live Operations</h1>
        <p className="text-zinc-500 text-sm mt-1">Real-time view of agent activity, handoffs, and workload</p>
      </div>

      {/* System stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Agents" value={stats?.total_agents ?? 0} />
        <StatCard label="Tasks" value={stats?.total_tasks ?? 0} />
        <StatCard label="Pending Approvals" value={stats?.pending_approvals ?? 0} warn />
        <StatCard label="Active Handoffs" value={handoffs.length} warn={handoffs.length > 0} />
      </div>

      {/* Agent Network */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader><CardTitle className="text-sm font-medium text-zinc-400">Agent Network</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {agents.map((agent) => {
              const inbox = inboxes[agent.id];
              const busy = (inbox?.assigned_tasks ?? 0) > 0;
              const hasWork = (inbox?.pending_handoffs ?? 0) + (inbox?.pending_reviews ?? 0) > 0;
              return (
                <div key={agent.id} className={`rounded-lg border p-4 ${busy ? "border-blue-500/30 bg-blue-500/5" : hasWork ? "border-amber-500/30 bg-amber-500/5" : "border-zinc-800 bg-zinc-900"}`}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium text-zinc-200">{agent.name}</p>
                    <Badge className={agent.status === "active" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"}>
                      {agent.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-zinc-500 mb-3">{agent.role.replace(/_/g, " ")}</p>
                  {inbox && (
                    <div className="space-y-1 text-xs">
                      {inbox.assigned_tasks > 0 && <div className="text-blue-400">{inbox.assigned_tasks} active tasks</div>}
                      {inbox.pending_handoffs > 0 && <div className="text-amber-400">{inbox.pending_handoffs} pending handoffs</div>}
                      {inbox.pending_reviews > 0 && <div className="text-purple-400">{inbox.pending_reviews} pending reviews</div>}
                      {inbox.blocked_tasks > 0 && <div className="text-red-400">{inbox.blocked_tasks} blocked</div>}
                      {inbox.pending_messages > 0 && <div className="text-zinc-400">{inbox.pending_messages} unread messages</div>}
                      {inbox.assigned_tasks === 0 && inbox.pending_handoffs === 0 && inbox.pending_reviews === 0 && <div className="text-zinc-600">Idle</div>}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Pending Handoffs */}
      {handoffs.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader><CardTitle className="text-sm font-medium text-zinc-400">Pending Handoffs</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {handoffs.map((h) => (
              <div key={h.id} className="flex items-center justify-between py-3 px-4 rounded-lg bg-zinc-800/50">
                <div className="flex items-center gap-3">
                  <Badge variant="outline" className="border-purple-500/30 text-purple-400">{h.handoff_type}</Badge>
                  <span className="text-sm text-zinc-300 truncate max-w-md">{h.reason}</span>
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button size="sm" variant="outline" className="border-emerald-600 text-emerald-400 text-xs" onClick={() => handleResolve(h.id, "accepted")}>Accept</Button>
                  <Button size="sm" variant="outline" className="border-blue-600 text-blue-400 text-xs" onClick={() => handleResolve(h.id, "completed")}>Complete</Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Tasks by Status */}
      {stats?.tasks_by_status && Object.keys(stats.tasks_by_status).length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader><CardTitle className="text-sm font-medium text-zinc-400">Workflow Status</CardTitle></CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-4">
              {Object.entries(stats.tasks_by_status).map(([status, count]) => (
                <div key={status} className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-full ${status === "completed" ? "bg-emerald-500" : status === "in_progress" ? "bg-blue-500" : status === "blocked" ? "bg-red-500" : status === "review" ? "bg-purple-500" : "bg-zinc-600"}`} />
                  <span className="text-sm text-zinc-300">{status.replace(/_/g, " ")}</span>
                  <span className="text-sm text-zinc-500 font-mono">{count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function StatCard({ label, value, warn }: { label: string; value: number; warn?: boolean }) {
  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardContent className="pt-6">
        <p className="text-xs text-zinc-500 uppercase tracking-wider">{label}</p>
        <p className={`text-3xl font-bold mt-2 ${warn && value > 0 ? "text-amber-400" : "text-white"}`}>{value}</p>
      </CardContent>
    </Card>
  );
}
