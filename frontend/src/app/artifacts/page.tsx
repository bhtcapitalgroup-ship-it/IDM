"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, type CollabArtifact } from "@/lib/api";

const typeColor: Record<string, string> = {
  spec: "border-blue-500/30 text-blue-400",
  api_contract: "border-purple-500/30 text-purple-400",
  db_change: "border-amber-500/30 text-amber-400",
  ui_component: "border-emerald-500/30 text-emerald-400",
  qa_report: "border-cyan-500/30 text-cyan-400",
  compliance_note: "border-red-500/30 text-red-400",
  deployment_plan: "border-orange-500/30 text-orange-400",
};

const statusColor: Record<string, string> = {
  draft: "border-zinc-600 text-zinc-400",
  review: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  approved: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  rejected: "bg-red-500/10 text-red-400 border-red-500/20",
  final: "bg-blue-500/10 text-blue-400 border-blue-500/20",
};

export default function ArtifactsPage() {
  const [artifacts, setArtifacts] = useState<CollabArtifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = () => { api.listArtifacts().then(setArtifacts).catch((e) => setError(e.message)).finally(() => setLoading(false)); };
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setCreating(true);
    try {
      const f = new FormData(e.currentTarget);
      await api.createArtifact({
        title: f.get("title") as string,
        artifact_type: f.get("artifact_type") as string,
        content: f.get("content") as string,
      });
      e.currentTarget.reset();
      setDialogOpen(false);
      load();
    } catch (err) { setError(err instanceof Error ? err.message : "Failed"); }
    finally { setCreating(false); }
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Artifacts</h1>
          <p className="text-zinc-500 text-sm mt-1">Deliverables produced by agents — specs, contracts, reports, plans</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger render={<Button />}>Create Artifact</DialogTrigger>
          <DialogContent className="bg-zinc-900 border-zinc-800 sm:max-w-lg">
            <DialogHeader><DialogTitle>Create Artifact</DialogTitle></DialogHeader>
            <form onSubmit={handleCreate} className="space-y-3">
              <Input name="title" placeholder="Artifact title" required className="bg-zinc-800 border-zinc-700" />
              <select name="artifact_type" required className="w-full rounded-md bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-zinc-100">
                {["spec","api_contract","db_change","ui_component","qa_report","compliance_note","deployment_plan"].map((t) => (
                  <option key={t} value={t}>{t.replace(/_/g, " ")}</option>
                ))}
              </select>
              <Textarea name="content" placeholder="Artifact content..." required rows={8} className="bg-zinc-800 border-zinc-700 font-mono text-xs" />
              <Button type="submit" className="w-full" disabled={creating}>{creating ? "Creating..." : "Create"}</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {error && <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>}

      <div className="space-y-3">
        {loading ? (
          <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-zinc-600 text-sm">Loading...</CardContent></Card>
        ) : artifacts.length === 0 ? (
          <Card className="bg-zinc-900 border-zinc-800"><CardContent className="pt-6 text-zinc-600 text-sm">No artifacts yet</CardContent></Card>
        ) : (
          artifacts.map((a) => (
            <Card key={a.id} className="bg-zinc-900 border-zinc-800">
              <CardHeader className="pb-2 cursor-pointer" onClick={() => setExpanded(expanded === a.id ? null : a.id)}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Badge variant="outline" className={typeColor[a.artifact_type] || "border-zinc-700 text-zinc-300"}>
                      {a.artifact_type.replace(/_/g, " ")}
                    </Badge>
                    <CardTitle className="text-sm font-medium text-zinc-200">{a.title}</CardTitle>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={statusColor[a.status] || "border-zinc-700 text-zinc-300"}>{a.status}</Badge>
                    <span className="text-xs text-zinc-600">v{a.version}</span>
                  </div>
                </div>
              </CardHeader>
              {expanded === a.id && (
                <CardContent>
                  <pre className="text-xs text-zinc-400 bg-zinc-800 p-4 rounded-lg overflow-auto max-h-64 whitespace-pre-wrap">{a.content}</pre>
                  <p className="text-xs text-zinc-600 mt-2">{new Date(a.created_at).toLocaleString()}</p>
                </CardContent>
              )}
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
