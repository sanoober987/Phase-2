"use client";

import { useState, useCallback, useRef } from 'react';
import { ChatMessage, ChatRequest } from '@/types';
import { getAuthHeaders } from '@/lib/auth';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface UseChatOptions {
  userId: string;
  onTasksChanged?: () => void;
}

interface UseChatReturn {
  messages: ChatMessage[];
  conversationId: string | null;
  isLoading: boolean;
  error: string | null;
  sendMessage: (text: string) => Promise<void>;
  clearError: () => void;
}

let _messageCounter = 0;
function nextId(): string {
  return `msg-${++_messageCounter}-${Date.now()}`;
}

export function useChat({ userId, onTasksChanged }: UseChatOptions): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      // Optimistically append user message
      const userMsg: ChatMessage = { id: nextId(), role: 'user', content: text.trim() };
      const assistantMsgId = nextId();
      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      // Abort any in-flight stream
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const req: ChatRequest = {
          message: text.trim(),
          ...(conversationId ? { conversation_id: conversationId } : {}),
        };

        // Use streaming endpoint
        const response = await fetch(
          `${API_BASE_URL}/api/${userId}/chat/stream`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...getAuthHeaders(),
            },
            body: JSON.stringify(req),
            signal: controller.signal,
          }
        );

        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data.detail || `Request failed (${response.status})`);
        }

        // Add empty assistant message that we'll stream into
        setMessages((prev) => [
          ...prev,
          { id: assistantMsgId, role: 'assistant', content: '' },
        ]);

        // Read SSE stream
        const reader = response.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Process complete SSE events (delimited by double newline)
          const events = buffer.split('\n\n');
          buffer = events.pop() || ''; // Keep incomplete event in buffer

          for (const eventBlock of events) {
            if (!eventBlock.trim()) continue;

            const lines = eventBlock.split('\n');
            let eventType = '';
            let eventData = '';

            for (const line of lines) {
              if (line.startsWith('event: ')) {
                eventType = line.slice(7).trim();
              } else if (line.startsWith('data: ')) {
                eventData = line.slice(6);
              }
            }

            if (!eventData) continue;

            try {
              const parsed = JSON.parse(eventData);

              if (eventType === 'token') {
                // Append text chunk to the assistant message
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMsgId
                      ? { ...m, content: m.content + parsed.text }
                      : m
                  )
                );
              } else if (eventType === 'done') {
                // Stream complete — store conversation ID
                if (parsed.conversation_id && !conversationId) {
                  setConversationId(parsed.conversation_id);
                }
                if (onTasksChanged) {
                  onTasksChanged();
                }
              } else if (eventType === 'error') {
                throw new Error(parsed.error || 'Stream error');
              }
            } catch (parseErr) {
              // If JSON parse fails for a token event, skip it
              if (eventType === 'error') {
                throw parseErr;
              }
            }
          }
        }
      } catch (err) {
        if ((err as Error).name === 'AbortError') {
          // User cancelled — don't show error
          return;
        }
        const message =
          err instanceof Error
            ? err.message
            : 'Failed to send message. Please try again.';
        setError(message);
        // Remove optimistically added messages on error
        setMessages((prev) =>
          prev.filter((m) => m.id !== userMsg.id && m.id !== assistantMsgId)
        );
      } finally {
        setIsLoading(false);
        abortRef.current = null;
      }
    },
    [userId, conversationId, isLoading, onTasksChanged]
  );

  const clearError = useCallback(() => setError(null), []);

  return { messages, conversationId, isLoading, error, sendMessage, clearError };
}
