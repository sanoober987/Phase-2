"use client";

import { useEffect, useRef } from 'react';
import { useChat } from '@/hooks/useChat';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';

interface ChatPanelProps {
  userId: string;
  onTasksChanged?: () => void;
}

export function ChatPanel({ userId, onTasksChanged }: ChatPanelProps) {
  const { messages, isLoading, error, sendMessage, clearError } = useChat({ userId, onTasksChanged });
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  return (
    <div className="flex flex-col h-full min-h-[400px] max-h-[600px] rounded-2xl border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/50">
        <div className="h-2 w-2 rounded-full bg-green-500" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">AI Task Assistant</h2>
        <span className="ml-auto text-xs text-zinc-400">Type a command or ask a question</span>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-center py-8">
            <p className="text-zinc-400 dark:text-zinc-500 text-sm">No messages yet. Try saying:</p>
            <ul className="text-xs text-zinc-400 dark:text-zinc-500 space-y-1">
              <li>&ldquo;Add a task: Buy groceries&rdquo;</li>
              <li>&ldquo;Show my pending tasks&rdquo;</li>
              <li>&ldquo;Mark Buy groceries as complete&rdquo;</li>
            </ul>
          </div>
        )}
        {messages.map((msg) => <ChatMessage key={msg.id} message={msg} />)}
        {isLoading && (
          <div className="flex justify-start mb-3">
            <div className="bg-zinc-100 dark:bg-zinc-800 rounded-2xl rounded-bl-sm px-4 py-2.5">
              <span className="flex gap-1 items-center">
                <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 bg-zinc-400 rounded-full animate-bounce [animation-delay:300ms]" />
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      {error && (
        <div className="mx-4 mb-2 flex items-start gap-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-3 py-2 text-xs text-red-700 dark:text-red-300">
          <span className="flex-1">{error}</span>
          <button onClick={clearError} className="ml-auto text-red-400 hover:text-red-600 font-bold leading-none" aria-label="Dismiss error">×</button>
        </div>
      )}
      <div className="px-4 pb-4">
        <ChatInput onSend={sendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
}
