import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  RefreshCw,
  AlertTriangle,
  Lightbulb,
  CheckCircle2,
  Clock,
  ArrowRight,
  TrendingDown,
  Cpu,
} from 'lucide-react';
import { ApiClient } from '../api';
import { AIInsight, User } from '../types';

export const AIInsightsPage: React.FC<{ user: User }> = ({ user }) => {
  const [insights, setInsights] = useState<AIInsight[]>([]);
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<any>(null);

  useEffect(() => {
    loadInsights();
  }, []);

  const loadInsights = async () => {
    try {
      const data = await ApiClient.get('/ai/insights');
      setInsights(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleScan = async () => {
    setScanning(true);
    try {
      const res = await ApiClient.post('/ai/scan-anomalies');
      setScanResult(res);
      loadInsights();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setScanning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-400" />
            AI Financial Investigation & Operations Intelligence
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Review statistical anomaly flags and available evidence. Findings require human review.
          </p>
        </div>
        {user.role !== 'auditor' && <button
          onClick={handleScan}
          disabled={scanning}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-lg shadow-purple-600/30 transition disabled:opacity-50"
        >
          <Cpu className={`w-4 h-4 ${scanning ? 'animate-spin' : ''}`} />
          <span>{scanning ? 'Scanning Feature Space...' : 'Run Anomaly Scan'}</span>
        </button>}
      </div>

      {/* Scan Banner Result */}
      {scanResult && (
        <div className="p-4 rounded-2xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-purple-400 shrink-0" />
            <div>
              <h3 className="text-sm font-semibold text-purple-300">Anomaly Scan Completed</h3>
              <p className="text-xs text-slate-400">
                Analyzed {scanResult.scanned_count} transaction feature vectors &bull; {scanResult.anomalies_detected} structural outliers flagged for investigator review
              </p>
            </div>
          </div>
          <button
            onClick={() => setScanResult(null)}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-purple-600/30 text-purple-200 border border-purple-500/30 hover:bg-purple-600/50 transition"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* 3-Layer Principles Banner */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center shrink-0">
            <Lightbulb className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">
              Advisory findings
            </h3>
            <p className="text-xs text-slate-400">
              Review flagged transactions and supporting records before taking action. Scores are not proof of errors or misconduct.
            </p>
          </div>
        </div>
      </div>

      {/* Macro Insights Cards */}
      {insights.length === 0 && <p className="text-sm text-slate-400">No verified insights are available yet.</p>}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {insights.map((ins) => (
          <div key={ins.id} className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between hover:border-purple-500/40 transition">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 font-mono">
                  {ins.insight_type.replace(/_/g, ' ')}
                </span>
                <span className="text-xs text-slate-500">
                  {new Date(ins.created_at).toLocaleDateString()}
                </span>
              </div>

              <h2 className="text-base font-bold text-white">{ins.title}</h2>
              <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-xl border border-slate-800">
                {ins.summary}
              </p>

              {/* Evidence Payload */}
              <div className="space-y-1">
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Reported Evidence</span>
                <div className="p-2.5 bg-slate-950/80 rounded-lg border border-slate-800 text-xs font-mono text-slate-400">
                  <pre className="overflow-x-auto">{JSON.stringify(ins.evidence, null, 2)}</pre>
                </div>
              </div>
            </div>

            {/* Recommendation */}
            <div className="mt-5 pt-4 border-t border-slate-800">
              <div className="p-3 bg-purple-950/20 border border-purple-500/20 rounded-xl text-xs text-purple-200">
                <span className="font-semibold text-purple-300">Operational Recommendation: </span>
                {ins.recommendation}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
