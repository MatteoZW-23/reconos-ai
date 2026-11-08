import React, { useState } from 'react';
import {
  Settings,
  Shield,
  Key,
  Globe,
  Sliders,
  CheckCircle,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [defaultCurrency, setDefaultCurrency] = useState('USD');
  const [defaultToleranceDays, setDefaultToleranceDays] = useState('2');
  const [enableDuplicateRejection, setEnableDuplicateRejection] = useState(true);
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Settings className="w-5 h-5 text-sky-400" />
          Platform & Engine Configuration
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Tenant-level default tolerances, currency standards, and cryptographic safeguards.
        </p>
      </div>

      {saved && (
        <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-2 text-xs text-emerald-300">
          <CheckCircle className="w-4 h-4 text-emerald-400" />
          <span>System configuration successfully updated.</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* Section 1: Financial Rules */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Sliders className="w-4 h-4 text-sky-400" />
            Deterministic Reconciliation Defaults
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Default Base Currency</label>
              <select
                value={defaultCurrency}
                onChange={(e) => setDefaultCurrency(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200"
              >
                <option value="USD">USD ($) - United States Dollar</option>
                <option value="ZWG">ZWG (ZiG) - Zimbabwe Gold</option>
                <option value="ZAR">ZAR (R) - South African Rand</option>
                <option value="KES">KES - Kenyan Shilling</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Default Temporal Tolerance Window (Days)
              </label>
              <input
                type="number"
                min="0"
                max="14"
                value={defaultToleranceDays}
                onChange={(e) => setDefaultToleranceDays(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200"
              />
            </div>
          </div>
        </div>

        {/* Section 2: Security & Integrity */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4">
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Shield className="w-4 h-4 text-emerald-400" />
            Cryptographic Integrity Safeguards
          </h2>

          <div className="flex items-center justify-between p-3 bg-slate-950/60 rounded-xl border border-slate-800">
            <div>
              <div className="text-xs font-semibold text-slate-200">SHA-256 Duplicate File Rejection</div>
              <div className="text-[11px] text-slate-500">
                Prevents accidental double-import of previously uploaded statement batches.
              </div>
            </div>
            <input
              type="checkbox"
              checked={enableDuplicateRejection}
              onChange={(e) => setEnableDuplicateRejection(e.target.checked)}
              className="rounded bg-slate-950 border-slate-700 text-sky-500"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            className="px-5 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-lg shadow-sky-600/30 transition"
          >
            Save Changes
          </button>
        </div>
      </form>
    </div>
  );
};
