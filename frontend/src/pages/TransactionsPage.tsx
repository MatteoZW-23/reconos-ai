import React, { useState, useEffect } from 'react';
import {
  FileSpreadsheet,
  Search,
  Filter,
  Plus,
  AlertTriangle,
  Copy,
  Sparkles,
  ArrowDownLeft,
  ArrowUpRight,
} from 'lucide-react';
import { ApiClient } from '../api';
import { NormalizedTransaction, FinancialAccount } from '../types';

export const TransactionsPage: React.FC = () => {
  const [transactions, setTransactions] = useState<NormalizedTransaction[]>([]);
  const [accounts, setAccounts] = useState<FinancialAccount[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);

  // Manual Transaction Form
  const [manualAccount, setManualAccount] = useState('');
  const [manualDate, setManualDate] = useState(new Date().toISOString().slice(0, 16));
  const [manualAmount, setManualAmount] = useState('');
  const [manualType, setManualType] = useState<'CREDIT' | 'DEBIT'>('CREDIT');
  const [manualRef, setManualRef] = useState('');
  const [manualDesc, setManualDesc] = useState('');

  useEffect(() => {
    loadAccounts();
    loadTransactions();
  }, [selectedAccountId, selectedStatus]);

  const loadAccounts = async () => {
    try {
      const data = await ApiClient.get('/accounts');
      setAccounts(data);
    } catch (e) {
      console.error(e);
    }
  };

  const loadTransactions = async () => {
    setLoading(true);
    try {
      let url = '/transactions?limit=250';
      if (selectedAccountId) url += `&account_id=${selectedAccountId}`;
      if (selectedStatus) url += `&status=${selectedStatus}`;
      if (search) url += `&search=${encodeURIComponent(search)}`;
      const data = await ApiClient.get(url);
      setTransactions(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadTransactions();
  };

  const handleCreateManual = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualAccount || !manualAmount) return;

    try {
      await ApiClient.post('/transactions', {
        financial_account_id: manualAccount,
        transaction_date: new Date(manualDate).toISOString(),
        amount: manualAmount,
        transaction_type: manualType,
        external_reference: manualRef || null,
        description: manualDesc || null,
      });
      setShowAddModal(false);
      setManualAmount('');
      setManualRef('');
      setManualDesc('');
      loadTransactions();
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-sky-400" />
            Transaction Operations Explorer
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Normalized transaction records across all connected financial accounts and statements.
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-lg shadow-sky-600/30 transition"
        >
          <Plus className="w-4 h-4" />
          <span>Manual Transaction Entry</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-2xl flex flex-col md:flex-row gap-3 items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search reference, description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-sky-500"
          />
        </form>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <select
            value={selectedAccountId}
            onChange={(e) => setSelectedAccountId(e.target.value)}
            className="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
          >
            <option value="">All Financial Accounts</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>

          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
          >
            <option value="">All Statuses</option>
            <option value="UNRECONCILED">Unreconciled</option>
            <option value="MATCHED">Matched</option>
            <option value="EXCEPTION">Exception</option>
            <option value="MANUAL_REVIEW">Manual Review</option>
          </select>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
              <tr>
                <th className="p-3">Date</th>
                <th className="p-3">Reference</th>
                <th className="p-3">Type</th>
                <th className="p-3">Description / Counterparty</th>
                <th className="p-3 text-right">Amount</th>
                <th className="p-3 text-center">Status</th>
                <th className="p-3 text-center">AI Anomaly</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
              {transactions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-slate-500 font-sans">
                    No transactions found matching current criteria.
                  </td>
                </tr>
              ) : (
                transactions.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-800/30 transition">
                    <td className="p-3 text-slate-400 whitespace-nowrap">
                      {new Date(tx.transaction_date).toLocaleDateString()}
                    </td>
                    <td className="p-3 font-semibold text-slate-200 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <span>{tx.external_reference || tx.internal_reference}</span>
                        {tx.is_duplicate && (
                          <span
                            title="Duplicate detected"
                            className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 border border-amber-500/30 font-sans"
                          >
                            DUP
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="p-3 whitespace-nowrap">
                      {tx.transaction_type === 'CREDIT' ? (
                        <span className="flex items-center gap-1 text-emerald-400 font-semibold font-sans text-[11px]">
                          <ArrowDownLeft className="w-3.5 h-3.5" /> CR
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-rose-400 font-semibold font-sans text-[11px]">
                          <ArrowUpRight className="w-3.5 h-3.5" /> DR
                        </span>
                      )}
                    </td>
                    <td className="p-3 max-w-xs truncate font-sans text-slate-300">
                      {tx.description || tx.counterparty_name || '—'}
                    </td>
                    <td className="p-3 text-right font-bold text-white whitespace-nowrap">
                      ${parseFloat(tx.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="p-3 text-center whitespace-nowrap font-sans">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                          tx.reconciliation_status === 'MATCHED'
                            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                            : tx.reconciliation_status === 'EXCEPTION'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            : tx.reconciliation_status === 'MANUAL_REVIEW'
                            ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            : 'bg-slate-800 text-slate-400 border border-slate-700'
                        }`}
                      >
                        {tx.reconciliation_status}
                      </span>
                    </td>
                    <td className="p-3 text-center whitespace-nowrap font-sans">
                      {tx.anomaly_flag ? (
                        <span
                          title={tx.anomaly_reasons?.join(', ')}
                          className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] font-bold flex items-center justify-center gap-1"
                        >
                          <AlertTriangle className="w-3 h-3 text-rose-400" />
                          {(tx.anomaly_score * 100).toFixed(0)}%
                        </span>
                      ) : (
                        <span className="text-slate-600 text-[11px]">Nominal</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal: Manual Transaction Entry */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-md space-y-4 shadow-2xl">
            <h2 className="text-lg font-bold text-white">Manual Transaction Entry</h2>
            <form onSubmit={handleCreateManual} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Financial Account *</label>
                <select
                  required
                  value={manualAccount}
                  onChange={(e) => setManualAccount(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-sky-500"
                >
                  <option value="">Select Account</option>
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Amount ($) *</label>
                  <input
                    type="number"
                    step="0.01"
                    required
                    placeholder="0.00"
                    value={manualAmount}
                    onChange={(e) => setManualAmount(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Type *</label>
                  <select
                    value={manualType}
                    onChange={(e) => setManualType(e.target.value as any)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-sky-500"
                  >
                    <option value="CREDIT">Credit (Inflow)</option>
                    <option value="DEBIT">Debit (Outflow)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Date & Time *</label>
                <input
                  type="datetime-local"
                  required
                  value={manualDate}
                  onChange={(e) => setManualDate(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Reference Number</label>
                <input
                  type="text"
                  placeholder="e.g. RECEIPT-88192"
                  value={manualRef}
                  onChange={(e) => setManualRef(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">Description</label>
                <input
                  type="text"
                  placeholder="e.g. Petty cash manual replenishment"
                  value={manualDesc}
                  onChange={(e) => setManualDesc(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-sky-600 text-white text-xs font-semibold hover:bg-sky-500 transition"
                >
                  Save Transaction
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
