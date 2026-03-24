"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, type Task } from "@/lib/api";

export default function OrchestratorPage() {
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    parent: Task;
    subtasks: Task[];
    plan: { summary: string; rationale: string };
    ai_metadata: Record<string, unknown>;
  } | null>(null);

  const handleDecompose = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim()) return;
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.decomposeGoal(goal.trim());
      setResult({
        parent: res.parent_task,
        subtasks: res.subtasks,
        plan: res.plan,
        ai_metadata: res.ai_metadata,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decomposition failed");
    } finally {
      setSubmitting(false);
    }
  };

  const statusColor = (s: string) => {
    switch (s) {
      case "assigned":
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "created":
        return "border-zinc-700 text-zinc-300";
      default:
        return "border-zinc-700 text-zinc-300";
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Executive Orchestrator</h1>
        <p className="text-zinc-500 text-sm mt-1">
          Decompose a high-level goal into tasks with auto-assignment
        </p>
      </div>

      <Card className="bg-zinc-900 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-zinc-400">
            Submit a Goal
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleDecompose} className="space-y-4">
            <Textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              placeholder="Describe what you want to build or accomplish..."
              className="bg-zinc-800 border-zinc-700 min-h-24"
              required
            />
            <Button type="submit" disabled={submitting || !goal.trim()}>
              {submitting ? "Decomposing..." : "Decompose Goal"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {/* Parent task */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium text-zinc-400">
                  Parent Task
                </CardTitle>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => router.push(`/tasks/${result.parent.id}`)}
                >
                  View Details
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-zinc-200 font-medium">{result.parent.title}</p>
              <p className="text-zinc-500 text-sm mt-1">{result.parent.description}</p>
            </CardContent>
          </Card>

          {/* Plan details */}
          {(result.plan.summary || result.plan.rationale) && (
            <Card className="bg-zinc-900 border-zinc-800">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-zinc-400">AI Plan</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {result.plan.summary && (
                  <div>
                    <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Summary</p>
                    <p className="text-sm text-zinc-300">{result.plan.summary}</p>
                  </div>
                )}
                {result.plan.rationale && (
                  <div>
                    <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Rationale</p>
                    <p className="text-sm text-zinc-400">{result.plan.rationale}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Subtasks */}
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-zinc-400">
                Generated Subtasks ({result.subtasks.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {result.subtasks.map((task) => (
                  <div
                    key={task.id}
                    className="flex items-center justify-between py-3 px-4 rounded-lg bg-zinc-800/50 cursor-pointer hover:bg-zinc-800 transition-colors"
                    onClick={() => router.push(`/tasks/${task.id}`)}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <Badge className={statusColor(task.status)}>
                        {task.status}
                      </Badge>
                      <span className="text-sm text-zinc-200 truncate">
                        {task.title}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-4">
                      {task.assigned_agent_id && (
                        <Badge
                          variant="outline"
                          className="border-emerald-500/30 text-emerald-400 text-xs"
                        >
                          auto-assigned
                        </Badge>
                      )}
                      {task.review_required && (
                        <Badge
                          variant="outline"
                          className="border-purple-500/30 text-purple-400 text-xs"
                        >
                          review
                        </Badge>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
