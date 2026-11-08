import React, { useState, useEffect } from 'react';
import {
  History,
  ShieldCheck,
  Search,
  Filter,
  User,
  Clock,
} from 'lucide-react';
import { ApiClient } from '../api';
import { AuditEvent } from '../types';

export const AuditPage: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionFilter, setActionFilter] = useState('');

  useEffect(() => {
    loadAuditEvents();
  }, [actionFilter]);

  const loadAuditEvents = async () => {
    setLoading(true);
    try {
      let url = '/audit?limit=150';
      if (actionFilter) url += `&action=${actionFilter}`;
      const data = await ApiClient.get(url);
      setEvents(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <History className="w-5 h-5 text-sky-400" />
          Immutable Audit Trail & Governance Ledger
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Tamper-evident record of statement imports, matching decisions, manual overrides, and approvals.
        </p>
      </div>

      {/* Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider">
              <tr>
                <th className="p-3">Timestamp (UTC)</th>
                <th className="p-3">User</th>
                <th className="p-3">Action</th>
                <th className="p-3">Resource Type</th>
                <th className="p-3">Audit Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
              {events.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-500 font-sans">
                    No audit records located.
                  </td>
                </tr>
              ) : (
                events.map((e) => (
                  <tr key={e.id} className="hover:bg-slate-800/30 transition">
                    <td className="p-3 text-slate-400 whitespace-nowrap">
                      {new Date(e.created_at).toLocaleString()}
                    </td>
                    <td className="p-3 font-sans font-medium text-slate-200 whitespace-nowrap">
                      {e.user_name || 'System Interceptor'}
                    </td>
                    <td className="p-3 font-bold text-sky-400 whitespace-nowrap">
                      {e.action}
                    </td>
                    <td className="p-3 text-slate-400 whitespace-nowrap">
                      {e.resource_type}
                    </td>
                    <td className="p-3 max-w-md truncate text-slate-400">
                      {JSON.stringify(e.details || {})}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
