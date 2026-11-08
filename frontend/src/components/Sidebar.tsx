import React from 'react';
import {
  LayoutDashboard,
  GitCompare,
  UploadCloud,
  FileSpreadsheet,
  AlertTriangle,
  Sparkles,
  Coins,
  Building2,
  GitBranch,
  FileText,
  History,
  Users,
  Settings,
  ShieldCheck,
  LogOut,
} from 'lucide-react';
import { User } from '../types';

interface SidebarProps {
  currentPage: string;
  onNavigate: (page: string) => void;
  user: User | null;
  onLogout: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPage,
  onNavigate,
  user,
  onLogout,
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'reconciliation', label: 'Recon Workspace', icon: GitCompare, badge: 'Core' },
    { id: 'ingestion', label: 'Import Statements', icon: UploadCloud },
    { id: 'transactions', label: 'Transaction Explorer', icon: FileSpreadsheet },
    { id: 'exceptions', label: 'Exceptions & Cases', icon: AlertTriangle, badge: 'Alert' },
    { id: 'ai-insights', label: 'AI Investigation', icon: Sparkles, badge: 'AI' },
    { id: 'shifts', label: 'Cashier Shift Floats', icon: Coins },
    { id: 'accounts', label: 'Financial Accounts', icon: Building2 },
    { id: 'branches', label: 'Branch Network', icon: GitBranch },
    { id: 'reports', label: 'Financial Reports', icon: FileText },
    { id: 'audit', label: 'Audit Trail', icon: History },
    { id: 'team', label: 'Team & RBAC', icon: Users },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900/90 border-r border-slate-800 flex flex-col h-screen shrink-0 sticky top-0 backdrop-blur-md">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-slate-800/80 gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
          <ShieldCheck className="w-5 h-5 text-white" />
        </div>
        <div>
          <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-200 to-sky-400 bg-clip-text text-transparent">
            ReconOS AI
          </span>
          <span className="block text-[10px] font-medium text-sky-400 uppercase tracking-widest -mt-1">
            Enterprise FinOps
          </span>
        </div>
      </div>

      {/* Navigation List */}
      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        <div className="px-3 pb-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
          Operations
        </div>
        {navItems.filter((item) => {
          if (user?.role === 'operator') return ['dashboard', 'shifts'].includes(item.id);
          if (user?.role === 'branch_manager') return ['dashboard', 'shifts', 'accounts'].includes(item.id);
          if (user?.role === 'accountant') return item.id !== 'team' && item.id !== 'audit';
          if (user?.role === 'auditor') return !['team', 'ingestion'].includes(item.id);
          return true;
        }).map((item) => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30 shadow-sm shadow-sky-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-sky-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge && (
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${
                    item.badge === 'AI'
                      ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                      : item.badge === 'Alert'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* User Footer Profile */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-sky-400 shrink-0">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-semibold text-slate-200 truncate">{user?.full_name}</p>
              <span className="inline-block text-[10px] font-mono text-sky-400 uppercase tracking-wider">
                {user?.role}
              </span>
            </div>
          </div>
          <button
            onClick={onLogout}
            title="Log out"
            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800/80 transition"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
