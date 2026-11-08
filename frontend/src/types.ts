export type UserRole =
  | 'owner'
  | 'finance_manager'
  | 'accountant'
  | 'branch_manager'
  | 'operator'
  | 'auditor'
  | 'admin';

export interface User {
  id: string;
  organization_id: string;
  branch_id?: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  organization_id: string;
  organization_name: string;
  role: UserRole;
  full_name: string;
  email: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  default_currency: string;
  is_active: boolean;
  created_at: string;
}

export interface Branch {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  address?: string;
  city?: string;
  country: string;
  is_active: boolean;
  created_at: string;
}

export interface FinancialAccount {
  id: string;
  organization_id: string;
  branch_id?: string;
  name: string;
  account_type: 'BANK' | 'MOBILE_MONEY' | 'POS_TERMINAL' | 'CASH_DRAWER' | 'GATEWAY' | 'ERP_LEDGER';
  provider_name: string;
  account_number: string;
  currency: string;
  opening_balance: string;
  current_balance: string;
  is_active: boolean;
  created_at: string;
}

export interface NormalizedTransaction {
  id: string;
  organization_id: string;
  batch_id: string;
  financial_account_id: string;
  branch_id?: string;
  external_reference?: string;
  internal_reference?: string;
  transaction_date: string;
  amount: string;
  currency: string;
  transaction_type: 'DEBIT' | 'CREDIT';
  fee_amount: string;
  balance_after?: string;
  counterparty_name?: string;
  counterparty_account?: string;
  description?: string;
  reconciliation_status: 'UNRECONCILED' | 'MATCHED' | 'PARTIALLY_MATCHED' | 'EXCEPTION' | 'MANUAL_REVIEW';
  is_duplicate: boolean;
  duplicate_of_id?: string;
  anomaly_score: number;
  anomaly_flag: boolean;
  anomaly_reasons?: string[];
  created_at: string;
}

export interface MatchParticipant {
  id: string;
  transaction_id: string;
  side: 'PRIMARY' | 'SECONDARY';
  allocated_amount: string;
  external_reference?: string;
  transaction_date?: string;
  description?: string;
}

export interface ReconciliationMatch {
  id: string;
  session_id: string;
  match_type: 'EXACT_REFERENCE' | 'AMOUNT_DATE_TOLERANCE' | 'ONE_TO_MANY' | 'MANY_TO_ONE' | 'MANUAL_OVERRIDE';
  confidence_score: string;
  status: 'SUGGESTED' | 'CONFIRMED' | 'REJECTED';
  primary_amount_total: string;
  secondary_amount_total: string;
  difference_amount: string;
  notes?: string;
  created_at: string;
  participants: MatchParticipant[];
}

export interface ReconciliationSession {
  id: string;
  organization_id: string;
  session_name: string;
  primary_account_id: string;
  secondary_account_id: string;
  date_from: string;
  date_to: string;
  status: 'DRAFT' | 'IN_PROGRESS' | 'COMPLETED' | 'APPROVED';
  total_primary_count: number;
  total_secondary_count: number;
  total_primary_amount: string;
  total_secondary_amount: string;
  matched_count: number;
  matched_amount: string;
  discrepancy_amount: string;
  reconciliation_rate: string;
  approved_by_id?: string;
  approved_at?: string;
  created_at: string;
  matches: ReconciliationMatch[];
}

export interface ExceptionCase {
  id: string;
  organization_id: string;
  session_id?: string;
  transaction_id?: string;
  case_number: string;
  title: string;
  description: string;
  category: 'MISSING_TRANSACTION' | 'AMOUNT_MISMATCH' | 'DUPLICATE_ENTRY' | 'UNRECOGNIZED_FEE' | 'TIMING_DELAY' | 'CASH_SHORTAGE';
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'OPEN' | 'UNDER_INVESTIGATION' | 'RESOLVED' | 'CLOSED' | 'ESCALATED';
  discrepancy_amount: string;
  currency: string;
  assigned_to_id?: string;
  created_by_id?: string;
  ai_analysis?: Record<string, any>;
  evidence?: Record<string, any>;
  resolution_notes?: string;
  resolved_at?: string;
  created_at: string;
}

export interface ShiftSummary {
  id: string;
  organization_id: string;
  branch_id: string;
  cashier_id?: string;
  cashier_name: string;
  shift_date: string;
  shift_number: string;
  opening_cash: string;
  cash_sales: string;
  mobile_money_sales: string;
  card_sales: string;
  cash_payouts: string;
  closing_cash_counted: string;
  system_expected_cash: string;
  cash_discrepancy: string;
  status: 'SUBMITTED' | 'VERIFIED' | 'DISCREPANCY_FLAGGED';
  supervisor_notes?: string;
  verified_by_id?: string;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  organization_id: string;
  user_id?: string;
  user_name?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details?: Record<string, any>;
  ip_address?: string;
  created_at: string;
}

export interface AIInsight {
  id: string;
  organization_id: string;
  insight_type: string;
  severity: string;
  title: string;
  summary: string;
  evidence: Record<string, any>;
  recommendation: string;
  is_acknowledged: boolean;
  created_at: string;
}

export interface InvestigationBriefing {
  transaction_id: string;
  amount: string;
  reference?: string;
  date: string;
  plain_language_explanation: string;
  root_cause_hypothesis: string;
  evidence_points: string[];
  suggested_investigator_action: string;
  confidence: number | null;
}
