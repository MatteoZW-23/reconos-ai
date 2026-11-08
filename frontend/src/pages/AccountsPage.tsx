import React, { useState, useEffect } from 'react';
import {
  Building2,
  Plus,
  Scale,
  CheckCircle,
  AlertTriangle,
  CreditCard,
  Building,
  Smartphone,
  Layers,
} from 'lucide-react';
import { ApiClient } from '../api';
import { FinancialAccount, Branch, User } from '../types';

export const AccountsPage: React.FC<{ user: User }> = ({ user }) => {
  const [accounts, setAccounts] = useState<FinancialAccount[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [balanceCheckResult, setBalanceCheckResult] = useState<any>(null);
  const [checkingAccountId, setCheckingAccountId] = useState<string | null>(null);

  // Form
  const [name, setName] = useState('');
  const [type, setType] = useState<'BANK' | 'MOBILE_MONEY' | 'POS_TERMINAL' | 'CASH_DRAWER' | 'GATEWAY' | 'ERP_LEDGER'>('BANK');
  const [provider, setProvider] = useState('');
  const [accNum, setAccNum] = useState('');
  const [currency, setCurrency] = useState('USD');
  const [openingBalance, setOpeningBalance] = useState('0.00');
  const [branchId, setBranchId] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [accs, brs] = await Promise.all([
        ApiClient.get('/accounts'),
        ApiClient.get('/branches'),
      ]);
      setAccounts(accs);
      setBranches(brs);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !provider || !accNum) return;

    try {
      const newAcc = await ApiClient.post('/accounts', {
        name,
        account_type: type,
        provider_name: provider,
        account_number: accNum,
        currency,
        opening_balance: openingBalance,
        branch_id: branchId || null,
      });
      setAccounts([...accounts, newAcc]);
      setShowModal(false);
      setName('');
      setProvider('');
      setAccNum('');
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleVerifyBalance = async (accId: string) => {
    setCheckingAccountId(accId);
    try {
      const result = await ApiClient.get(`/accounts/${accId}/balance-check`);
      setBalanceCheckResult(result);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setCheckingAccountId(null);
    }
  };

  const getAccountIcon = (t: string) => {
    switch (t) {
      case 'BANK': return <Building className="w-4 h-4 text-sky-400" />;
      case 'MOBILE_MONEY': return <Smartphone className="w-4 h-4 text-emerald-400" />;
      case 'POS_TERMINAL': return <CreditCard className="w-4 h-4 text-amber-400" />;
      default: return <Layers className="w-4 h-4 text-indigo-400" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Building2 className="w-5 h-5 text-sky-400" />
            Financial Accounts & Payment Channels
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Registered commercial banks, mobile-money merchant wallets, POS terminals, and internal ledger accounts.
          </p>
        </div>
        {['owner', 'admin', 'finance_manager', 'accountant'].includes(user.role) && <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-lg shadow-sky-600/30 transition"
        >
          <Plus className="w-4 h-4" />
          <span>Register New Account</span>
        </button>}
      </div>

      {/* Balance Verification Modal / Result Banner */}
      {balanceCheckResult && (
        <div className={`p-4 rounded-2xl border ${balanceCheckResult.is_balanced ? 'bg-emerald-500/10 border-emerald-500/30' : 'bg-rose-500/10 border-rose-500/30'} flex flex-col md:flex-row md:items-center justify-between gap-4`}>
          <div className="flex items-start gap-3">
            {balanceCheckResult.is_balanced ? (
              <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            )}
            <div>
              <h3 className={`text-sm font-bold ${balanceCheckResult.is_balanced ? 'text-emerald-300' : 'text-rose-300'}`}>
                {balanceCheckResult.account_name} &bull; Arithmetic Comparison
              </h3>
              <p className="text-xs text-slate-300 mt-1">{balanceCheckResult.status_message}</p>
              <div className="flex flex-wrap gap-4 text-xs font-mono text-slate-400 mt-2">
                <span>Opening: {balanceCheckResult.currency} {parseFloat(balanceCheckResult.opening_balance).toFixed(2)}</span>
                <span>Credits: {balanceCheckResult.currency} {parseFloat(balanceCheckResult.total_credits).toFixed(2)}</span>
                <span>Debits: {balanceCheckResult.currency} {parseFloat(balanceCheckResult.total_debits).toFixed(2)}</span>
                <span>Calculated: {balanceCheckResult.currency} {parseFloat(balanceCheckResult.expected_closing).toFixed(2)}</span>
                <span className="font-bold text-white">Recorded current: {balanceCheckResult.currency} {parseFloat(balanceCheckResult.actual_closing).toFixed(2)}</span>
              </div>
            </div>
          </div>
          <button
            onClick={() => setBalanceCheckResult(null)}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white border border-slate-700 transition"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Accounts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {accounts.map((acc) => (
          <div key={acc.id} className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between hover:border-slate-700 transition">
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
                    {getAccountIcon(acc.account_type)}
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-slate-200">{acc.name}</h2>
                    <span className="text-[10px] text-slate-400 font-mono">{acc.provider_name}</span>
                  </div>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
                  {acc.account_type}
                </span>
              </div>

              <div className="mt-4 pt-4 border-t border-slate-800/80 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Account / Merchant #:</span>
                  <span className="font-mono text-slate-300 font-medium">{acc.account_number}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Opening Balance:</span>
                  <span className="font-mono text-slate-400">${parseFloat(acc.opening_balance).toFixed(2)} {acc.currency}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-slate-500">Statement Balance:</span>
                  <span className="font-mono text-white font-bold text-sm">${parseFloat(acc.current_balance).toFixed(2)} {acc.currency}</span>
                </div>
              </div>
            </div>

            <div className="mt-5 pt-3 border-t border-slate-800/80 flex justify-end">
              <button
                onClick={() => handleVerifyBalance(acc.id)}
                disabled={checkingAccountId === acc.id}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-sky-600 text-slate-300 hover:text-white text-xs font-semibold transition disabled:opacity-50"
              >
                <Scale className="w-3.5 h-3.5" />
                <span>{checkingAccountId === acc.id ? 'Checking...' : 'Verify Balance Equation'}</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Modal: Create Account */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-md space-y-4 shadow-2xl">
            <h2 className="text-lg font-bold text-white">Register Financial Account</h2>
            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Account Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Stanbic Operating Account"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Account Type *</label>
                  <select
                    value={type}
                    onChange={(e) => setType(e.target.value as any)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                  >
                    <option value="BANK">Bank Account</option>
                    <option value="MOBILE_MONEY">Mobile Money Wallet</option>
                    <option value="POS_TERMINAL">POS Terminal</option>
                    <option value="CASH_DRAWER">Cash Drawer / Float</option>
                    <option value="ERP_LEDGER">ERP / POS Ledger</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Provider Entity *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Stanbic Bank"
                    value={provider}
                    onChange={(e) => setProvider(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Account Number *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. ACC-991823"
                    value={accNum}
                    onChange={(e) => setAccNum(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Opening Balance ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={openingBalance}
                    onChange={(e) => setOpeningBalance(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Operating Branch (Optional)</label>
                <select
                  value={branchId}
                  onChange={(e) => setBranchId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                >
                  <option value="">Organization-Wide (HQ / General)</option>
                  {branches.map((b) => (
                    <option key={b.id} value={b.id}>{b.name}</option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-sky-600 text-white text-xs font-semibold hover:bg-sky-500 transition"
                >
                  Save Account
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
