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
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, type Task } from "@/lib/api";

const STATUS_FILTERS = [
  "all",
  "created",
  "assigned",
  "in_progress",
  "review",
  "completed",
  "blocked",
  "failed",
];

export default function TasksPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);

  const loadTasks = (status?: string) => {
    setError(null);
    const params = status && status !== "all" ? { status } : undefined;
    api
      .listTasks(params)
      .then(setTasks)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadTasks(filter);
  }, [filter]);

  const handleCreate = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setCreating(true);
    try {
      const form = new FormData(e.currentTarget);
      await api.createTask({
        title: form.get("title") as string,
        description: (form.get("description") as string) || undefined,
        priority: (form.get("priority") as string) || "medium",
      });
      e.currentTarget.reset();
      setDialogOpen(false);
      loadTasks(filter);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setCreating(false);
    }
  };

  const priorityColor = (p: string) => {
    switch (p) {
      case "critical":
        return "bg-red-500/10 text-red-400 border-red-500/20";
      case "high":
        return "bg-orange-500/10 text-orange-400 border-orange-500/20";
      case "medium":
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "low":
        return "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";
      default:
        return "border-zinc-700 text-zinc-300";
    }
  };

  const statusColor = (s: string) => {
    switch (s) {
      case "completed":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "in_progress":
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "review":
        return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      case "blocked":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "failed":
        return "bg-red-500/10 text-red-400 border-red-500/20";
      default:
        return "border-zinc-700 text-zinc-300";
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Task Registry</h1>
          <p className="text-zinc-500 text-sm mt-1">{tasks.length} tasks</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger render={<Button />}>Create Task</DialogTrigger>
          <DialogContent className="bg-zinc-900 border-zinc-800">
            <DialogHeader>
              <DialogTitle>Create New Task</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <Input
                name="title"
                placeholder="Task title"
                required
                className="bg-zinc-800 border-zinc-700"
              />
              <Textarea
                name="description"
                placeholder="Description (optional)"
                className="bg-zinc-800 border-zinc-700"
              />
              <select
                name="priority"
                defaultValue="medium"
                className="w-full rounded-md bg-zinc-800 border border-zinc-700 px-3 py-2 text-sm text-zinc-100"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
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

      <Tabs value={filter} onValueChange={setFilter}>
        <TabsList className="bg-zinc-900 border border-zinc-800">
          {STATUS_FILTERS.map((s) => (
            <TabsTrigger
              key={s}
              value={s}
              className="data-[state=active]:bg-zinc-800 text-xs capitalize"
            >
              {s.replace(/_/g, " ")}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-zinc-800 hover:bg-transparent">
                <TableHead className="text-zinc-500">Title</TableHead>
                <TableHead className="text-zinc-500">Status</TableHead>
                <TableHead className="text-zinc-500">Priority</TableHead>
                <TableHead className="text-zinc-500">Review</TableHead>
                <TableHead className="text-zinc-500">Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-zinc-600">
                    Loading...
                  </TableCell>
                </TableRow>
              ) : tasks.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-zinc-600">
                    No tasks
                  </TableCell>
                </TableRow>
              ) : (
                tasks.map((task) => (
                  <TableRow
                    key={task.id}
                    className="border-zinc-800 cursor-pointer hover:bg-zinc-800/50"
                    onClick={() => router.push(`/tasks/${task.id}`)}
                  >
                    <TableCell className="font-medium text-zinc-200 max-w-md truncate">
                      {task.title}
                    </TableCell>
                    <TableCell>
                      <Badge className={statusColor(task.status)}>
                        {task.status.replace(/_/g, " ")}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={priorityColor(task.priority)}>
                        {task.priority}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-zinc-500">
                      {task.review_required ? "Yes" : "-"}
                    </TableCell>
                    <TableCell className="text-zinc-500 text-sm">
                      {new Date(task.created_at).toLocaleDateString()}
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
