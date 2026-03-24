"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, type AuditLog } from "@/lib/api";

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getAuditLogs({ limit: 100 })
      .then(setLogs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Audit Log</h1>
        <p className="text-zinc-500 text-sm mt-1">All system actions</p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-transparent">
                <TableHead className="text-zinc-500">Time</TableHead>
                <TableHead className="text-zinc-500">Actor</TableHead>
                <TableHead className="text-zinc-500">Action</TableHead>
                <TableHead className="text-zinc-500">Resource</TableHead>
                <TableHead className="text-zinc-500">Details</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={5} className="text-center text-zinc-600">Loading...</TableCell></TableRow>
              ) : logs.length === 0 ? (
                <TableRow><TableCell colSpan={5} className="text-center text-zinc-600">No audit logs</TableCell></TableRow>
              ) : (
                logs.map((log) => (
                  <TableRow key={log.id} className="border-zinc-800">
                    <TableCell className="text-zinc-500 text-xs whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-zinc-400 text-sm">
                      <span className="text-zinc-600">{log.actor_type}:</span>{" "}
                      {log.actor.slice(0, 8)}...
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="border-zinc-700 text-zinc-300 text-xs">
                        {log.action}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-zinc-400 text-sm">
                      {log.resource_type}/{log.resource_id.slice(0, 8)}
                    </TableCell>
                    <TableCell className="text-zinc-600 text-xs max-w-xs truncate">
                      {log.after_state ? JSON.stringify(log.after_state).slice(0, 80) : "-"}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
