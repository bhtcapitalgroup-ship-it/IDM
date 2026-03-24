"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { api, type Agent, type MemoryEntry } from "@/lib/api";

export default function MemoryPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    api.listAgents().then(setAgents).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedAgent) { setEntries([]); return; }
    api.getAgentMemory(selectedAgent).then(setEntries).catch((e) => setError(e.message));
  }, [selectedAgent]);

  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedAgent) return;
    setCreating(true);
    try {
      const form = new FormData(e.currentTarget);
      let value: Record<string, unknown> = {};
      try { value = JSON.parse((form.get("value") as string) || "{}"); } catch { /* empty */ }
      await api.storeMemory({
        agent_id: selectedAgent,
        key: form.get("key") as string,
        value,
        scope: (form.get("scope") as string) || "session",
        content: (form.get("content") as string) || undefined,
      });
      e.currentTarget.reset();
      setDialogOpen(false);
      api.getAgentMemory(selectedAgent).then(setEntries);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to store memory");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteMemory(id);
      setEntries((prev) => prev.filter((e) => e.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Agent Memory</h1>
        <p className="text-zinc-500 text-sm mt-1">View and manage agent context and memory entries</p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      {/* Agent selector */}
      <div className="flex items-center gap-4">
        <select
          value={selectedAgent || ""}
          onChange={(e) => setSelectedAgent(e.target.value || null)}
          className="rounded-md bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-zinc-100 min-w-64"
        >
          <option value="">Select an agent...</option>
          {agents.map((a) => (
            <option key={a.id} value={a.id}>{a.name} ({a.role.replace(/_/g, " ")})</option>
          ))}
        </select>

        {selectedAgent && (
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger render={<Button />}>Add Memory</DialogTrigger>
            <DialogContent className="bg-zinc-900 border-zinc-800">
              <DialogHeader>
                <DialogTitle>Store Memory Entry</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreate} className="space-y-4">
                <Input name="key" placeholder="Key" required className="bg-zinc-800 border-zinc-700" />
                <select name="scope" defaultValue="session" className="w-full rounded-md bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-zinc-100">
                  <option value="session">Session</option>
                  <option value="task">Task</option>
                  <option value="role">Role</option>
                  <option value="global">Global</option>
                </select>
                <Textarea name="content" placeholder="Text content (optional)" className="bg-zinc-800 border-zinc-700" />
                <Textarea name="value" placeholder='JSON value (e.g. {"key": "val"})' className="bg-zinc-800 border-zinc-700 font-mono text-xs" />
                <Button type="submit" className="w-full" disabled={creating}>
                  {creating ? "Storing..." : "Store"}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        )}
      </div>

      {/* Memory entries */}
      {!selectedAgent ? (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6">
            <p className="text-zinc-600 text-sm">Select an agent to view its memory entries.</p>
          </CardContent>
        </Card>
      ) : entries.length === 0 ? (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6">
            <p className="text-zinc-600 text-sm">No memory entries for this agent.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => (
            <Card key={entry.id} className="bg-zinc-900 border-zinc-800">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CardTitle className="text-sm font-medium text-zinc-200">{entry.key}</CardTitle>
                    <Badge variant="outline" className="border-zinc-700 text-zinc-400 text-xs">{entry.scope}</Badge>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-zinc-600">{new Date(entry.created_at).toLocaleString()}</span>
                    <Button variant="outline" size="sm" className="border-red-600 text-red-400 hover:bg-red-950 text-xs" onClick={() => handleDelete(entry.id)}>
                      Delete
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {entry.content && <p className="text-sm text-zinc-400 mb-2">{entry.content}</p>}
                {Object.keys(entry.value).length > 0 && (
                  <pre className="text-xs text-zinc-500 bg-zinc-800 p-3 rounded-lg overflow-auto max-h-32">
                    {JSON.stringify(entry.value, null, 2)}
                  </pre>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
