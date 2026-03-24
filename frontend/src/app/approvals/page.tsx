"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, type Approval } from "@/lib/api";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadApprovals = () => {
    setError(null);
    api
      .listApprovals()
      .then(setApprovals)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadApprovals();
  }, []);

  const handleDecision = async (id: string, decision: "approved" | "rejected") => {
    try {
      await api.decideApproval(id, decision);
      loadApprovals();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to process decision");
    }
  };

  const statusColor = (s: string) => {
    switch (s) {
      case "approved": return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "rejected": return "bg-red-500/10 text-red-400 border-red-500/20";
      case "pending": return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      default: return "border-zinc-700 text-zinc-300";
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Approval Queue</h1>
        <p className="text-zinc-500 text-sm mt-1">
          {approvals.filter((a) => a.status === "pending").length} pending approvals
        </p>
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
                <TableHead className="text-zinc-500">Action Type</TableHead>
                <TableHead className="text-zinc-500">Description</TableHead>
                <TableHead className="text-zinc-500">Status</TableHead>
                <TableHead className="text-zinc-500">Requested</TableHead>
                <TableHead className="text-zinc-500">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={5} className="text-center text-zinc-600">Loading...</TableCell></TableRow>
              ) : approvals.length === 0 ? (
                <TableRow><TableCell colSpan={5} className="text-center text-zinc-600">No approvals</TableCell></TableRow>
              ) : (
                approvals.map((approval) => (
                  <TableRow key={approval.id} className="border-zinc-800">
                    <TableCell>
                      <Badge variant="outline" className="border-zinc-700 text-zinc-300">
                        {approval.action_type.replace(/_/g, " ")}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-zinc-400 max-w-sm truncate">
                      {approval.description || "-"}
                    </TableCell>
                    <TableCell>
                      <Badge className={statusColor(approval.status)}>{approval.status}</Badge>
                    </TableCell>
                    <TableCell className="text-zinc-500 text-sm">
                      {new Date(approval.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      {approval.status === "pending" && (
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-emerald-600 text-emerald-400 hover:bg-emerald-950 text-xs"
                            onClick={() => handleDecision(approval.id, "approved")}
                          >
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-red-600 text-red-400 hover:bg-red-950 text-xs"
                            onClick={() => handleDecision(approval.id, "rejected")}
                          >
                            Reject
                          </Button>
                        </div>
                      )}
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
