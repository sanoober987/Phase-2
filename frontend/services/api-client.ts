// ======================================================
// API CLIENT — PRODUCTION SAFE VERSION (HACKATHON READY)
// ======================================================

import { getAuthHeaders, logout, redirectToLogin } from "@/lib/auth";
import {
  Task,
  TaskCreateData,
  TaskUpdateData,
  TaskListResponse,
  TaskQueryParams,
  ChatRequest,
  ChatResponse,
} from "@/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const REQUEST_TIMEOUT = 120000;

// ======================================================
// API ERROR CLASS (MUST EXPORT)
// ======================================================

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// ======================================================
// API SERVICE
// ======================================================

class TaskApiService {

  // -----------------------------
  // Core Request Handler
  // -----------------------------

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {

    const controller = new AbortController();
    const timeoutId = setTimeout(
      () => controller.abort(),
      REQUEST_TIMEOUT
    );

    try {
      const response = await fetch(
        `${API_BASE_URL}${endpoint}`,
        {
          ...options,
          headers: {
            "Content-Type": "application/json",
            ...getAuthHeaders(),
          },
          signal: controller.signal,
        }
      );

      clearTimeout(timeoutId);

      // Auth expired
      if (response.status === 401) {
        logout();
        redirectToLogin();
        throw new ApiError("Session expired", 401);
      }

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));

        throw new ApiError(
          data.detail || `Request failed (${response.status})`,
          response.status
        );
      }

      if (response.status === 204) {
        return undefined as unknown as T;
      }

      return response.json();
    }
    catch (err: any) {
      clearTimeout(timeoutId);

      if (err.name === "AbortError") {
        throw new ApiError("Request timeout", 408);
      }

      throw err;
    }
  }

  // ======================================================
  // TASK APIs
  // ======================================================

  async getTasks(params?: TaskQueryParams): Promise<TaskListResponse> {
    const query = new URLSearchParams();

    if (params?.completed !== undefined)
      query.append("completed", String(params.completed));

    if (params?.limit !== undefined)
      query.append("limit", String(params.limit));

    if (params?.offset !== undefined)
      query.append("offset", String(params.offset));

    const endpoint =
      "/api/tasks" + (query.toString() ? `?${query}` : "");

    return this.request<TaskListResponse>(endpoint, {
      method: "GET",
    });
  }

  async createTask(data: TaskCreateData): Promise<Task> {
    return this.request<Task>("/api/tasks", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async patchTask(
    id: string,
    data: TaskUpdateData
  ): Promise<Task> {
    return this.request<Task>(`/api/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteTask(id: string): Promise<void> {
    return this.request<void>(`/api/tasks/${id}`, {
      method: "DELETE",
    });
  }

  async toggleComplete(id: string): Promise<Task> {
    return this.request<Task>(`/api/tasks/${id}/complete`, {
      method: "PATCH",
    });
  }

  // ======================================================
  // CHAT API
  // ======================================================

  async sendChatMessage(
    userId: string,
    body: ChatRequest
  ): Promise<ChatResponse> {
    return this.request<ChatResponse>(
      `/api/${userId}/chat`,
      {
        method: "POST",
        body: JSON.stringify(body),
      }
    );
  }
}

// ======================================================
// EXPORT SINGLETON INSTANCE
// ======================================================

export const taskApiService = new TaskApiService();