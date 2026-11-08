import React, { useState, useEffect } from 'react';
import {
  GitCompare,
  Play,
  CheckCircle,
  XCircle,
  AlertCircle,
  FileCheck,
  Plus,
  ArrowRight,
  ShieldCheck,
  Check,
  Filter,
} from 'lucide-react';
import { ApiClient } from '../api';
import { ReconciliationSession, FinancialAccount, User } from '../types';

export const ReconciliationPage: React.FC<{ user: User }> = ({ user }) => {
  const [sessions, setSessions] = useState<ReconciliationSession[]>([]);
  const [accounts, setAccounts] = useState<FinancialAccount[]>([]);
  const [selectedSession, setSelectedSession] = useState<ReconciliationSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // New Session Form State
  const [sessionName, setSessionName] = useState('');
  const [primaryAccountId, setPrimaryAccountId] = useState('');
  const [secondaryAccountId, setSecondaryAccountId] = useState('');
  const [toleranceDays, setToleranceDays] = useState(2);
  const [allowOneToMany, setAllowOneToMany] = useState(true);
  const [allowManyToOne, setAllowManyToOne] = useState(true);

  // Manual Match selection
  const [selectedPrimaryTxIds, setSelectedPrimaryTxIds] = useState<string[]>([]);
  const [selectedSecondaryTxIds, setSelectedSecondaryTxIds] = useState<string[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [sessionsData, accountsData] = await Promise.all([
        ApiClient.get('/reconciliation/sessions'),
        ApiClient.get('/accounts'),
      ]);
      setSessions(sessionsData);
      setAccounts(accountsData);
      if (sessionsData.length > 0 && !selectedSession) {
        setSelectedSession(sessionsData[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSession = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!primaryAccountId || !secondaryAccountId) return;

    try {
      const newSession = await ApiClient.post('/reconciliation/sessions', {
        session_name: sessionName,
        primary_account_id: primaryAccountId,
        secondary_account_id: secondaryAccountId,
        date_from: new Date(Date.now() - 30 * 86400000).toISOString(),
        date_to: new Date().toISOString(),
        rule_config: {
          exact_reference_match: true,
          date_tolerance_days: toleranceDays,
          allow_one_to_many: allowOneToMany,
          allow_many_to_one: allowManyToOne,
        },
      });
      setSessions([newSession, ...sessions]);
      setSelectedSession(newSession);
      setShowCreateModal(false);
      setSessionName('');
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleExecute = async () => {
    if (!selectedSession) return;
    setExecuting(true);
    try {
      const updated = await ApiClient.post(`/reconciliation/sessions/${selectedSession.id}/execute`);
      setSelectedSession(updated);
      setSessions(sessions.map((s) => (s.id === updated.id ? updated : s)));
    } catch (e: any) {
      alert(e.message);
    } finally {
      setExecuting(false);
    }
  };

  const handleDecision = async (matchId: string, action: 'CONFIRM' | 'REJECT') => {
    if (!selectedSession) return;
    try {
      const updated = await ApiClient.post(
        `/reconciliation/sessions/${selectedSession.id}/matches/${matchId}/decision`,
        { action }
      );
      setSelectedSession(updated);
      setSessions(sessions.map((s) => (s.id === updated.id ? updated : s)));
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleApprove = async () => {
    if (!selectedSession) return;
    try {
      const updated = await ApiClient.post(`/reconciliation/sessions/${selectedSession.id}/approve`, {
        notes: 'Formally approved by Finance Manager',
      });
      setSelectedSession(updated);
      setSessions(sessions.map((s) => (s.id === updated.id ? updated : s)));
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header and Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-sky-400" />
            Financial Reconciliation Workspace
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Deterministic multi-channel matching, tolerance clustering, and manager approvals.
          </p>
        </div>
        {user.role !== 'auditor' && <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-lg shadow-sky-600/30 transition"
        >
          <Plus className="w-4 h-4" />
          <span>New Reconciliation Session</span>
        </button>}
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left: Sessions list */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 space-y-3">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
            Sessions History
          </div>
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {sessions.map((s) => (
              <div
                key={s.id}
                onClick={() => setSelectedSession(s)}
                className={`p-3 rounded-xl cursor-pointer border transition text-left ${
                  selectedSession?.id === s.id
                    ? 'bg-sky-500/10 border-sky-500/40 text-white'
                    : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold truncate">{s.session_name}</span>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold ${
                      s.status === 'APPROVED'
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : s.status === 'COMPLETED'
                        ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {s.status}
                  </span>
                </div>
                <div className="flex justify-between items-center text-[11px] text-slate-500 mt-2 font-mono">
                  <span>{s.matched_count} matches</span>
                  <span className="text-emerald-400 font-semibold">{s.reconciliation_rate}%</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Selected Session Details & Matches */}
        <div className="lg:col-span-3 space-y-6">
          {selectedSession ? (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6">
              {/* Session Top KPI Bar */}
              <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
                <div>
                  <div className="flex items-center gap-3">
                    <h2 className="text-lg font-bold text-white">{selectedSession.session_name}</h2>
                    <span className="text-xs px-2.5 py-0.5 rounded-full font-mono bg-slate-800 text-slate-300 border border-slate-700">
                      ID: {selectedSession.id.slice(0, 8)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Created on {new Date(selectedSession.created_at).toLocaleDateString()} &bull; Primary vs Secondary
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  {user.role !== 'auditor' && selectedSession.status === 'DRAFT' && (
                    <button
                      onClick={handleExecute}
                      disabled={executing}
                      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>{executing ? 'Executing Rules...' : 'Run Engine'}</span>
                    </button>
                  )}
                  {['owner', 'finance_manager'].includes(user.role) && selectedSession.status === 'COMPLETED' && (
                    <button
                      onClick={handleApprove}
                      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-600/30 transition"
                    >
                      <ShieldCheck className="w-4 h-4" />
                      <span>Approve Session</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
                  <span className="text-[11px] text-slate-500 uppercase font-medium">Reconciliation Rate</span>
                  <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
                    {selectedSession.reconciliation_rate}%
                  </div>
                </div>
                <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
                  <span className="text-[11px] text-slate-500 uppercase font-medium">Matched Volume</span>
                  <div className="text-xl font-bold font-mono text-white mt-1">
                    ${parseFloat(selectedSession.matched_amount || '0').toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </div>
                </div>
                <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
                  <span className="text-[11px] text-slate-500 uppercase font-medium">Discrepancy Volume</span>
                  <div className="text-xl font-bold font-mono text-amber-400 mt-1">
                    ${parseFloat(selectedSession.discrepancy_amount || '0').toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </div>
                </div>
                <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
                  <span className="text-[11px] text-slate-500 uppercase font-medium">Matched Pairs</span>
                  <div className="text-xl font-bold font-mono text-sky-400 mt-1">
                    {selectedSession.matched_count} Pairs
                  </div>
                </div>
              </div>

              {/* Match Results Table */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-slate-200">Reconciled Match Participants</h3>
                {selectedSession.matches.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 text-sm bg-slate-950/40 rounded-xl border border-dashed border-slate-800">
                    No match results yet. Click "Run Engine" to trigger deterministic rule-based matching.
                  </div>
                ) : (
                  <div className="divide-y divide-slate-800 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/50">
                    {selectedSession.matches.map((m) => (
                      <div key={m.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono font-bold text-sky-400">
                              [{m.match_type.replace(/_/g, ' ')}]
                            </span>
                            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              {m.confidence_score}% Confidence
                            </span>
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                                m.status === 'CONFIRMED'
                                  ? 'bg-emerald-500/20 text-emerald-300'
                                  : m.status === 'SUGGESTED'
                                  ? 'bg-amber-500/20 text-amber-300'
                                  : 'bg-rose-500/20 text-rose-300'
                              }`}
                            >
                              {m.status}
                            </span>
                          </div>
                          <p className="text-xs text-slate-400">{m.notes}</p>
                          <div className="flex items-center gap-4 text-xs font-mono text-slate-400 mt-2">
                            <span>Primary Total: ${parseFloat(m.primary_amount_total).toFixed(2)}</span>
                            <ArrowRight className="w-3 h-3 text-slate-600" />
                            <span>Secondary Total: ${parseFloat(m.secondary_amount_total).toFixed(2)}</span>
                          </div>
                        </div>

                        {/* Action buttons if suggested */}
                        {user.role !== 'auditor' && selectedSession.status === 'COMPLETED' && m.status === 'SUGGESTED' && (
                          <div className="flex items-center gap-2">
                            {parseFloat(m.difference_amount) === 0 && <button
                              onClick={() => handleDecision(m.id, 'CONFIRM')}
                              className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition"
                            >
                              Confirm
                            </button>}
                            {parseFloat(m.difference_amount) !== 0 && <span className="text-xs text-amber-300">Unequal amounts require partial allocation, which is not yet supported.</span>}
                            <button
                              onClick={() => handleDecision(m.id, 'REJECT')}
                              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-rose-600 text-slate-300 hover:text-white text-xs font-semibold transition"
                            >
                              Reject
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-12 text-center text-slate-500">
              Select or create a reconciliation session to view the workspace.
            </div>
          )}
        </div>
      </div>

      {/* Modal: Create Session */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-lg space-y-4 shadow-2xl">
            <h2 className="text-lg font-bold text-white">Create Reconciliation Session</h2>
            <form onSubmit={handleCreateSession} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Session Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. October 2026 Stanbic vs Sales Ledger"
                  value={sessionName}
                  onChange={(e) => setSessionName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Primary Account (Internal/ERP)</label>
                  <select
                    required
                    value={primaryAccountId}
                    onChange={(e) => setPrimaryAccountId(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-sky-500"
                  >
                    <option value="">Select Account</option>
                    {accounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name} ({a.provider_name})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Secondary Account (Bank/Provider)</label>
                  <select
                    required
                    value={secondaryAccountId}
                    onChange={(e) => setSecondaryAccountId(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-sky-500"
                  >
                    <option value="">Select Account</option>
                    {accounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name} ({a.provider_name})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Date Tolerance (Days)</label>
                  <input
                    type="number"
                    min="0"
                    max="14"
                    value={toleranceDays}
                    onChange={(e) => setToleranceDays(parseInt(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div className="flex items-center gap-2 pt-6">
                  <input
                    type="checkbox"
                    id="o2m"
                    checked={allowOneToMany}
                    onChange={(e) => setAllowOneToMany(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-700 text-sky-500"
                  />
                  <label htmlFor="o2m" className="text-xs text-slate-300">
                    One primary to several secondary entries
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <input type="checkbox" id="m2o" checked={allowManyToOne}
                    onChange={(e) => setAllowManyToOne(e.target.checked)}
                    className="rounded bg-slate-950 border-slate-700 text-sky-500" />
                  <label htmlFor="m2o" className="text-xs text-slate-300">Several primary entries to one secondary</label>
                </div>
              </div>
              <p className="text-xs text-slate-400">Aggregate matches are suggestions that require review. Large candidate groups may need manual review.</p>

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-sky-600 text-white text-xs font-semibold hover:bg-sky-500 transition"
                >
                  Create Session
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
