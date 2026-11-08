import React from 'react';
import {
  Bell,
  Clock,
  Building,
  RefreshCw,
  Cpu,
} from 'lucide-react';
import { User } from '../types';

interface NavbarProps {
  user: User | null;
  organizationName: string;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  organizationName,
  onRefresh,
  isRefreshing,
}) => {
  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/60 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Left: Organization context & Data Freshness Indicator */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/80">
          <Building className="w-3.5 h-3.5 text-sky-400" />
          <span className="text-xs font-semibold text-slate-200">{organizationName || 'ReconOS Tenant'}</span>
        </div>

        <div className="hidden md:flex items-center gap-2 text-xs text-slate-400">
          <Clock className="w-3.5 h-3.5 text-emerald-400" />
          <span>Data from recorded statements</span>
        </div>
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-3">
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 rounded-lg transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-sky-400' : ''}`} />
            <span>Refresh</span>
          </button>
        )}

        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[11px] font-medium text-indigo-300">
          <Cpu className="w-3 h-3 text-indigo-400 animate-pulse" />
          <span>AI Engine Active</span>
        </div>

        <div className="w-8 h-8 rounded-lg bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400 hover:text-slate-200 cursor-pointer transition">
          <Bell className="w-4 h-4" />
        </div>
      </div>
    </header>
  );
};
