import React, { useState, useEffect } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Database,
  Hash,
  Sparkles,
} from 'lucide-react';
import { ApiClient } from '../api';
import { FinancialAccount } from '../types';

export const IngestionPage: React.FC = () => {
  const [accounts, setAccounts] = useState<FinancialAccount[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<any>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [rowErrors, setRowErrors] = useState<any[]>([]);
  const [errorLoadMessage, setErrorLoadMessage] = useState('');
  const [sourceHeaders, setSourceHeaders] = useState<string[]>([]);

  // Column mapping states
  const [dateCol, setDateCol] = useState('');
  const [amountCol, setAmountCol] = useState('');
  const [refCol, setRefCol] = useState('');
  const [typeCol, setTypeCol] = useState('');
  const [descCol, setDescCol] = useState('');
  const [feeCol, setFeeCol] = useState('');
  const [balanceCol, setBalanceCol] = useState('');
  const [dateFormat, setDateFormat] = useState('');
  const [defaultType, setDefaultType] = useState('');

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    try {
      const data = await ApiClient.get('/accounts');
      setAccounts(data);
      if (data.length > 0) setSelectedAccountId(data[0].id);
    } catch (e) {
      console.error(e);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;
    setFile(selectedFile);
    setUploadResult(null);
    setRowErrors([]);
    setErrorLoadMessage('');
    setPreview(null);
    setDateFormat('');
    setDefaultType('');

    // Trigger preview
    const formData = new FormData();
    formData.append('file', selectedFile);
    if (selectedAccountId) formData.append('account_id', selectedAccountId);

    setLoadingPreview(true);
    try {
      const previewData = await ApiClient.postFormData('/ingestion/preview', formData);
      setPreview(previewData);
      setSourceHeaders(previewData.headers);

      // Pre-fill suggested mappings
      const m = previewData.suggested_mapping;
      if (m) {
        setDateCol(m.date_col || '');
        setAmountCol(m.amount_col || '');
        setRefCol(m.reference_col || '');
        setTypeCol(m.type_col || '');
        setDescCol(m.description_col || '');
        setFeeCol(m.fee_col || '');
        setBalanceCol(m.balance_col || '');
      }
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleUploadAndNormalize = async () => {
    if (!file || !selectedAccountId) return;

    const mapping = {
      date_col: dateCol,
      amount_col: amountCol,
      reference_col: refCol || null,
      type_col: typeCol || null,
      description_col: descCol || null,
      fee_col: feeCol || null,
      balance_col: balanceCol || null,
      date_format: dateFormat || null,
      default_type: defaultType || null,
    };

    const formData = new FormData();
    formData.append('file', file);
    formData.append('account_id', selectedAccountId);
    formData.append('mapping_json', JSON.stringify(mapping));

    setUploading(true);
    try {
      const result = await ApiClient.postFormData('/ingestion/upload', formData);
      setUploadResult(result);
      if (result.error_rows > 0) {
        try {
          setRowErrors(await ApiClient.get(`/ingestion/batches/${result.id}/errors`));
        } catch {
          setErrorLoadMessage('Row details could not be loaded. Ask a finance administrator to review the import.');
        }
      }
      setPreview(null);
      setFile(null);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setUploading(false);
    }
  };

  const retryFailedRows = async () => {
    if (!uploadResult) return;
    setUploading(true);
    setErrorLoadMessage('');
    try {
      const result = await ApiClient.post(`/ingestion/batches/${uploadResult.id}/retry`, {
        date_col: dateCol, amount_col: amountCol, reference_col: refCol || null,
        type_col: typeCol || null, description_col: descCol || null, fee_col: feeCol || null,
        balance_col: balanceCol || null, date_format: dateFormat || null, default_type: defaultType || null,
      });
      setUploadResult(result);
      setRowErrors(result.error_rows ? await ApiClient.get(`/ingestion/batches/${result.id}/errors`) : []);
    } catch (err: any) {
      setErrorLoadMessage(err.message || 'Could not retry the failed rows.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <UploadCloud className="w-5 h-5 text-sky-400" />
          Universal Statement Ingestion
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Upload bank statements, mobile money reports (EcoCash/M-Pesa), POS settlements, or ERP ledger extracts.
        </p>
      </div>

      {/* Success Banner */}
      {uploadResult && (
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-700 space-y-3">
          <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <div>
              <h3 className="text-sm font-semibold text-slate-100">{uploadResult.error_rows ? 'Statement processed with row errors' : 'Statement processed'}</h3>
              <p className="text-xs text-slate-400">
                Batch #{uploadResult.id.slice(0, 8)} &bull; {uploadResult.valid_rows} records normalized &bull; {uploadResult.error_rows} rows failed
              </p>
            </div>
          </div>
          <button
            onClick={() => setUploadResult(null)}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-emerald-600/30 text-emerald-200 border border-emerald-500/30 hover:bg-emerald-600/50 transition"
          >
            Upload Another
          </button>
          </div>
          {uploadResult.error_rows > 0 && <div className="text-xs text-amber-300 space-y-1" role="alert">
            <p>Failed rows were not normalized. Adjust the mapping and retry only those rows; successful rows will not be processed again. Showing up to 100 errors.</p>
            {errorLoadMessage && <p>{errorLoadMessage}</p>}
            {rowErrors.map((row: any) => <p key={row.id}>Row {row.row_number}: {row.error_message}</p>)}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
              <label>Date column<select value={dateCol} onChange={e => setDateCol(e.target.value)} className="block w-full bg-slate-950 text-slate-100 p-2">{sourceHeaders.map(h => <option key={h}>{h}</option>)}</select></label>
              <label>Amount column<select value={amountCol} onChange={e => setAmountCol(e.target.value)} className="block w-full bg-slate-950 text-slate-100 p-2">{sourceHeaders.map(h => <option key={h}>{h}</option>)}</select></label>
              <label>Type column<select value={typeCol} onChange={e => setTypeCol(e.target.value)} className="block w-full bg-slate-950 text-slate-100 p-2"><option value="">None</option>{sourceHeaders.map(h => <option key={h}>{h}</option>)}</select></label>
              <label>Date format<select value={dateFormat} onChange={e => setDateFormat(e.target.value)} className="block w-full bg-slate-950 text-slate-100 p-2"><option value="">ISO</option><option value="%d/%m/%Y">DD/MM/YYYY</option><option value="%m/%d/%Y">MM/DD/YYYY</option><option value="%d-%m-%Y">DD-MM-YYYY</option></select></label>
              <label>Direction when type is missing<select value={defaultType} onChange={e => setDefaultType(e.target.value)} className="block w-full bg-slate-950 text-slate-100 p-2"><option value="">Require direction</option><option value="CREDIT">Credit</option><option value="DEBIT">Debit</option></select></label>
            </div>
            <button disabled={uploading} onClick={retryFailedRows} className="px-3 py-2 bg-sky-700 text-white rounded-lg disabled:opacity-50">{uploading ? 'Retrying…' : 'Retry failed rows'}</button>
          </div>}
        </div>
      )}

      {/* Upload & Config Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Step 1 & 2: Account Selection and Dropzone */}
        <div className="lg:col-span-1 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              1. Select Destination Financial Account
            </label>
            <select
              value={selectedAccountId}
              onChange={(e) => setSelectedAccountId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-sky-500"
            >
              {accounts.map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.name} ({acc.provider_name})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              2. Upload File (CSV or Excel)
            </label>
            <label className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-slate-800 hover:border-sky-500/50 bg-slate-950/60 rounded-2xl cursor-pointer transition">
              <UploadCloud className="w-8 h-8 text-sky-400 mb-2" />
              <span className="text-xs font-medium text-slate-200">
                {file ? file.name : 'Click or drag statement file'}
              </span>
              <span className="text-[11px] text-slate-500 mt-1">Supports CSV, TSV, XLSX</span>
              <input
                type="file"
                accept=".csv,.xlsx,.xls,.tsv"
                onChange={handleFileChange}
                className="hidden"
              />
            </label>
          </div>

          {loadingPreview && (
            <div className="flex items-center justify-center gap-2 text-xs text-sky-400 p-3 bg-sky-500/5 rounded-xl border border-sky-500/20">
              <Sparkles className="w-4 h-4 animate-spin" />
              <span>Analyzing dialect, encoding, and schema...</span>
            </div>
          )}
        </div>

        {/* Step 3: Mapping Wizard & Preview */}
        <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
              3. Schema Mapping & Duplicate Detection
            </h2>
            {preview && (
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/20 font-mono">
                Detected: {preview.detected_adapter}
              </span>
            )}
          </div>

          {preview ? (
            <div className="space-y-4">
              {/* Duplicate alert if detected */}
              {preview.is_duplicate && (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center gap-3 text-xs text-amber-300">
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>{preview.duplicate_message}</span>
                </div>
              )}

              {/* SHA-256 Digest */}
              <div className="flex items-center gap-2 text-xs text-slate-500 font-mono bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                <Hash className="w-3.5 h-3.5 text-slate-400" />
                <span className="truncate">SHA-256: {preview.file_hash}</span>
              </div>

              {/* Column Mapping Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">Date Column *</label>
                  <select
                    value={dateCol}
                    onChange={(e) => setDateCol(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                  >
                    {preview.headers.map((h: string) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">Amount Column *</label>
                  <select
                    value={amountCol}
                    onChange={(e) => setAmountCol(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                  >
                    {preview.headers.map((h: string) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">Reference Column</label>
                  <select
                    value={refCol}
                    onChange={(e) => setRefCol(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                  >
                    <option value="">None / Not Applicable</option>
                    {preview.headers.map((h: string) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">Type (Dr/Cr) Column</label>
                  <select
                    value={typeCol}
                    onChange={(e) => setTypeCol(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                  >
                    <option value="">No type column</option>
                    {preview.headers.map((h: string) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">Description / Narrative</label>
                  <select
                    value={descCol}
                    onChange={(e) => setDescCol(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                  >
                    <option value="">None</option>
                    {preview.headers.map((h: string) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">Fee Column</label>
                  <select
                    value={feeCol}
                    onChange={(e) => setFeeCol(e.target.value)}
                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200"
                  >
                    <option value="">None / 0.00</option>
                    {preview.headers.map((h: string) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">Statement date format</label>
                  <select value={dateFormat} onChange={(e) => setDateFormat(e.target.value)} className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200">
                    <option value="">ISO: YYYY-MM-DD or ISO date/time</option>
                    <option value="%d/%m/%Y">DD/MM/YYYY</option>
                    <option value="%m/%d/%Y">MM/DD/YYYY</option>
                    <option value="%d-%m-%Y">DD-MM-YYYY</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-slate-400 mb-1">Direction when type is missing</label>
                  <select value={defaultType} onChange={(e) => setDefaultType(e.target.value)} className="w-full px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200">
                    <option value="">Require direction (negative amounts are debit)</option>
                    <option value="CREDIT">Positive amounts are credit</option>
                    <option value="DEBIT">Positive amounts are debit</option>
                  </select>
                </div>
              </div>
              <p className="text-xs text-amber-300">Check the date format and direction against the original statement. Separate debit and credit columns are not yet supported.</p>

              {/* Sample Rows Table */}
              <div className="space-y-2">
                <span className="text-xs font-semibold text-slate-400">Sample Ingestion Preview (Top 5 Rows)</span>
                <div className="border border-slate-800 rounded-xl overflow-x-auto bg-slate-950/60 max-h-48">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-900 border-b border-slate-800 text-slate-400">
                      <tr>
                        {preview.headers.map((h: string) => (
                          <th key={h} className="p-2 font-medium">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-300 font-mono">
                      {preview.sample_rows.map((row: any, i: number) => (
                        <tr key={i}>
                          {preview.headers.map((h: string) => (
                            <td key={h} className="p-2 truncate max-w-[150px]">{row[h]}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Action Button */}
              <div className="flex justify-end pt-2">
                <button
                  onClick={handleUploadAndNormalize}
                  disabled={uploading}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold shadow-lg shadow-sky-600/30 transition disabled:opacity-50"
                >
                  <Database className="w-4 h-4" />
                  <span>{uploading ? 'Normalizing Statement...' : 'Ingest & Normalize Statement'}</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-slate-500 text-xs bg-slate-950/40 rounded-xl border border-dashed border-slate-800">
              Upload a file on the left to inspect columns and configure data mapping.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
