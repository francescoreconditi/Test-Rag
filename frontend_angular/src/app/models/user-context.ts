/**
 * User Context and Authentication Models
 * Mirrors the Python backend authentication system
 */

export enum UserRole {
  ADMIN = 'admin',
  ANALYST = 'analyst',
  VIEWER = 'viewer',
  GUEST = 'guest'
}

export enum TenantTier {
  FREE = 'free',
  PROFESSIONAL = 'professional',
  ENTERPRISE = 'enterprise'
}

export interface LoginRequest {
  email: string;
  password: string;
  tenant_id?: string;
}

export interface LoginResponse {
  success: boolean;
  user?: UserContext;
  token?: string;
  refresh_token?: string;
  tenants?: TenantContext[];
  error?: string;
  message?: string;
}

export interface UserContext {
  user_id: string;
  email: string;
  role: UserRole;
  tenant_id: string;
  tenant_name: string;
  tenant_tier: TenantTier;
  permissions: string[];
  session_expires_at: Date;
  last_login?: Date;
}

export interface TenantContext {
  tenant_id: string;
  name: string;
  tier: TenantTier;
  created_at?: Date;
  is_active?: boolean;
  max_users?: number;
  max_documents?: number;
  features: string[];
  user_count?: number;
  document_count?: number;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: UserContext | null;
  tenants: TenantContext[];
  currentTenant: TenantContext | null;
  loading: boolean;
  error: string | null;
}

export interface SecurityEvent {
  event_type: string;
  user_id: string;
  tenant_id: string;
  details: any;
  timestamp: Date;
  ip_address?: string;
}