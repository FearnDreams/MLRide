// Jupyter会话类型定义
export interface JupyterSession {
  id: number;
  project: number;
  token: string | null;
  url: string | null;
  port: number | null;
  workspace_dir: string | null;
  process_id: number | null;
  status: 'creating' | 'running' | 'stopped' | 'error';
  created_at: string;
  updated_at: string;
  direct_access_url?: string | null;  // 直接访问URL
}

// Jupyter API响应类型
export interface JupyterResponse {
  status: 'success' | 'warning' | 'error';
  message: string;
  data?: any;
  error_details?: string;
}
