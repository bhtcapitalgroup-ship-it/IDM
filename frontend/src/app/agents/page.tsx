"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, type Agent } from "@/lib/api";

const AGENT_ROLES = [
  "executive_orchestrator",
  "product_architect",
  "frontend_builder",
  "backend_builder",
  "database_builder",
  "qa_inspector",
  "devops_operator",
  "compliance_reviewer",
];

export default function AgentsPage() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const loadAgents = () => {
    setError(null);
    api
      .listAgents()
      .then(setAgents)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadAgents();
  }, []);

  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setCreating(true);
    try {
      const form = new FormData(e.currentTarget);
      await api.createAgent({
        name: form.get("name") as string,
        role: form.get("role") as string,
        description: (form.get("description") as string) || undefined,
      });
      e.currentTarget.reset();
      setDialogOpen(false);
      loadAgents();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create agent");
    } finally {
      setCreating(false);
    }
  };

  const statusColor = (s: string) => {
    switch (s) {
      case "active":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "inactive":
        return "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";
      case "error":
        return "bg-red-500/10 text-red-400 border-red-500/20";
      default:
        return "border-zinc-700 text-zinc-300";
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Agent Registry</h1>
          <p className="text-zinc-500 text-sm mt-1">
            {agents.length} registered agents
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger render={<Button />}>Create Agent</DialogTrigger>
          <DialogContent className="bg-zinc-900 border-zinc-800">
            <DialogHeader>
              <DialogTitle>Create New Agent</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <Input
                name="name"
                placeholder="Agent name"
                required
                className="bg-zinc-800 border-zinc-700"
              />
              <select
                name="role"
                required
                className="w-full rounded-md bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-zinc-100"
              >
                <option value="">Select role...</option>
                {AGENT_ROLES.map((r) => (
                  <option key={r} value={r}>
                    {r.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
              <Textarea
                name="description"
                placeholder="Description (optional)"
                className="bg-zinc-800 border-zinc-700"
              />
              <Button type="submit" className="w-full" disabled={creating}>
                {creating ? "Creating..." : "Create"}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
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
                <TableHead className="text-zinc-500">Name</TableHead>
                <TableHead className="text-zinc-500">Role</TableHead>
                <TableHead className="text-zinc-500">Type</TableHead>
                <TableHead className="text-zinc-500">Status</TableHead>
                <TableHead className="text-zinc-500">Version</TableHead>
                <TableHead className="text-zinc-500">Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-zinc-600">
                    Loading...
                  </TableCell>
                </TableRow>
              ) : agents.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-zinc-600">
                    No agents registered
                  </TableCell>
                </TableRow>
              ) : (
                agents.map((agent) => (
                  <TableRow
                    key={agent.id}
                    className="border-zinc-800 cursor-pointer hover:bg-zinc-800/50"
                    onClick={() => router.push(`/agents/${agent.id}`)}
                  >
                    <TableCell className="font-medium text-zinc-200">
                      {agent.name}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className="border-zinc-700 text-zinc-300"
                      >
                        {agent.role.replace(/_/g, " ")}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-zinc-400">{agent.type}</TableCell>
                    <TableCell>
                      <Badge className={statusColor(agent.status)}>
                        {agent.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-zinc-500">
                      {agent.version}
                    </TableCell>
                    <TableCell className="text-zinc-500 text-sm">
                      {new Date(agent.created_at).toLocaleDateString()}
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
