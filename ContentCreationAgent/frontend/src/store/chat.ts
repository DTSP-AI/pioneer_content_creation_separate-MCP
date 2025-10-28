import { create } from 'zustand'
import type { ChatThread, ChatMessage } from '../types'

interface ChatStore {
  threads: ChatThread[]
  currentThread: ChatThread | null
  messages: ChatMessage[]
  isLoading: boolean
  isSending: boolean
  error: string | null

  setThreads: (threads: ChatThread[]) => void
  addThread: (thread: ChatThread) => void
  setCurrentThread: (thread: ChatThread | null) => void
  setMessages: (messages: ChatMessage[]) => void
  addMessage: (message: ChatMessage) => void
  updateMessage: (messageId: string, updates: Partial<ChatMessage>) => void
  setIsLoading: (loading: boolean) => void
  setIsSending: (sending: boolean) => void
  setError: (error: string | null) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatStore>((set) => ({
  threads: [],
  currentThread: null,
  messages: [],
  isLoading: false,
  isSending: false,
  error: null,

  setThreads: (threads) => set({ threads }),

  addThread: (thread) =>
    set((state) => ({
      threads: [thread, ...state.threads],
    })),

  setCurrentThread: (thread) => set({ currentThread: thread }),

  setMessages: (messages) => set({ messages }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  updateMessage: (messageId, updates) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === messageId ? { ...msg, ...updates } : msg
      ),
    })),

  setIsLoading: (loading) => set({ isLoading: loading }),
  setIsSending: (sending) => set({ isSending: sending }),
  setError: (error) => set({ error }),
  clearMessages: () => set({ messages: [] }),
}))
