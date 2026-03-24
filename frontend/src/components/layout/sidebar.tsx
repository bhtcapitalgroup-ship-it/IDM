"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: "grid" },
  { href: "/operations", label: "Operations", icon: "activity" },
  { href: "/orchestrator", label: "Orchestrator", icon: "zap" },
  { href: "/agents", label: "Agents", icon: "bot" },
  { href: "/tasks", label: "Tasks", icon: "list" },
  { href: "/conversations", label: "Conversations", icon: "msg" },
  { href: "/artifacts", label: "Artifacts", icon: "file" },
  { href: "/prompts", label: "Prompts", icon: "file" },
  { href: "/tools", label: "Tools", icon: "wrench" },
  { href: "/memory", label: "Memory", icon: "brain" },
  { href: "/trader-eval", label: "Trader Eval", icon: "chart" },
  { href: "/approvals", label: "Approvals", icon: "shield" },
  { href: "/audit", label: "Audit Log", icon: "scroll" },
];

const iconMap: Record<string, string> = {
  grid: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
  activity: "M22 12h-4l-3 9L9 3l-3 9H2",
  msg: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
  zap: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
  bot: "M12 2a2 2 0 0 1 2 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 0 1 7 7h1a1 1 0 0 1 0 2h-1v1a7 7 0 0 1-7 7H9a7 7 0 0 1-7-7v-1H1a1 1 0 0 1 0-2h1a7 7 0 0 1 7-7h1V5.73A2 2 0 0 1 12 2zM9 14a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm6 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2z",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  file: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M16 13H8M16 17H8M10 9H8",
  wrench: "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z",
  brain: "M12 2a7 7 0 0 0-7 7c0 3 2 5.5 5 6.5V22h4v-6.5c3-1 5-3.5 5-6.5a7 7 0 0 0-7-7z",
  chart: "M18 20V10M12 20V4M6 20v-6",
  shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
  scroll: "M8 21h12a2 2 0 0 0 2-2v-2H10v2a2 2 0 1 1-4 0V5a2 2 0 0 1 2-2h14v14",
};

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="w-64 min-h-screen bg-zinc-950 border-r border-zinc-800 flex flex-col">
      <div className="p-6 border-b border-zinc-800">
        <h1 className="text-lg font-bold text-white tracking-tight">Agentic Builder</h1>
        <p className="text-xs text-zinc-500 mt-1">Company Operating System</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
              pathname === item.href || pathname?.startsWith(item.href + "/")
                ? "bg-zinc-800 text-white"
                : "text-zinc-400 hover:text-white hover:bg-zinc-900"
            )}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d={iconMap[item.icon]} />
            </svg>
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="p-4 border-t border-zinc-800 space-y-3">
        {user && (
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <p className="text-sm text-zinc-300 truncate">{user.full_name}</p>
              <p className="text-xs text-zinc-600 truncate">{user.email}</p>
            </div>
            <button
              onClick={logout}
              className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors shrink-0 ml-2"
            >
              Logout
            </button>
          </div>
        )}
        <div className="text-xs text-zinc-600">v0.1.0 | local</div>
      </div>
    </aside>
  );
}
