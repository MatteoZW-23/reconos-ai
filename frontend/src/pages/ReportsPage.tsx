import React, { useState, useEffect } from 'react';
import {
  FileText,
  Download,
  Calendar,
  Building,
  CheckCircle,
  FileSpreadsheet,
} from 'lucide-react';
import { ApiClient } from '../api';

export const ReportsPage: React.FC = () => {
  const [report, setReport] = useState<any>(null);
  const [targetDate, setTargetDate] = useState(new Date().toISOString().slice(0, 10));
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadReport();
  }, [targetDate]);

  const loadReport = async () => {
    setLoading(true);
    try {
      const data = await ApiClient.get(`/reports/daily?date=${targetDate}`);
      setReport(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPdf = () => {
    const token = localStorage.getItem('reconos_token');
    fetch(`/api/v1/reports/daily/export/pdf?date=${targetDate}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => { if (!res.ok) throw new Error(`Request failed (${res.status})`); return res.blob(); })
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ReconOS_Daily_Report_${targetDate}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      })
      .catch((err) => alert('Failed to download PDF: ' + err));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <FileText className="w-5 h-5 text-sky-400" />
            Financial Operations & Audit Reports
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Daily totals cover the organization reporting currency only; no conversion is applied.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <input
            type="date"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
            className="px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-200"
          />
          <button
            onClick={handleDownloadPdf}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-lg shadow-sky-600/30 transition"
          >
            <Download className="w-4 h-4" />
            <span>Download PDF</span>
          </button>
        </div>
      </div>

      {/* Report Summary Card */}
      {report && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between pb-4 border-b border-slate-800 gap-4">
            <div>
              <span className="text-xs font-mono font-bold text-sky-400 uppercase">
                {report.organization_name} &bull; Daily Financial Reconciliation Report
              </span>
              <h2 className="text-lg font-bold text-white mt-1">
                Statement Date: {report.report_date}
              </h2>
            </div>
            <div className="text-right">
              <span className="text-2xl font-bold font-mono text-emerald-400">
                {report.reconciliation_rate}%
              </span>
              <span className="block text-[11px] text-slate-500 font-mono">Reconciliation Completion</span>
            </div>
          </div>

          {/* Metrics Table */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
              <span className="text-[11px] text-slate-500 uppercase font-medium">Total Transactions</span>
              <div className="text-xl font-bold font-mono text-white mt-1">
                {report.total_transactions}
              </div>
            </div>
            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
              <span className="text-[11px] text-slate-500 uppercase font-medium">Total Volume</span>
              <div className="text-xl font-bold font-mono text-white mt-1">
                {report.currency} {parseFloat(report.total_volume).toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
              <span className="text-[11px] text-slate-500 uppercase font-medium">Matched Volume</span>
              <div className="text-xl font-bold font-mono text-emerald-400 mt-1">
                {report.currency} {parseFloat(report.matched_volume).toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-xl">
              <span className="text-[11px] text-slate-500 uppercase font-medium">Discrepancy Volume</span>
              <div className="text-xl font-bold font-mono text-amber-400 mt-1">
                {report.currency} {parseFloat(report.unmatched_volume).toLocaleString('en-US', { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          {/* Branch Coverage */}
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Configured Operating Branches
            </span>
            <div className="flex flex-wrap gap-2 pt-1">
              {report.branches_covered.map((bName: string) => (
                <span key={bName} className="text-xs px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
                  {bName}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
