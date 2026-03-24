"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, type DashboardStats, type AuditLog } from "@/lib/api";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getStats(), api.getAuditLogs({ limit: 10 })])
      .then(([s, l]) => {
        setStats(s);
        setLogs(l);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-8">
        <div className="text-zinc-500 text-sm">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-zinc-500 text-sm mt-1">System overview</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard title="Total Agents" value={stats?.total_agents ?? 0} />
        <StatCard title="Total Tasks" value={stats?.total_tasks ?? 0} />
        <StatCard title="Pending Approvals" value={stats?.pending_approvals ?? 0} variant="warning" />
        <StatCard title="Active Tasks" value={stats?.tasks_by_status?.in_progress ?? 0} />
      </div>

      {stats?.tasks_by_status && Object.keys(stats.tasks_by_status).length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400">Tasks by Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {Object.entries(stats.tasks_by_status).map(([status, count]) => (
                <div key={status} className="flex items-center gap-2">
                  <Badge variant="outline" className="border-zinc-700 text-zinc-300">
                    {status}
                  </Badge>
                  <span className="text-sm text-zinc-400">{count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-zinc-400">Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          {logs.length === 0 ? (
            <p className="text-zinc-600 text-sm">No activity yet</p>
          ) : (
            <div className="space-y-2">
              {logs.map((log) => (
                <div key={log.id} className="flex items-center justify-between text-sm py-2 border-b border-zinc-800 last:border-0">
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className="border-zinc-700 text-zinc-300 text-xs">
                      {log.action}
                    </Badge>
                    <span className="text-zinc-400">
                      {log.resource_type}/{log.resource_id.slice(0, 8)}
                    </span>
                  </div>
                  <span className="text-zinc-600 text-xs">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  title,
  value,
  variant,
}: {
  title: string;
  value: number;
  variant?: "warning";
}) {
  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardContent className="pt-6">
        <p className="text-xs text-zinc-500 font-medium uppercase tracking-wider">{title}</p>
        <p className={`text-3xl font-bold mt-2 ${variant === "warning" && value > 0 ? "text-amber-400" : "text-white"}`}>
          {value}
        </p>
      </CardContent>
    </Card>
  );
}
