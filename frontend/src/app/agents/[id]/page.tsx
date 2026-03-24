"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { api, type Agent } from "@/lib/api";

export default function AgentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState(false);

  const id = params.id as string;

  useEffect(() => {
    api
      .getAgent(id)
      .then(setAgent)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const toggleStatus = async () => {
    if (!agent) return;
    setToggling(true);
    try {
      const newStatus = agent.status === "active" ? "inactive" : "active";
      const updated = await api.updateAgent(id, { status: newStatus });
      setAgent(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update status");
    } finally {
      setToggling(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-zinc-500 text-sm">Loading agent...</div>;
  }

  if (error || !agent) {
    return (
      <div className="p-8">
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error || "Agent not found"}
        </div>
        <Button variant="outline" className="mt-4" onClick={() => router.push("/agents")}>
          Back to Agents
        </Button>
      </div>
    );
  }

  const statusColor =
    agent.status === "active"
      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
      : "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={() => router.push("/agents")}
            className="text-xs text-zinc-500 hover:text-zinc-300 mb-2 block"
          >
            &larr; Back to Agents
          </button>
          <h1 className="text-2xl font-bold">{agent.name}</h1>
          <p className="text-zinc-500 text-sm mt-1">{agent.description || "No description"}</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge className={statusColor}>{agent.status}</Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={toggleStatus}
            disabled={toggling}
          >
            {toggling
              ? "Updating..."
              : agent.status === "active"
                ? "Deactivate"
                : "Activate"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Core Info */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400">Agent Info</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Field label="Role" value={agent.role.replace(/_/g, " ")} />
            <Field label="Type" value={agent.type} />
            <Field label="Version" value={agent.version} />
            <Field label="Memory Scope" value={agent.memory_scope} />
            <Field label="Created By" value={agent.creation_source} />
            <Field label="Owner" value={agent.owner || "Unassigned"} />
            <Field label="Created" value={new Date(agent.created_at).toLocaleString()} />
            <Field label="Updated" value={new Date(agent.updated_at).toLocaleString()} />
          </CardContent>
        </Card>

        {/* Permissions */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400">Permissions</CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(agent.permissions).length === 0 ? (
              <p className="text-zinc-600 text-sm">No permissions defined</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {Object.entries(agent.permissions).map(([key, val]) => (
                  <Badge
                    key={key}
                    variant="outline"
                    className={
                      val
                        ? "border-emerald-500/30 text-emerald-400"
                        : "border-zinc-700 text-zinc-500"
                    }
                  >
                    {key.replace(/_/g, " ")}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Tools */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400">Tools</CardTitle>
          </CardHeader>
          <CardContent>
            {agent.tools.length === 0 ? (
              <p className="text-zinc-600 text-sm">No tools assigned</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {agent.tools.map((tool) => (
                  <Badge key={tool} variant="outline" className="border-blue-500/30 text-blue-400">
                    {tool.replace(/_/g, " ")}
                  </Badge>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Config */}
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-400">Configuration</CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(agent.config).length === 0 ? (
              <p className="text-zinc-600 text-sm">No custom configuration</p>
            ) : (
              <pre className="text-xs text-zinc-400 bg-zinc-800 p-3 rounded-lg overflow-auto">
                {JSON.stringify(agent.config, null, 2)}
              </pre>
            )}
          </CardContent>
        </Card>
      </div>

      <Separator className="bg-zinc-800" />

      <div className="text-xs text-zinc-600">
        ID: {agent.id}
      </div>
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
