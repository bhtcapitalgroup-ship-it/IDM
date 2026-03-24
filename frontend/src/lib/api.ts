const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function buildQuery(params?: Record<string, unknown>): string {
  if (!params) return "";
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null);
  if (entries.length === 0) return "";
  const q = new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString();
  return `?${q}`;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
    if (typeof window !== "undefined") {
      localStorage.setItem("token", token);
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== "undefined") {
      this.token = localStorage.getItem("token");
    }
    return this.token;
  }

  clearToken() {
    this.token = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
    }
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...((options.headers as Record<string, string>) || {}),
    };
    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `API error: ${res.status}`);
    }
    if (res.status === 204) return undefined as T;
    return res.json();
  }

  // Auth
  login(email: string, password: string) {
    return this.request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  seedAdmin() {
    return this.request("/api/auth/seed", { method: "POST" });
  }

  getMe() {
    return this.request<{ id: string; email: string; full_name: string; role: string }>("/api/auth/me");
  }

  // Agents
  listAgents(params?: { role?: string; status?: string }) {
    return this.request<Agent[]>(`/api/agents${buildQuery(params)}`);
  }

  getAgent(id: string) {
    return this.request<Agent>(`/api/agents/${id}`);
  }

  createAgent(data: Partial<Agent>) {
    return this.request<Agent>("/api/agents", { method: "POST", body: JSON.stringify(data) });
  }

  updateAgent(id: string, data: Partial<Agent>) {
    return this.request<Agent>(`/api/agents/${id}`, { method: "PATCH", body: JSON.stringify(data) });
  }

  deleteAgent(id: string) {
    return this.request<void>(`/api/agents/${id}`, { method: "DELETE" });
  }

  // Tasks
  listTasks(params?: { status?: string; assigned_agent_id?: string; priority?: string }) {
    return this.request<Task[]>(`/api/tasks${buildQuery(params)}`);
  }

  getTask(id: string) {
    return this.request<Task>(`/api/tasks/${id}`);
  }

  createTask(data: Partial<Task>) {
    return this.request<Task>("/api/tasks", { method: "POST", body: JSON.stringify(data) });
  }

  updateTask(id: string, data: Partial<Task>) {
    return this.request<Task>(`/api/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) });
  }

  // Approvals
  listApprovals(params?: { status?: string }) {
    return this.request<Approval[]>(`/api/approvals${buildQuery(params)}`);
  }

  createApproval(data: Partial<Approval>) {
    return this.request<Approval>("/api/approvals", { method: "POST", body: JSON.stringify(data) });
  }

  decideApproval(id: string, status: string, reason?: string) {
    return this.request<Approval>(`/api/approvals/${id}/decide`, {
      method: "POST",
      body: JSON.stringify({ status, decision_reason: reason }),
    });
  }

  // Admin
  getStats() {
    return this.request<DashboardStats>("/api/admin/stats");
  }

  getAuditLogs(params?: { limit?: number; action?: string; resource_type?: string }) {
    return this.request<AuditLog[]>(`/api/admin/audit-logs${buildQuery(params)}`);
  }

  // Orchestrator
  decomposeGoal(goal: string) {
    return this.request<DecomposeResponse>("/api/orchestrator/decompose", {
      method: "POST",
      body: JSON.stringify({ goal }),
    });
  }

  // Collaboration
  listThreads(params?: { task_id?: string }) {
    return this.request<CollabThread[]>(`/api/collab/threads${buildQuery(params)}`);
  }
  createThread(data: { title: string; task_id?: string }) {
    return this.request<CollabThread>("/api/collab/threads", { method: "POST", body: JSON.stringify(data) });
  }
  listMessages(threadId: string) {
    return this.request<CollabMessage[]>(`/api/collab/threads/${threadId}/messages`);
  }
  sendMessage(data: { thread_id: string; sender_agent_id?: string; message_type?: string; content: string }) {
    return this.request<CollabMessage>("/api/collab/messages", { method: "POST", body: JSON.stringify(data) });
  }
  listArtifacts(params?: { artifact_type?: string; task_id?: string }) {
    return this.request<CollabArtifact[]>(`/api/collab/artifacts${buildQuery(params)}`);
  }
  createArtifact(data: { title: string; artifact_type: string; content: string; creator_agent_id?: string; task_id?: string }) {
    return this.request<CollabArtifact>("/api/collab/artifacts", { method: "POST", body: JSON.stringify(data) });
  }
  updateArtifact(id: string, data: { content?: string; status?: string }) {
    return this.request<CollabArtifact>(`/api/collab/artifacts/${id}`, { method: "PATCH", body: JSON.stringify(data) });
  }
  listHandoffs(params?: { agent_id?: string; status?: string }) {
    return this.request<CollabHandoff[]>(`/api/collab/handoffs${buildQuery(params)}`);
  }
  createHandoff(data: { source_agent_id: string; target_agent_id: string; task_id?: string; reason: string; handoff_type?: string }) {
    return this.request<CollabHandoff>("/api/collab/handoffs", { method: "POST", body: JSON.stringify(data) });
  }
  resolveHandoff(id: string, status: string, notes?: string) {
    return this.request<CollabHandoff>(`/api/collab/handoffs/${id}/resolve`, { method: "POST", body: JSON.stringify({ status, notes }) });
  }
  getAgentInbox(agentId: string) {
    return this.request<AgentInbox>(`/api/collab/inbox/${agentId}`);
  }

  // Trader Eval
  listAccounts(params?: { status?: string; user_email?: string }) {
    return this.request<TradingAccount[]>(`/api/trader/accounts${buildQuery(params)}`);
  }
  getAccount(id: string) {
    return this.request<TradingAccount>(`/api/trader/accounts/${id}`);
  }
  createAccount(data: { user_email: string; account_type: string; plan: string; starting_balance: number }) {
    return this.request<TradingAccount>("/api/trader/accounts", { method: "POST", body: JSON.stringify(data) });
  }
  listTrades(accountId: string, params?: { status?: string }) {
    return this.request<TradeRecord[]>(`/api/trader/accounts/${accountId}/trades${buildQuery(params)}`);
  }
  openTrade(data: { account_id: string; symbol: string; direction: string; entry_price: number; quantity: number }) {
    return this.request<TradeRecord>("/api/trader/trades", { method: "POST", body: JSON.stringify(data) });
  }
  closeTrade(tradeId: string, exit_price: number) {
    return this.request<TradeRecord>(`/api/trader/trades/${tradeId}/close`, { method: "POST", body: JSON.stringify({ exit_price }) });
  }
  listPayouts(params?: { status?: string }) {
    return this.request<PayoutReq[]>(`/api/trader/payouts${buildQuery(params)}`);
  }
  createPayout(data: { account_id: string; amount: number; method: string }) {
    return this.request<PayoutReq>("/api/trader/payouts", { method: "POST", body: JSON.stringify(data) });
  }
  decidePayout(id: string, status: string, review_notes?: string) {
    return this.request<PayoutReq>(`/api/trader/payouts/${id}/decide`, { method: "POST", body: JSON.stringify({ status, review_notes }) });
  }
  listViolations(params?: { account_id?: string; severity?: string }) {
    return this.request<RuleViolation[]>(`/api/trader/violations${buildQuery(params)}`);
  }
  listFraudAlerts(params?: { status?: string }) {
    return this.request<FraudAlertItem[]>(`/api/trader/fraud-alerts${buildQuery(params)}`);
  }

  // Prompts
  listPrompts(params?: { category?: string; role?: string }) {
    return this.request<Prompt[]>(`/api/prompts${buildQuery(params)}`);
  }

  createPrompt(data: { name: string; template: string; category?: string; role?: string; guardrails?: Record<string, unknown> }) {
    return this.request<Prompt>("/api/prompts", { method: "POST", body: JSON.stringify(data) });
  }

  updatePrompt(id: string, data: Partial<Prompt>) {
    return this.request<Prompt>(`/api/prompts/${id}`, { method: "PATCH", body: JSON.stringify(data) });
  }

  // Tools
  listTools(params?: { role?: string }) {
    return this.request<ToolDef[]>(`/api/tools${buildQuery(params)}`);
  }

  createTool(data: { name: string; description?: string; allowed_roles?: string[]; permission_level?: string; requires_approval?: boolean }) {
    return this.request<ToolDef>("/api/tools", { method: "POST", body: JSON.stringify(data) });
  }

  updateTool(id: string, data: Partial<ToolDef>) {
    return this.request<ToolDef>(`/api/tools/${id}`, { method: "PATCH", body: JSON.stringify(data) });
  }

  // Memory
  getAgentMemory(agentId: string, params?: { scope?: string }) {
    return this.request<MemoryEntry[]>(`/api/memory/${agentId}${buildQuery(params)}`);
  }

  storeMemory(data: { agent_id: string; key: string; value: Record<string, unknown>; scope?: string; content?: string }) {
    return this.request<MemoryEntry>("/api/memory", { method: "POST", body: JSON.stringify(data) });
  }

  deleteMemory(id: string) {
    return this.request<void>(`/api/memory/${id}`, { method: "DELETE" });
  }

  // Health
  health() {
    return this.request<{ status: string; version: string }>("/api/health");
  }
}

export const api = new ApiClient();

// Types
export interface Agent {
  id: string;
  name: string;
  role: string;
  type: string;
  status: string;
  description: string | null;
  permissions: Record<string, unknown>;
  tools: string[];
  version: string;
  owner: string | null;
  memory_scope: string;
  creation_source: string;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  parent_task_id: string | null;
  assigned_agent_id: string | null;
  created_by: string;
  priority: string;
  status: string;
  dependencies: string[];
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  review_required: boolean;
  retry_count: number;
  max_retries: number;
  created_at: string;
  updated_at: string;
}

export interface Approval {
  id: string;
  task_id: string | null;
  action_type: string;
  description: string | null;
  requested_by: string;
  reviewed_by: string | null;
  status: string;
  payload: Record<string, unknown>;
  decision_reason: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface AuditLog {
  id: string;
  actor: string;
  actor_type: string;
  action: string;
  resource_type: string;
  resource_id: string;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  metadata_: Record<string, unknown>;
  created_at: string;
}

export interface DashboardStats {
  total_agents: number;
  total_tasks: number;
  pending_approvals: number;
  tasks_by_status: Record<string, number>;
}

export interface DecomposeResponse {
  parent_task: Task;
  subtasks: Task[];
  plan: { summary: string; rationale: string };
  ai_metadata: Record<string, unknown>;
}

export interface Prompt {
  id: string;
  name: string;
  category: string;
  role: string | null;
  template: string;
  output_schema: Record<string, unknown> | null;
  guardrails: Record<string, unknown>;
  version: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ToolDef {
  id: string;
  name: string;
  description: string | null;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  allowed_roles: string[];
  permission_level: string;
  environment_access: string[];
  requires_approval: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MemoryEntry {
  id: string;
  agent_id: string;
  scope: string;
  scope_id: string | null;
  key: string;
  value: Record<string, unknown>;
  content: string | null;
  created_at: string;
  updated_at: string;
}

export interface TradingAccount {
  id: string; user_email: string; account_type: string; plan: string; status: string;
  starting_balance: number; current_balance: number;
  max_drawdown_pct: number; daily_loss_limit_pct: number; profit_target_pct: number;
  trading_days: number; min_trading_days: number; rules: Record<string, unknown>;
  created_at: string; updated_at: string; expires_at: string | null;
}

export interface TradeRecord {
  id: string; account_id: string; symbol: string; direction: string;
  entry_price: number; exit_price: number | null; quantity: number; pnl: number;
  status: string; opened_at: string; closed_at: string | null;
}

export interface PayoutReq {
  id: string; account_id: string; amount: number; method: string; status: string;
  reviewed_by: string | null; review_notes: string | null; fraud_flags: unknown[];
  created_at: string; reviewed_at: string | null; paid_at: string | null;
}

export interface RuleViolation {
  id: string; account_id: string; rule_type: string; description: string;
  severity: string; auto_action: string | null; resolved: boolean; details: Record<string, unknown>;
  detected_at: string;
}

export interface FraudAlertItem {
  id: string; account_id: string; alert_type: string; risk_score: number;
  description: string; evidence: Record<string, unknown>; status: string;
  reviewed_by: string | null; created_at: string; resolved_at: string | null;
}

export interface CollabThread {
  id: string; title: string; task_id: string | null; status: string;
  created_by: string; created_at: string; updated_at: string;
}
export interface CollabMessage {
  id: string; thread_id: string; sender_agent_id: string | null;
  sender_user_id: string | null; message_type: string; content: string;
  metadata_: Record<string, unknown>; created_at: string;
}
export interface CollabArtifact {
  id: string; title: string; artifact_type: string; status: string; version: number;
  content: string; creator_agent_id: string | null; task_id: string | null;
  thread_id: string | null; metadata_: Record<string, unknown>;
  created_at: string; updated_at: string;
}
export interface CollabHandoff {
  id: string; source_agent_id: string; target_agent_id: string;
  task_id: string | null; artifact_id: string | null; reason: string;
  handoff_type: string; status: string; notes: string | null;
  created_at: string; resolved_at: string | null;
}
export interface AgentInbox {
  assigned_tasks: number; pending_messages: number; pending_handoffs: number;
  pending_reviews: number; blocked_tasks: number;
}
