"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { api, type Task } from "@/lib/api";

const VALID_TRANSITIONS: Record<string, string[]> = {
  created: ["pending", "assigned", "cancelled"],
  pending: ["assigned", "cancelled"],
  assigned: ["in_progress", "cancelled", "blocked"],
  in_progress: ["review", "completed", "failed", "blocked", "cancelled"],
  review: ["approved", "rejected"],
  approved: ["completed"],
  rejected: ["assigned"],
  blocked: ["assigned", "in_progress", "cancelled"],
  failed: ["assigned", "cancelled"],
};

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [task, setTask] = useState<Task | null>(null);
  const [subtasks, setSubtasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [transitioning, setTransitioning] = useState(false);

  const id = params.id as string;

  const loadTask = () => {
    api
      .getTask(id)
      .then((t) => {
        setTask(t);
        // Load subtasks
        api.listTasks().then((all) => {
          setSubtasks(all.filter((st) => st.parent_task_id === t.id));
        });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadTask();
  }, [id]);

  const transitionTo = async (newStatus: string) => {
    setTransitioning(true);
    try {
      const updated = await api.updateTask(id, { status: newStatus });
      setTask(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update status");
    } finally {
      setTransitioning(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-zinc-500 text-sm">Loading task...</div>;
  }

  if (error || !task) {
    return (
      <div className="p-8">
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error || "Task not found"}
        </div>
        <Button variant="outline" className="mt-4" onClick={() => router.push("/tasks")}>
          Back to Tasks
        </Button>
      </div>
    );
  }

  const allowedTransitions = VALID_TRANSITIONS[task.status] || [];

  const statusColor = (s: string) => {
    switch (s) {
      case "completed": case "approved":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "in_progress":
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "review":
        return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      case "blocked":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "failed": case "cancelled": case "rejected":
        return "bg-red-500/10 text-red-400 border-red-500/20";
      default:
        return "border-zinc-700 text-zinc-300";
    }
  };

  const priorityColor = (p: string) => {
    switch (p) {
      case "critical": return "bg-red-500/10 text-red-400 border-red-500/20";
      case "high": return "bg-orange-500/10 text-orange-400 border-orange-500/20";
      case "medium": return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      default: return "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";
    }
  };

  const transitionColor = (s: string) => {
    if (s === "completed" || s === "approved") return "border-emerald-600 text-emerald-400 hover:bg-emerald-950";
    if (s === "cancelled" || s === "rejected" || s === "failed") return "border-red-600 text-red-400 hover:bg-red-950";
    if (s === "blocked") return "border-amber-600 text-amber-400 hover:bg-amber-950";
    return "border-zinc-600 text-zinc-300 hover:bg-zinc-800";
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <button
          onClick={() => router.push("/tasks")}
          className="text-xs text-zinc-500 hover:text-zinc-300 mb-2 block"
        >
          &larr; Back to Tasks
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">{task.title}</h1>
            <p className="text-zinc-500 text-sm mt-1">{task.description || "No description"}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={statusColor(task.status)}>{task.status.replace(/_/g, " ")}</Badge>
            <Badge className={priorityColor(task.priority)}>{task.priority}</Badge>
          </div>
        </div>
      </div>

      {/* Status Transitions */}
      {allowedTransitions.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400">Transition Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {allowedTransitions.map((s) => (
                <Button
                  key={s}
                  variant="outline"
                  size="sm"
                  className={transitionColor(s)}
                  disabled={transitioning}
                  onClick={() => transitionTo(s)}
                >
                  {s.replace(/_/g, " ")}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Task Details */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400">Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Field label="Created by" value={task.created_by.slice(0, 8) + "..."} />
            <Field label="Assigned Agent" value={task.assigned_agent_id ? task.assigned_agent_id.slice(0, 8) + "..." : "Unassigned"} />
            <Field label="Review Required" value={task.review_required ? "Yes" : "No"} />
            <Field label="Retries" value={`${task.retry_count} / ${task.max_retries}`} />
            <Field label="Created" value={new Date(task.created_at).toLocaleString()} />
            <Field label="Updated" value={new Date(task.updated_at).toLocaleString()} />
            {task.parent_task_id && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-zinc-500">Parent Task</span>
                <button
                  onClick={() => router.push(`/tasks/${task.parent_task_id}`)}
                  className="text-blue-400 hover:text-blue-300"
                >
                  {task.parent_task_id.slice(0, 8)}...
                </button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Dependencies */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400">Dependencies</CardTitle>
          </CardHeader>
          <CardContent>
            {task.dependencies.length === 0 ? (
              <p className="text-zinc-600 text-sm">No dependencies</p>
            ) : (
              <div className="space-y-2">
                {task.dependencies.map((depId) => (
                  <button
                    key={depId}
                    onClick={() => router.push(`/tasks/${depId}`)}
                    className="block text-sm text-blue-400 hover:text-blue-300"
                  >
                    Task {depId.slice(0, 8)}...
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Input Payload */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400">Input Payload</CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(task.input_payload).length === 0 ? (
              <p className="text-zinc-600 text-sm">No input data</p>
            ) : (
              <pre className="text-xs text-zinc-400 bg-zinc-800 p-3 rounded-lg overflow-auto max-h-48">
                {JSON.stringify(task.input_payload, null, 2)}
              </pre>
            )}
          </CardContent>
        </Card>

        {/* Output Payload */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400">Output Payload</CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(task.output_payload).length === 0 ? (
              <p className="text-zinc-600 text-sm">No output data</p>
            ) : (
              <pre className="text-xs text-zinc-400 bg-zinc-800 p-3 rounded-lg overflow-auto max-h-48">
                {JSON.stringify(task.output_payload, null, 2)}
              </pre>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Subtasks */}
      {subtasks.length > 0 && (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400">
              Subtasks ({subtasks.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {subtasks.map((st) => (
                <div
                  key={st.id}
                  className="flex items-center justify-between py-2 px-3 rounded-lg bg-zinc-800/50 cursor-pointer hover:bg-zinc-800"
                  onClick={() => router.push(`/tasks/${st.id}`)}
                >
                  <div className="flex items-center gap-3">
                    <Badge className={statusColor(st.status)} >
                      {st.status.replace(/_/g, " ")}
                    </Badge>
                    <span className="text-sm text-zinc-200">{st.title}</span>
                  </div>
                  <Badge className={priorityColor(st.priority)}>{st.priority}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Separator className="bg-zinc-800" />
      <div className="text-xs text-zinc-600">ID: {task.id}</div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-zinc-500">{label}</span>
      <span className="text-zinc-200">{value}</span>
    </div>
  );
}
