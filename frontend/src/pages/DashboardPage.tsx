import React from 'react';
import {
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Wallet,
  ArrowUpRight,
  ShieldAlert,
  Building,
  CreditCard,
  Sparkles,
} from 'lucide-react';

interface DashboardPageProps {
  analytics: any;
  onNavigate: (page: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ analytics, onNavigate }) => {
  if (analytics?.scope === 'employee') {
    return (
      <div className="space-y-6">
        <div><h1 className="text-2xl font-bold text-white">My shifts</h1>
          <p className="text-sm text-slate-400 mt-1">Your ten most recent submitted shift summaries.</p></div>
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
          {analytics.shifts.length === 0 ? <p className="text-slate-400 text-sm">No shift summaries submitted yet.</p> :
            analytics.shifts.map((shift: any) => <div key={shift.id} className="flex flex-wrap justify-between gap-3 border-b border-slate-800 py-3 text-sm text-slate-200">
              <span>{shift.date} · Shift {shift.shift_number}</span><span>{shift.status.replace(/_/g, ' ')}</span>
              <span>Discrepancy: {shift.cash_discrepancy}</span>
              {shift.supervisor_notes && <span className="w-full text-sky-300">Supervisor: {shift.supervisor_notes}</span>}</div>)}
          <p className="text-xs text-slate-400">{analytics.notice}</p>
          <button onClick={() => onNavigate('shifts')} className="text-sm text-sky-400">Open shift summaries →</button>
        </div>
      </div>
    );
  }
  const kpis = analytics?.kpis || {
    total_recorded_balance: '0.00',
    reconciliation_rate_percent: 0,
    total_transactions: 0,
    total_volume: '0.00',
    matched_transactions: 0,
    matched_volume: '0.00',
    unmatched_transactions: 0,
    unmatched_volume: '0.00',
    open_exceptions_count: 0,
    open_exceptions_volume: '0.00',
    shift_float_variance_total: '0.00',
  };

  const accounts = analytics?.accounts || [];
  const branches = analytics?.branches || [];
  const channels = analytics?.channels || [];
  const dailyTrend = analytics?.daily_trend || [];

  if (['finance_manager', 'accountant', 'auditor'].includes(analytics?.role)) {
    return (
      <div className="space-y-6">
        <div><h1 className="text-2xl font-bold text-white">Finance Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">Organization-wide recorded {kpis.currency} transactions; other currencies are excluded.</p></div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5"><p className="text-slate-400 text-xs">Reconciled transactions</p><p className="text-xl font-bold text-white mt-2">{kpis.matched_transactions} / {kpis.total_transactions}</p></div>
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5"><p className="text-slate-400 text-xs">Unmatched recorded amount</p><p className="text-xl font-bold text-amber-400 mt-2">{kpis.currency} {kpis.unmatched_volume}</p></div>
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5"><p className="text-slate-400 text-xs">Open exceptions in {kpis.currency}</p><p className="text-xl font-bold text-white mt-2">{kpis.open_exceptions_count}</p></div>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
          <h2 className="text-white font-semibold">Finance workspace</h2>
          <p className="text-sm text-slate-400">Review recorded transactions, reconciliation matches and open exceptions. Financial journals and settlement accounts are not yet available.</p>
          <div className="flex flex-wrap gap-3">{[['reconciliation', 'Reconciliation'], ['exceptions', 'Exceptions'], ['reports', 'Reports']].map(([page, label]) =>
            <button key={page} onClick={() => onNavigate(page)} className="px-4 py-2 rounded-lg bg-slate-800 text-sky-300 text-sm">{label} →</button>)}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner / Welcome */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 bg-gradient-to-r from-slate-900 via-sky-950/40 to-slate-900 p-6 rounded-2xl border border-sky-500/20 shadow-xl">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            {analytics?.scope === 'branch' ? `${analytics.branch_name} — Branch Dashboard` :
              ['finance_manager', 'accountant', 'auditor'].includes(analytics?.role) ? 'Finance Dashboard' : 'Owner Dashboard'}
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/30">
              Recorded data
            </span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            {analytics?.scope === 'branch' ? 'This branch only. ' : 'Organization-wide. '}
            Statement-based data. Totals cover {kpis.currency || "the reporting currency"} only; no conversion is applied.
          </p>
        </div>
        {analytics?.scope !== 'branch' && <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigate('ingestion')}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition shadow-sm"
          >
            Upload Statement
          </button>
          <button
            onClick={() => onNavigate('reconciliation')}
            className="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-lg shadow-sky-600/30 transition"
          >
            Run Reconciliation
          </button>
        </div>}
      </div>

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Balance */}
        <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Recorded Balance</span>
            <div className="w-8 h-8 rounded-lg bg-sky-500/10 text-sky-400 flex items-center justify-center">
              <Wallet className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-white font-mono">
              {kpis.currency} {parseFloat(kpis.total_recorded_balance || '0').toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </div>
            <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
              <span>Recorded balances in {kpis.currency}</span>
            </div>
          </div>
        </div>

        {/* Card 2: Recon Rate */}
        <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Reconciliation Rate</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-emerald-400 font-mono">
              {kpis.reconciliation_rate_percent}%
            </div>
            <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
              <span>{kpis.matched_transactions} of {kpis.total_transactions} txs matched</span>
            </div>
          </div>
        </div>

        {/* Card 3: Discrepancies / Unmatched */}
        <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Unmatched Discrepancy</span>
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-amber-400 font-mono">
              {kpis.currency} {parseFloat(kpis.unmatched_volume || '0').toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </div>
            <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
              <span>{kpis.unmatched_transactions} items awaiting resolution</span>
            </div>
          </div>
        </div>

        {/* Card 4: Open Exceptions */}
        <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Exception Cases</span>
            <div className="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-400 flex items-center justify-center">
              <ShieldAlert className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-rose-400 font-mono">
              {kpis.open_exceptions_count} Cases
            </div>
            <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
              <span>{kpis.currency} {parseFloat(kpis.open_exceptions_volume || '0').toLocaleString('en-US', { minimumFractionDigits: 2 })} exposure</span>
            </div>
          </div>
        </div>
      </div>

      {/* Middle Row: Accounts Summary & Payment Channel Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Connected Accounts */}
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-semibold text-white">Financial Accounts & Statement Balances</h2>
              <p className="text-xs text-slate-400">Statement-derived ledger balances across all registered providers</p>
            </div>
            <button
              onClick={() => onNavigate('accounts')}
              className="text-xs text-sky-400 hover:text-sky-300 font-medium flex items-center gap-1"
            >
              Manage Accounts <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="divide-y divide-slate-800/80">
            {accounts.map((acc: any) => (
              <div key={acc.id} className="py-3 flex items-center justify-between hover:bg-slate-800/20 px-2 rounded-lg transition">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300">
                    {acc.type === 'BANK' ? <Building className="w-4 h-4 text-sky-400" /> : <CreditCard className="w-4 h-4 text-emerald-400" />}
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-slate-200">{acc.name}</h3>
                    <p className="text-xs text-slate-500 font-mono">{acc.provider} &bull; {acc.account_number}</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-sm font-semibold text-white font-mono">
                    {parseFloat(acc.balance).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </span>
                  <span className="block text-[11px] text-slate-500">{acc.currency}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Payment Channels Breakdown */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-semibold text-white">Channel Match Rates</h2>
              <p className="text-xs text-slate-400">Performance across gateways & banks</p>
            </div>
            <Sparkles className="w-4 h-4 text-purple-400" />
          </div>

          <div className="space-y-4">
            {channels.map((ch: any) => (
              <div key={ch.channel} className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-semibold text-slate-300">{ch.channel}</span>
                  <span className="text-xs font-mono font-bold text-sky-400">{ch.match_rate}%</span>
                </div>
                {/* Progress bar */}
                <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-sky-500 to-indigo-500 h-1.5 rounded-full"
                    style={{ width: `${Math.min(100, ch.match_rate)}%` }}
                  />
                </div>
                <div className="flex justify-between items-center text-[11px] text-slate-500 mt-2 font-mono">
                  <span>{ch.transaction_count} transactions</span>
                  <span>{kpis.currency} {parseFloat(ch.total_volume).toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Row: Branch Performance & Float Accountability */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Branch Operations */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-semibold text-white">Branch Reconciliation Coverage</h2>
              <p className="text-xs text-slate-400">Operating branch efficiency and volume</p>
            </div>
            {analytics?.scope !== 'branch' && <button
              onClick={() => onNavigate('branches')}
              className="text-xs text-sky-400 hover:text-sky-300 font-medium flex items-center gap-1"
            >
              View Branches <ArrowUpRight className="w-3.5 h-3.5" />
            </button>}
          </div>

          <div className="space-y-3">
            {branches.map((b: any) => (
              <div key={b.id} className="p-3 bg-slate-950/50 border border-slate-800/80 rounded-xl flex items-center justify-between">
                <div>
                  <div className="text-sm font-medium text-slate-200">{b.name}</div>
                  <div className="text-xs text-slate-500 font-mono">Code: {b.code}</div>
                </div>
                <div className="text-right">
                  <span className="text-xs font-bold text-emerald-400 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                    {b.reconciliation_rate}% Reconciled
                  </span>
                  <div className="text-[11px] text-slate-500 mt-1">{b.total_transactions} txs</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Cash Float Status */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-base font-semibold text-white">Cash Drawer & Float Integrity</h2>
              <span className="text-xs font-medium px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                Shift Auditing
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Daily cashier opening float vs physical counted cash vs recorded POS and mobile sales.
            </p>

            <div className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Total Shift Float Variance:</span>
                <span className="text-slate-400">Unavailable: shift currency is not recorded</span>
              </div>
              <div className="text-xs text-slate-500">
                Mathematical equation: <code className="text-sky-400">Opening + Sales - Payouts = Expected Closing</code>
              </div>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-slate-800 flex justify-end">
            <button
              onClick={() => onNavigate('shifts')}
              className="text-xs font-semibold px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 transition"
            >
              Open Shift Summaries &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
