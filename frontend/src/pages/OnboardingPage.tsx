import React, { useState } from 'react';
import { ShieldCheck, Building2, User, ArrowRight, ArrowLeft } from 'lucide-react';
import { ApiClient } from '../api';
import { AuthResponse } from '../types';

interface OnboardingPageProps {
  onOnboardingSuccess: (authData: AuthResponse) => void;
  onGoToLogin: () => void;
}

export const OnboardingPage: React.FC<OnboardingPageProps> = ({
  onOnboardingSuccess,
  onGoToLogin,
}) => {
  const [step, setStep] = useState(1);
  const [orgName, setOrgName] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [branchName, setBranchName] = useState('Headquarters Depot');
  const [branchCode, setBranchCode] = useState('HQ-01');
  const [adminName, setAdminName] = useState('');
  const [adminEmail, setAdminEmail] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFinish = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data: AuthResponse = await ApiClient.post('/auth/onboarding', {
        organization_name: orgName,
        default_currency: currency,
        admin_full_name: adminName,
        admin_email: adminEmail,
        admin_password: adminPassword,
        branch_name: branchName,
        branch_code: branchCode,
      });
      localStorage.setItem('reconos_token', data.access_token);
      localStorage.setItem('reconos_auth', JSON.stringify(data));
      onOnboardingSuccess(data);
    } catch (err: any) {
      setError(err.message || 'Onboarding failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center p-4 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-lg bg-slate-900/90 border border-slate-800 rounded-3xl p-8 backdrop-blur-xl shadow-2xl relative z-10 space-y-6">
        <div className="text-center space-y-1">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/30 mx-auto mb-2">
            <Building2 className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-xl font-bold text-white">Organization Setup Wizard</h1>
          <p className="text-xs text-slate-400">Step {step} of 2 &bull; Provisioning Multi-Tenant FinOps Environment</p>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
            {error}
          </div>
        )}

        {step === 1 ? (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Company / Enterprise Legal Name *</label>
              <input
                type="text"
                required
                placeholder="e.g. Makoni Retail Holdings Ltd"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Base Currency *</label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                >
                  <option value="USD">USD ($)</option>
                  <option value="ZWG">ZWG (ZiG)</option>
                  <option value="ZAR">ZAR (R)</option>
                  <option value="KES">KES</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Initial Branch Code *</label>
                <input
                  type="text"
                  required
                  value={branchCode}
                  onChange={(e) => setBranchCode(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                />
              </div>
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-slate-800">
              <button
                type="button"
                onClick={onGoToLogin}
                className="text-xs text-slate-400 hover:text-slate-200"
              >
                Back to Login
              </button>
              <button
                type="button"
                disabled={!orgName}
                onClick={() => setStep(2)}
                className="flex items-center gap-2 px-5 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-lg shadow-sky-600/30 transition disabled:opacity-50"
              >
                <span>Continue</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleFinish} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Administrator Full Name *</label>
              <input
                type="text"
                required
                placeholder="e.g. Farai Moyo"
                value={adminName}
                onChange={(e) => setAdminName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Admin Email Address *</label>
              <input
                type="email"
                required
                placeholder="admin@makoniholdings.co.zw"
                value={adminEmail}
                onChange={(e) => setAdminEmail(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">Admin Master Password *</label>
              <input
                type="password"
                required
                placeholder="Min 8 characters"
                value={adminPassword}
                onChange={(e) => setAdminPassword(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
              />
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Back</span>
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 text-white text-xs font-bold shadow-lg shadow-sky-600/30 transition disabled:opacity-50"
              >
                <span>{loading ? 'Initializing...' : 'Launch Workspace'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
