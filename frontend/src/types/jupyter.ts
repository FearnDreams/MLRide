// Jupyter会话类型定义
export interface JupyterSession {
  id: number;
  project: number;
  token: string | null;
  url: string | null;
  status: 'creating' | 'running' | 'stopped' | 'error';
  created_at: string;
  updated_at: string;
}

// Jupyter API响应类型
export interface JupyterResponse {
  status: 'success' | 'error';
  message?: string;
  data?: JupyterSession;
}
