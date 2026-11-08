import React, { useState, useEffect } from 'react';
import {
  Coins,
  Plus,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Calculator,
} from 'lucide-react';
import { ApiClient } from '../api';
import { ShiftSummary, Branch, User } from '../types';

export const ShiftsPage: React.FC<{ user: User }> = ({ user }) => {
  const [shifts, setShifts] = useState<ShiftSummary[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [showModal, setShowModal] = useState(false);

  // Form
  const [branchId, setBranchId] = useState('');
  const [cashierName, setCashierName] = useState(user.full_name);
  const [shiftDate, setShiftDate] = useState(new Date().toISOString().slice(0, 10));
  const [shiftNumber, setShiftNumber] = useState('SHIFT-MORNING-01');
  const [openingCash, setOpeningCash] = useState('');
  const [cashSales, setCashSales] = useState('');
  const [mobileSales, setMobileSales] = useState('0.00');
  const [cardSales, setCardSales] = useState('0.00');
  const [cashPayouts, setCashPayouts] = useState('0.00');
  const [closingCash, setClosingCash] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [shiftsData, branchesData] = await Promise.all([
        ApiClient.get('/shifts'),
        ApiClient.get('/branches'),
      ]);
      setShifts(shiftsData);
      setBranches(branchesData);
      if (branchesData.length > 0) setBranchId(branchesData[0].id);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSubmitShift = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!branchId || !cashierName || !cashSales || !closingCash) return;

    try {
      const newShift = await ApiClient.post('/shifts', {
        branch_id: branchId,
        cashier_name: cashierName,
        shift_date: shiftDate,
        shift_number: shiftNumber,
        opening_cash: openingCash,
        cash_sales: cashSales,
        mobile_money_sales: mobileSales,
        card_sales: cardSales,
        cash_payouts: cashPayouts,
        closing_cash_counted: closingCash,
      });
      setShifts([newShift, ...shifts]);
      setShowModal(false);
      setCashSales('');
      setClosingCash('');
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleVerify = async (shiftId: string) => {
    const note = window.prompt('Supervisor note for the cashier (optional):');
    if (note === null) return;
    try {
      const updated = await ApiClient.patch(`/shifts/${shiftId}/verify`, {
        status: 'VERIFIED',
        supervisor_notes: note,
      });
      setShifts(shifts.map((s) => (s.id === updated.id ? updated : s)));
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Coins className="w-5 h-5 text-amber-400" />
            Cashier Shift & Float Reconciliation
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Cash counts are compared with recorded cash flows. Discrepancies are flagged on the shift for supervisor review; shift currency is not yet recorded.
          </p>
        </div>
        {['operator', 'branch_manager', 'accountant', 'owner', 'admin'].includes(user.role) && <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-lg shadow-sky-600/30 transition"
        >
          <Plus className="w-4 h-4" />
          <span>Submit Shift End Summary</span>
        </button>}
      </div>

      {/* Shifts Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
              <tr>
                <th className="p-3">Shift Date</th>
                <th className="p-3">Shift #</th>
                <th className="p-3">Cashier</th>
                <th className="p-3 text-right">Opening Float</th>
                <th className="p-3 text-right">Cash In</th>
                <th className="p-3 text-right">Counted Cash</th>
                <th className="p-3 text-right">System Expected</th>
                <th className="p-3 text-right">Variance</th>
                <th className="p-3 text-center">Status</th>
                <th className="p-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
              {shifts.length === 0 ? (
                <tr>
                  <td colSpan={10} className="p-8 text-center text-slate-500 font-sans">
                    No shift summaries recorded yet.
                  </td>
                </tr>
              ) : (
                shifts.map((s) => {
                  const varianceNum = parseFloat(s.cash_discrepancy);
                  return (
                    <tr key={s.id} className="hover:bg-slate-800/30 transition">
                      <td className="p-3 text-slate-400 whitespace-nowrap">{s.shift_date}</td>
                      <td className="p-3 font-semibold text-slate-200">{s.shift_number}</td>
                      <td className="p-3 font-sans text-slate-300">{s.cashier_name}{s.supervisor_notes && <div className="text-sky-300 text-xs mt-1">Supervisor: {s.supervisor_notes}</div>}</td>
                      <td className="p-3 text-right">${parseFloat(s.opening_cash).toFixed(2)}</td>
                      <td className="p-3 text-right text-emerald-400 font-semibold">
                        +${parseFloat(s.cash_sales).toFixed(2)}
                      </td>
                      <td className="p-3 text-right font-bold text-white">
                        ${parseFloat(s.closing_cash_counted).toFixed(2)}
                      </td>
                      <td className="p-3 text-right text-slate-400">
                        ${parseFloat(s.system_expected_cash).toFixed(2)}
                      </td>
                      <td className="p-3 text-right font-bold whitespace-nowrap">
                        <span
                          className={
                            varianceNum === 0
                              ? 'text-emerald-400'
                              : varianceNum > 0
                              ? 'text-sky-400'
                              : 'text-rose-400'
                          }
                        >
                          {varianceNum > 0 ? '+' : ''}${varianceNum.toFixed(2)}
                        </span>
                      </td>
                      <td className="p-3 text-center whitespace-nowrap font-sans">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                            s.status === 'VERIFIED'
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : s.status === 'DISCREPANCY_FLAGGED'
                              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                              : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          }`}
                        >
                          {s.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="p-3 text-center whitespace-nowrap font-sans">
                        {['branch_manager', 'finance_manager', 'owner', 'admin'].includes(user.role) && s.cashier_id !== user.id && s.status !== 'VERIFIED' && (
                          <button
                            onClick={() => handleVerify(s.id)}
                            className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-emerald-600 text-slate-300 hover:text-white text-[11px] font-semibold transition"
                          >
                            Verify Float
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal: Submit Shift Summary */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-lg space-y-4 shadow-2xl">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Calculator className="w-5 h-5 text-sky-400" />
              Cashier End-of-Shift Summary
            </h2>
            <form onSubmit={handleSubmitShift} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Operating Branch *</label>
                  <select
                    required
                    value={branchId}
                    onChange={(e) => setBranchId(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                  >
                    {branches.map((b) => (
                      <option key={b.id} value={b.id}>{b.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Cashier Full Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Tendai Chikore"
                    value={cashierName}
                    readOnly
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Shift Date *</label>
                  <input
                    type="date"
                    required
                    value={shiftDate}
                    onChange={(e) => setShiftDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Shift ID / Code *</label>
                  <input
                    type="text"
                    required
                    value={shiftNumber}
                    onChange={(e) => setShiftNumber(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">Opening Cash ($)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    required
                    value={openingCash}
                    onChange={(e) => setOpeningCash(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">Cash Sales ($) *</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    required
                    placeholder="0.00"
                    value={cashSales}
                    onChange={(e) => setCashSales(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">Cash Payouts ($)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={cashPayouts}
                    onChange={(e) => setCashPayouts(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200"
                  />
                </div>
              </div>

              <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
                <label className="block text-xs font-bold text-sky-400 mb-1">
                  Physical Closing Cash Counted ($) *
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  required
                  placeholder="Counted cash in register..."
                  value={closingCash}
                  onChange={(e) => setClosingCash(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-white font-mono font-bold focus:outline-none focus:border-sky-500"
                />
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
                  Submit & Calculate Float
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
