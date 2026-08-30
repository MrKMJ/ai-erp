export interface Me {
  id: string;
  email: string;
  full_name: string;
  is_owner: boolean;
  roles: string[];
  permissions: string[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  tenant_id: string;
  user_id: string;
}

export interface ProfitLoss {
  revenue: number;
  expenses: number;
  net_profit: number;
  lines: { code: string; name: string; type: string; balance: number }[];
}

export interface CashFlow {
  horizon_days: number;
  opening_bank: number;
  expected_inflow: number;
  expected_outflow: number;
  projected_balance: number;
  shortfall: boolean;
}

export interface InventoryRow {
  product_id: string;
  sku: string;
  name: string;
  on_hand: number;
  reorder_level: number;
  safety_stock: number;
  avg_cost: number;
  below_reorder: boolean;
}

export interface Recommendation {
  id: string;
  type: string;
  severity: "info" | "low" | "medium" | "high";
  title: string;
  description: string;
  confidence: number;
  estimated_impact: string;
  suggested_action: Record<string, unknown>;
  entity_type: string | null;
  entity_id: string | null;
  status: string;
}

export interface ChatEvidence {
  name: string;
  result: unknown;
}

export interface ChatResponse {
  conversation_id: string;
  answer: string;
  evidence: ChatEvidence[];
}

export interface ToolSpec {
  name: string;
  description: string;
  risk: string;
  permission: string;
  allowed_for_you: boolean;
}
