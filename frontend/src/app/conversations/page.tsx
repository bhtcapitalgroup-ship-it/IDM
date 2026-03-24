"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api, type CollabThread, type CollabMessage } from "@/lib/api";

const msgTypeColor: Record<string, string> = {
  clarification: "border-blue-500/30 text-blue-400",
  handoff: "border-purple-500/30 text-purple-400",
  review: "border-amber-500/30 text-amber-400",
  escalation: "border-red-500/30 text-red-400",
  status_update: "border-zinc-600 text-zinc-400",
};

export default function ConversationsPage() {
  const [threads, setThreads] = useState<CollabThread[]>([]);
  const [selected, setSelected] = useState<CollabThread | null>(null);
  const [messages, setMessages] = useState<CollabMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [newMsg, setNewMsg] = useState("");
  const [msgType, setMsgType] = useState("status_update");

  useEffect(() => {
    api.listThreads().then(setThreads).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selected) {
      api.listMessages(selected.id).then(setMessages);
    }
  }, [selected]);

  const handleSend = async () => {
    if (!selected || !newMsg.trim()) return;
    await api.sendMessage({ thread_id: selected.id, message_type: msgType, content: newMsg.trim() });
    setNewMsg("");
    api.listMessages(selected.id).then(setMessages);
  };

  const handleCreateThread = async () => {
    const title = prompt("Thread title:");
    if (!title) return;
    const thread = await api.createThread({ title });
    setThreads((prev) => [thread, ...prev]);
    setSelected(thread);
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Conversations</h1>
          <p className="text-zinc-500 text-sm mt-1">Agent-to-agent and team communication threads</p>
        </div>
        <Button onClick={handleCreateThread}>New Thread</Button>
      </div>

      <div className="grid grid-cols-3 gap-6 min-h-[600px]">
        {/* Thread list */}
        <Card className="bg-zinc-900 border-zinc-800 col-span-1 overflow-auto">
          <CardContent className="p-0">
            {loading ? (
              <div className="p-4 text-zinc-600 text-sm">Loading...</div>
            ) : threads.length === 0 ? (
              <div className="p-4 text-zinc-600 text-sm">No threads yet</div>
            ) : (
              threads.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setSelected(t)}
                  className={`w-full text-left px-4 py-3 border-b border-zinc-800 hover:bg-zinc-800/50 transition-colors ${
                    selected?.id === t.id ? "bg-zinc-800" : ""
                  }`}
                >
                  <p className="text-sm text-zinc-200 truncate">{t.title}</p>
                  <p className="text-xs text-zinc-600 mt-1">{new Date(t.updated_at).toLocaleString()}</p>
                </button>
              ))
            )}
          </CardContent>
        </Card>

        {/* Message view */}
        <Card className="bg-zinc-900 border-zinc-800 col-span-2 flex flex-col">
          {!selected ? (
            <CardContent className="flex-1 flex items-center justify-center">
              <p className="text-zinc-600 text-sm">Select a thread to view messages</p>
            </CardContent>
          ) : (
            <>
              <CardHeader className="border-b border-zinc-800">
                <CardTitle className="text-sm">{selected.title}</CardTitle>
              </CardHeader>
              <CardContent className="flex-1 overflow-auto p-4 space-y-3">
                {messages.length === 0 ? (
                  <p className="text-zinc-600 text-sm">No messages yet</p>
                ) : (
                  messages.map((m) => (
                    <div key={m.id} className="flex gap-3">
                      <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-xs text-zinc-500 shrink-0">
                        {m.sender_agent_id ? "A" : "U"}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant="outline" className={msgTypeColor[m.message_type] || msgTypeColor.status_update}>
                            {m.message_type.replace(/_/g, " ")}
                          </Badge>
                          <span className="text-xs text-zinc-600">{new Date(m.created_at).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-sm text-zinc-300">{m.content}</p>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
              <div className="border-t border-zinc-800 p-4 space-y-2">
                <div className="flex gap-2">
                  <select value={msgType} onChange={(e) => setMsgType(e.target.value)} className="rounded-md bg-zinc-800 border border-zinc-700 px-2 py-1 text-xs text-zinc-100">
                    <option value="status_update">Status Update</option>
                    <option value="clarification">Clarification</option>
                    <option value="review">Review</option>
                    <option value="escalation">Escalation</option>
                    <option value="handoff">Handoff</option>
                  </select>
                  <Input value={newMsg} onChange={(e) => setNewMsg(e.target.value)} placeholder="Type a message..." className="bg-zinc-800 border-zinc-700 flex-1" onKeyDown={(e) => e.key === "Enter" && handleSend()} />
                  <Button onClick={handleSend} disabled={!newMsg.trim()}>Send</Button>
                </div>
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
