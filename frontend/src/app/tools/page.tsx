"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, type ToolDef } from "@/lib/api";

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolDef[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const load = () => {
    setError(null);
    api.listTools().then(setTools).catch((e) => setError(e.message)).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setCreating(true);
    try {
      const form = new FormData(e.currentTarget);
      const rolesRaw = (form.get("allowed_roles") as string) || "";
      await api.createTool({
        name: form.get("name") as string,
        description: (form.get("description") as string) || undefined,
        allowed_roles: rolesRaw ? rolesRaw.split(",").map((r) => r.trim()) : [],
        permission_level: (form.get("permission_level") as string) || "standard",
        requires_approval: form.get("requires_approval") === "on",
      });
      e.currentTarget.reset();
      setDialogOpen(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create tool");
    } finally {
      setCreating(false);
    }
  };

  const levelColor = (l: string) => {
    if (l === "elevated") return "bg-amber-500/10 text-amber-400 border-amber-500/20";
    return "border-zinc-700 text-zinc-300";
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tool Registry</h1>
          <p className="text-zinc-500 text-sm mt-1">{tools.length} tools</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger render={<Button />}>Create Tool</DialogTrigger>
          <DialogContent className="bg-zinc-900 border-zinc-800">
            <DialogHeader>
              <DialogTitle>Create Tool</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <Input name="name" placeholder="Tool name" required className="bg-zinc-800 border-zinc-700" />
              <Textarea name="description" placeholder="Description" className="bg-zinc-800 border-zinc-700" />
              <Input name="allowed_roles" placeholder="Allowed roles (comma-separated)" className="bg-zinc-800 border-zinc-700" />
              <select name="permission_level" defaultValue="standard" className="w-full rounded-md bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-zinc-100">
                <option value="standard">Standard</option>
                <option value="elevated">Elevated</option>
              </select>
              <label className="flex items-center gap-2 text-sm text-zinc-400">
                <input type="checkbox" name="requires_approval" className="rounded" />
                Requires approval
              </label>
              <Button type="submit" className="w-full" disabled={creating}>
                {creating ? "Creating..." : "Create"}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-transparent">
                <TableHead className="text-zinc-500">Name</TableHead>
                <TableHead className="text-zinc-500">Description</TableHead>
                <TableHead className="text-zinc-500">Allowed Roles</TableHead>
                <TableHead className="text-zinc-500">Level</TableHead>
                <TableHead className="text-zinc-500">Approval</TableHead>
                <TableHead className="text-zinc-500">Active</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={6} className="text-center text-zinc-600">Loading...</TableCell></TableRow>
              ) : tools.length === 0 ? (
                <TableRow><TableCell colSpan={6} className="text-center text-zinc-600">No tools registered</TableCell></TableRow>
              ) : (
                tools.map((t) => (
                  <TableRow key={t.id} className="border-zinc-800">
                    <TableCell className="font-medium text-zinc-200">{t.name.replace(/_/g, " ")}</TableCell>
                    <TableCell className="text-zinc-400 text-sm max-w-xs truncate">{t.description || "-"}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {t.allowed_roles.length === 0
                          ? <span className="text-zinc-600 text-xs">any</span>
                          : t.allowed_roles.map((r) => (
                              <Badge key={r} variant="outline" className="border-zinc-700 text-zinc-400 text-xs">{r.replace(/_/g, " ")}</Badge>
                            ))}
                      </div>
                    </TableCell>
                    <TableCell><Badge className={levelColor(t.permission_level)}>{t.permission_level}</Badge></TableCell>
                    <TableCell className="text-zinc-500">{t.requires_approval ? "Yes" : "-"}</TableCell>
                    <TableCell>{t.is_active ? <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">active</Badge> : <Badge className="bg-zinc-500/10 text-zinc-400 border-zinc-500/20">off</Badge>}</TableCell>
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
