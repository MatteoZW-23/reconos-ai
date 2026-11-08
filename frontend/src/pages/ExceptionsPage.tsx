import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  Sparkles,
  ShieldAlert,
  Clock,
  CheckCircle,
  ArrowRight,
  UserCheck,
  Search,
} from 'lucide-react';
import { ApiClient } from '../api';
import { ExceptionCase, InvestigationBriefing, User } from '../types';

export const ExceptionsPage: React.FC<{ user: User }> = ({ user }) => {
  const [exceptions, setExceptions] = useState<ExceptionCase[]>([]);
  const [selectedCase, setSelectedCase] = useState<ExceptionCase | null>(null);
  const [briefing, setBriefing] = useState<InvestigationBriefing | null>(null);
  const [loadingBriefing, setLoadingBriefing] = useState(false);
  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [resolutionNotes, setResolutionNotes] = useState('');

  useEffect(() => {
    loadExceptions();
  }, [filterSeverity, filterStatus]);

  const loadExceptions = async () => {
    try {
      let url = '/exceptions?';
      if (filterSeverity) url += `&severity=${filterSeverity}`;
      if (filterStatus) url += `&status=${filterStatus}`;
      const data = await ApiClient.get(url);
      setExceptions(data);
      if (data.length > 0 && !selectedCase) {
        setSelectedCase(data[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSelectCase = async (c: ExceptionCase) => {
    setSelectedCase(c);
    setBriefing(null);
    if (c.transaction_id) {
      setLoadingBriefing(true);
      try {
        const brief = await ApiClient.get(`/exceptions/${c.id}/ai-investigate`);
        setBriefing(brief);
      } catch (e) {
        console.error(e);
      } finally {
        setLoadingBriefing(false);
      }
    }
  };

  const handleResolveCase = async (newStatus: 'RESOLVED' | 'ESCALATED' | 'CLOSED') => {
    if (!selectedCase) return;
    try {
      const updated = await ApiClient.patch(`/exceptions/${selectedCase.id}`, {
        status: newStatus,
        resolution_notes: resolutionNotes || 'Resolved via investigation portal',
      });
      setSelectedCase(updated);
      setExceptions(exceptions.map((ex) => (ex.id === updated.id ? updated : ex)));
      setResolutionNotes('');
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          Financial Discrepancy & Exception Cases
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Investigate missing transactions, float variances, unrecognized provider fees, and clearing timing delays.
        </p>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Cases List */}
        <div className="lg:col-span-1 bg-slate-900/80 border border-slate-800 rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Active Cases ({exceptions.length})
            </span>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="px-2 py-1 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-300"
            >
              <option value="">All Severity</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          <div className="space-y-2 max-h-[650px] overflow-y-auto">
            {exceptions.map((c) => (
              <div
                key={c.id}
                onClick={() => handleSelectCase(c)}
                className={`p-3 rounded-xl cursor-pointer border transition text-left ${
                  selectedCase?.id === c.id
                    ? 'bg-sky-500/10 border-sky-500/40 text-white'
                    : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white font-mono">{c.case_number}</span>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                      c.severity === 'CRITICAL'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        : c.severity === 'HIGH'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        : 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                    }`}
                  >
                    {c.severity}
                  </span>
                </div>
                <div className="text-xs font-medium text-slate-200 mt-1 line-clamp-1">{c.title}</div>
                <div className="flex justify-between items-center text-[11px] text-slate-500 mt-2 font-mono">
                  <span>${parseFloat(c.discrepancy_amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}</span>
                  <span className="font-sans text-[10px] uppercase text-slate-400">{c.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Case Detail & AI Investigation Briefing */}
        <div className="lg:col-span-2 space-y-6">
          {selectedCase ? (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20">
                      {selectedCase.case_number}
                    </span>
                    <span className="text-xs font-semibold text-slate-400">
                      Category: {selectedCase.category.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <h2 className="text-lg font-bold text-white mt-1">{selectedCase.title}</h2>
                </div>
                <div className="text-right">
                  <div className="text-xl font-bold font-mono text-amber-400">
                    ${parseFloat(selectedCase.discrepancy_amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </div>
                  <span className="text-[11px] text-slate-500 font-mono">Exposure Value</span>
                </div>
              </div>

              {/* Description & Evidence */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Case Background</h3>
                <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
                  {selectedCase.description}
                </p>
              </div>

              {/* AI Explainable Root-Cause Briefing */}
              <div className="p-4 rounded-xl bg-gradient-to-br from-purple-950/30 to-indigo-950/30 border border-purple-500/30 space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold text-purple-300">
                  <Sparkles className="w-4 h-4 text-purple-400" />
                  <span>Explainable AI Financial Investigation Analysis</span>
                </div>

                {loadingBriefing ? (
                  <div className="text-xs text-purple-300 animate-pulse py-3">
                    Analyzing ledger timestamps, counterparty sequences, and settlement windows...
                  </div>
                ) : briefing ? (
                  <div className="space-y-3 text-xs">
                    <div>
                      <span className="font-semibold text-slate-300">Root-Cause Hypothesis: </span>
                      <span className="text-purple-300 font-medium">{briefing.root_cause_hypothesis}</span>
                    </div>

                    <p className="text-slate-300 leading-relaxed">{briefing.plain_language_explanation}</p>

                    <div className="space-y-1 pt-1">
                      <span className="font-semibold text-slate-400 text-[11px] uppercase">Grounded Evidence:</span>
                      <ul className="list-disc list-inside text-slate-400 font-mono text-[11px] space-y-0.5">
                        {briefing.evidence_points.map((pt, i) => (
                          <li key={i}>{pt}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="p-2.5 rounded-lg bg-purple-900/30 border border-purple-500/20 text-purple-200">
                      <span className="font-semibold">Recommended Investigator Action: </span>
                      {briefing.suggested_investigator_action}
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-400">
                    No active transaction linked for real-time investigation briefing.
                  </div>
                )}
              </div>

              {/* Resolution Controls */}
              {user.role !== 'auditor' && <div className="pt-4 border-t border-slate-800 space-y-3">
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Resolution Workflow & Notes
                </label>
                <textarea
                  rows={2}
                  placeholder="Enter investigation findings, bank confirmation ticket, or resolution rationale..."
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-sky-500"
                />

                <div className="flex items-center justify-end gap-3">
                  <button
                    onClick={() => handleResolveCase('ESCALATED')}
                    className="px-3 py-1.5 rounded-lg bg-amber-600/30 text-amber-200 hover:bg-amber-600/50 border border-amber-500/30 text-xs font-semibold transition"
                  >
                    Escalate to Executive
                  </button>
                  <button
                    onClick={() => handleResolveCase('RESOLVED')}
                    className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md shadow-emerald-600/20 transition"
                  >
                    Mark as Resolved
                  </button>
                </div>
              </div>}
            </div>
          ) : (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-12 text-center text-slate-500 text-xs">
              Select an exception case to view investigation details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
