"use client";

import { useEffect, useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, type Prompt } from "@/lib/api";

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const load = () => {
    setError(null);
    api.listPrompts().then(setPrompts).catch((e) => setError(e.message)).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setCreating(true);
    try {
      const form = new FormData(e.currentTarget);
      await api.createPrompt({
        name: form.get("name") as string,
        template: form.get("template") as string,
        category: (form.get("category") as string) || "base",
        role: (form.get("role") as string) || undefined,
      });
      e.currentTarget.reset();
      setDialogOpen(false);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create prompt");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Prompt Registry</h1>
          <p className="text-zinc-500 text-sm mt-1">{prompts.length} prompts</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger render={<Button />}>Create Prompt</DialogTrigger>
          <DialogContent className="bg-zinc-900 border-zinc-800 sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>Create Prompt</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <Input name="name" placeholder="Prompt name" required className="bg-zinc-800 border-zinc-700" />
              <div className="grid grid-cols-2 gap-3">
                <Input name="category" placeholder="Category (default: base)" className="bg-zinc-800 border-zinc-700" />
                <Input name="role" placeholder="Agent role (optional)" className="bg-zinc-800 border-zinc-700" />
              </div>
              <Textarea name="template" placeholder="Prompt template text..." required rows={6} className="bg-zinc-800 border-zinc-700 font-mono text-xs" />
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
                <TableHead className="text-zinc-500">Category</TableHead>
                <TableHead className="text-zinc-500">Role</TableHead>
                <TableHead className="text-zinc-500">Version</TableHead>
                <TableHead className="text-zinc-500">Active</TableHead>
                <TableHead className="text-zinc-500">Template Preview</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow><TableCell colSpan={6} className="text-center text-zinc-600">Loading...</TableCell></TableRow>
              ) : prompts.length === 0 ? (
                <TableRow><TableCell colSpan={6} className="text-center text-zinc-600">No prompts registered</TableCell></TableRow>
              ) : (
                prompts.map((p) => (
                  <TableRow key={p.id} className="border-zinc-800">
                    <TableCell className="font-medium text-zinc-200">{p.name}</TableCell>
                    <TableCell><Badge variant="outline" className="border-zinc-700 text-zinc-300">{p.category}</Badge></TableCell>
                    <TableCell className="text-zinc-400">{p.role || "-"}</TableCell>
                    <TableCell className="text-zinc-500">v{p.version}</TableCell>
                    <TableCell>{p.is_active ? <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">active</Badge> : <Badge className="bg-zinc-500/10 text-zinc-400 border-zinc-500/20">inactive</Badge>}</TableCell>
                    <TableCell className="text-zinc-600 text-xs max-w-xs truncate font-mono">{p.template.slice(0, 80)}{p.template.length > 80 ? "..." : ""}</TableCell>
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
