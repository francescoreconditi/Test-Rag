export interface NavigationItem {
  id: string;
  label: string;
  icon: string;
  route: string;
  children?: NavigationItem[];
  badge?: string | number;
  disabled?: boolean;
}

export interface Theme {
  name: string;
  primary: string;
  accent: string;
  warn: string;
  isDark: boolean;
}

export interface NotificationMessage {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  autoClose?: boolean;
  duration?: number;
}

export interface LoadingState {
  isLoading: boolean;
  operation?: string;
  progress?: number;
}

export interface ErrorState {
  hasError: boolean;
  message?: string;
  code?: string;
  details?: any;
}

export interface FileUploadProgress {
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
}

export interface TableColumn<T = any> {
  key: keyof T;
  label: string;
  sortable?: boolean;
  filterable?: boolean;
  type?: 'text' | 'number' | 'date' | 'currency' | 'percentage';
  format?: (value: any) => string;
  width?: string;
}

export interface PaginationConfig {
  page: number;
  pageSize: number;
  totalItems: number;
  pageSizeOptions: number[];
}

export interface FilterConfig {
  field: string;
  operator: 'equals' | 'contains' | 'startsWith' | 'endsWith' | 'greaterThan' | 'lessThan';
  value: any;
}

export interface SortConfig {
  field: string;
  direction: 'asc' | 'desc';
}

export interface DialogConfig {
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  type?: 'confirm' | 'alert' | 'custom';
  data?: any;
}

export interface UserPreferences {
  theme: string;
  language: string;
  dateFormat: string;
  currency: string;
  timezone: string;
  notifications: {
    email: boolean;
    push: boolean;
    desktop: boolean;
  };
  dashboard: {
    defaultPage: string;
    autoRefresh: boolean;
    refreshInterval: number;
  };
}