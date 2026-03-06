// Auth Types
export interface User {
  id: string;
  email: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface SignInCredentials {
  email: string;
  password: string;
}

export interface SignUpCredentials {
  email: string;
  password: string;
  confirmPassword: string;
}

// Task Types — aligned with backend TaskResponse schema
export interface Task {
  id: string; // UUID from backend
  title: string;
  description: string | null;
  completed: boolean; // matches backend field name
  user_id: string; // matches backend field name
  created_at: string;
  updated_at: string;
}

export interface TaskCreateData {
  title: string;
  description?: string;
}

export interface TaskUpdateData {
  title?: string;
  description?: string;
  completed?: boolean;
}

// Backend returns { tasks: [], count: number }
export interface TaskListResponse {
  tasks: Task[];
  count: number;
}

export interface TaskQueryParams {
  completed?: boolean;
  limit?: number;
  offset?: number;
}

// Tasks State (for useTasks hook)
export interface TasksState {
  items: Task[];
  total: number;
  isLoading: boolean;
  error: string | null;
  filter: {
    isCompleted: boolean | null;
  };
  pagination: {
    limit: number;
    offset: number;
  };
}

// API Error Types
export interface ErrorResponse {
  detail: string;
  error_code: string | null;
  timestamp: string;
}

// Form Types
export interface TaskFormData {
  title: string;
  description: string;
}

// Toast Types
export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

// Chat Types
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

export interface ToolCallRecord {
  tool: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown>;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
}

export interface ChatResponse {
  reply: string;
  tool_calls: ToolCallRecord[];
  conversation_id: string;
}
