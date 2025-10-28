import { useEffect, useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  Plus,
  MessageSquare,
  CheckCircle,
  XCircle,
  Menu,
  X,
} from 'lucide-react';
import { useChatStore } from '../store/chat';
import { useWorkflowStore } from '../store/workflow';
import { apiClient } from '../services/api';
import Button from '../components/Button';
import Card from '../components/Card';
import type { ChatMessage as ChatMessageType } from '../types';

// Progress mapping: Map workflow phases to progress percentages
function getProgressPercentage(
  currentPhase: string,
  workflowStatus: string
): number {
  if (workflowStatus === 'completed') return 100;
  if (workflowStatus === 'failed') return 0;

  switch (currentPhase) {
    case 'supervisor':
      return 20;
    case 'content_creation':
      return 50;
    case 'tiktok':
      return 80;
    case 'youtube_shorts':
      return 90;
    case 'publishing':
      return 85;
    default:
      return 10;
  }
}

export default function Chat() {
  const {
    threads,
    currentThread,
    messages,
    isSending,
    setThreads,
    setCurrentThread,
    setMessages,
    addMessage,
    setIsSending,
    setError,
  } = useChatStore();

  const { workflows, addWorkflow, updateWorkflowById } = useWorkflowStore();
  const [inputMessage, setInputMessage] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadThreads = useCallback(async () => {
    try {
      const threadsData = await apiClient.listThreads();
      setThreads(threadsData);
      if (threadsData.length > 0 && !currentThread) {
        setCurrentThread(threadsData[0]);
      }
    } catch (error) {
      console.error('Failed to load threads:', error);
    }
  }, [setThreads, currentThread, setCurrentThread]);

  const loadMessages = useCallback(
    async (threadId: string) => {
      try {
        const messagesData = await apiClient.getMessages(threadId);
        setMessages(messagesData);
      } catch (error) {
        console.error('Failed to load messages:', error);
        setMessages([]);
      }
    },
    [setMessages]
  );

  // Load threads on mount
  useEffect(() => {
    loadThreads();
  }, [loadThreads]);

  // Load messages when thread changes
  useEffect(() => {
    if (currentThread) {
      loadMessages(currentThread.thread_id);
    }
  }, [currentThread, loadMessages]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isSending) return;

    const messageText = inputMessage.trim();
    setInputMessage('');
    setIsSending(true);
    setError(null);

    try {
      const response = await apiClient.sendMessage({
        thread_id: currentThread?.thread_id,
        message: messageText,
      });

      // Add user message
      addMessage(response.message);

      // Update thread list
      if (!currentThread) {
        setCurrentThread(response.thread);
        setThreads([response.thread, ...threads]);
      }

      // If workflow was created, add it
      if (response.workflow_created) {
        addWorkflow(response.workflow_created);
      }

      // AI response will come via backend
    } catch (error) {
      console.error('Failed to send message:', error);
      setError(
        error instanceof Error ? error.message : 'Failed to send message'
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleNewThread = () => {
    setCurrentThread(null);
    setMessages([]);
  };

  const handleApprove = async (messageId: string) => {
    if (!currentThread) return;

    try {
      const workflow = await apiClient.approveWorkflow(
        currentThread.thread_id,
        messageId
      );
      addWorkflow(workflow);

      // 🔌 WEBSOCKET: Connect to workflow updates
      const workflowId = workflow.workflow_id;
      if (workflowId) {
        connectToWorkflowUpdates(workflowId, currentThread.thread_id);
      }

      // Reload messages to see updated state
      loadMessages(currentThread.thread_id);
    } catch (error) {
      console.error('Failed to approve workflow:', error);
    }
  };

  // 🔌 WEBSOCKET: Real-time workflow updates
  const connectToWorkflowUpdates = useCallback(
    (workflowId: string, threadId: string) => {
      const wsUrl = `ws://localhost:8006/api/ws/workflows/${workflowId}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log(`WebSocket connected: ${workflowId}`);
      };

      ws.onmessage = (event) => {
        try {
          const update = JSON.parse(event.data);
          console.log('Workflow update:', update);

          // Reload messages when workflow updates (to show progress messages)
          if (
            update.event === 'node_completed' ||
            update.event === 'workflow_completed'
          ) {
            loadMessages(threadId);
          }

          // Update workflow in real-time based on phase changes
          if (update.event === 'node_completed') {
            // Map node names to workflow phases
            const phase =
              update.node === 'youtube_shorts'
                ? 'youtube_shorts'
                : update.node === 'tiktok'
                ? 'tiktok'
                : update.node === 'content_creation'
                ? 'content_creation'
                : update.node === 'supervisor'
                ? 'supervisor'
                : update.node;

            updateWorkflowById(workflowId, {
              current_phase: phase as any,
              workflow_status: update.workflow_status || 'running',
              total_cost_usd: update.total_cost_usd,
              cost_breakdown: update.cost_breakdown,
            });
          }

          // Handle workflow completion
          if (update.event === 'workflow_completed') {
            updateWorkflowById(workflowId, {
              workflow_status:
                update.status === 'completed' ? 'completed' : 'failed',
              current_phase: 'completed' as const,
              total_cost_usd: update.total_cost_usd || 0,
              publish_results: update.publish_results || {},
              video_path: update.video_url, // Use video_url from backend as video_path
              error_message: update.error,
            });
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log(`WebSocket closed: ${workflowId}`);
      };

      // Cleanup on unmount
      return () => {
        ws.close();
      };
    },
    [loadMessages, updateWorkflowById]
  );

  const handleReject = async (messageId: string) => {
    if (!currentThread) return;

    try {
      await apiClient.rejectWorkflow(
        currentThread.thread_id,
        messageId,
        'User rejected'
      );
      // Reload messages
      loadMessages(currentThread.thread_id);
    } catch (error) {
      console.error('Failed to reject workflow:', error);
    }
  };

  const activeWorkflows = workflows.filter(
    (w) => w.workflow_status === 'running' || w.workflow_status === 'pending'
  );

  const completedWorkflows = workflows.filter(
    (w) => w.workflow_status === 'completed'
  );

  return (
    <div className="flex h-[calc(100vh-8rem)] md:h-[calc(100vh-12rem)] lg:h-[calc(100vh-10rem)] gap-4 relative">
      {/* Mobile Hamburger Button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="md:hidden fixed top-4 left-4 z-50 p-2 bg-dark-800 rounded-lg border border-dark-700 hover:bg-dark-700 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors"
        aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/50 z-30"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Left Sidebar - Thread History */}
      <aside
        className={`w-full max-w-xs sm:max-w-sm md:w-80 flex-shrink-0 space-y-4 fixed md:relative inset-y-0 left-0 z-40 bg-dark-900 md:bg-transparent p-4 md:p-0 transition-transform duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
        aria-label="Thread history sidebar"
      >
        <Card className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Conversations</h2>
            <Button
              size="sm"
              onClick={handleNewThread}
              aria-label="Start new conversation"
            >
              <Plus className="w-4 h-4" />
            </Button>
          </div>

          <div className="space-y-2 max-h-[min(25rem,50vh)] overflow-y-auto">
            {threads.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-4">
                No conversations yet
              </p>
            ) : (
              threads.map((thread) => (
                <motion.button
                  key={thread.thread_id}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => {
                    setCurrentThread(thread);
                    setSidebarOpen(false);
                  }}
                  className={`w-full text-left p-3 rounded-lg transition-colors ${
                    currentThread?.thread_id === thread.thread_id
                      ? 'bg-primary-500/20 border-2 border-primary-500'
                      : 'bg-dark-800 hover:bg-dark-700'
                  }`}
                  aria-pressed={currentThread?.thread_id === thread.thread_id}
                >
                  <div className="flex items-start gap-2">
                    <MessageSquare
                      className="w-4 h-4 mt-1 flex-shrink-0"
                      aria-hidden="true"
                    />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm truncate">
                        {thread.title}
                      </p>
                      {thread.last_message && (
                        <p className="text-xs text-gray-400 truncate mt-1">
                          {thread.last_message}
                        </p>
                      )}
                    </div>
                  </div>
                </motion.button>
              ))
            )}
          </div>
        </Card>

        {/* Active Workflows Panel */}
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-3">Active Workflows</h3>
          {activeWorkflows.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-2">
              No active workflows
            </p>
          ) : (
            <div className="space-y-2 max-h-[min(18rem,30vh)] overflow-y-auto">
              {activeWorkflows.map((workflow) => (
                <div
                  key={workflow.workflow_id}
                  className="p-3 bg-dark-800 rounded-lg"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <p className="text-xs flex-1 truncate font-medium">
                      {workflow.user_request}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between items-center">
                      <p className="text-xs text-gray-400 capitalize">
                        {workflow.current_phase || 'Initializing'}
                      </p>
                      <p className="text-xs text-gray-500">
                        {workflow.workflow_status || 'running'}
                      </p>
                    </div>
                    {/* Animated status bar */}
                    <div className="w-full h-1.5 bg-dark-700 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-primary-500 to-secondary-500"
                        initial={{ width: '0%' }}
                        animate={{
                          width: `${getProgressPercentage(
                            workflow.current_phase || 'initializing',
                            workflow.workflow_status || 'running'
                          )}%`,
                        }}
                        transition={{
                          duration: 0.5,
                          ease: 'easeInOut',
                        }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Completed Workflows Panel */}
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-3">Recent Videos</h3>
          {completedWorkflows.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-2">
              No completed videos yet
            </p>
          ) : (
            <div className="space-y-2 max-h-[min(18rem,30vh)] overflow-y-auto">
              {completedWorkflows.slice(0, 5).map((workflow) => (
                <div
                  key={workflow.workflow_id}
                  className="p-3 bg-dark-800 rounded-lg hover:bg-dark-700 transition-colors"
                >
                  <p className="text-xs truncate font-medium mb-1">
                    {workflow.user_request}
                  </p>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-gray-400">
                      ${workflow.total_cost_usd?.toFixed(2) || '0.00'}
                    </span>
                    {workflow.video_path && (
                      <a
                        href={`http://localhost:8006/videos/${workflow.video_path.replace(
                          /^.*\/videos\//,
                          ''
                        )}`}
                        className="text-primary-400 hover:text-primary-300"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Watch →
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0">
        <Card className="flex-1 flex flex-col p-0 overflow-hidden">
          {/* Chat Header */}
          <div className="p-4 md:p-6 border-b border-dark-700 flex-shrink-0">
            <h2 className="text-lg md:text-xl font-semibold truncate">
              {currentThread ? currentThread.title : 'New Conversation'}
            </h2>
            <p className="text-sm text-gray-400 mt-1">
              Chat with the supervisor agent to create content
            </p>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-500">
                <p>Start a conversation to create content</p>
              </div>
            ) : (
              <AnimatePresence>
                {messages.map((message) => (
                  <ChatMessage
                    key={message.id}
                    message={message}
                    onApprove={() => handleApprove(message.id)}
                    onReject={() => handleReject(message.id)}
                  />
                ))}
              </AnimatePresence>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <form
            onSubmit={handleSendMessage}
            className="p-4 md:p-6 border-t border-dark-700 flex-shrink-0"
          >
            <div className="flex gap-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder="Ask me to create content for TikTok, YouTube Shorts..."
                disabled={isSending}
                className="flex-1 px-4 py-3 bg-dark-800 border border-dark-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                aria-label="Message input"
              />
              <Button
                type="submit"
                isLoading={isSending}
                disabled={!inputMessage.trim()}
                aria-label="Send message"
              >
                <Send className="w-5 h-5" />
              </Button>
            </div>
          </form>
        </Card>
      </main>
    </div>
  );
}

function ChatMessage({
  message,
  onApprove,
  onReject,
}: {
  message: ChatMessageType;
  onApprove: () => void;
  onReject: () => void;
}) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  const awaitingApproval = message.metadata?.awaiting_approval;
  const proposal = message.metadata?.workflow_proposal;
  const workflowCompleted = message.metadata?.workflow_completed;
  const videoUrl = message.metadata?.video_url;
  const publishResults = message.metadata?.publish_results;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-full sm:max-w-[85%] md:max-w-[75%] lg:max-w-[70%] rounded-lg p-3 md:p-4 ${
          isUser
            ? 'bg-primary-500 text-white'
            : isSystem
            ? 'bg-yellow-500/10 border border-yellow-500/20 text-yellow-300'
            : 'bg-dark-800 text-gray-100'
        }`}
        role="article"
        aria-label={`Message from ${
          isUser ? 'you' : isSystem ? 'system' : 'agent'
        }`}
      >
        <p className="text-sm md:text-base whitespace-pre-wrap break-words">
          {message.content}
        </p>

        {/* Workflow Proposal Approval UI */}
        {awaitingApproval && proposal && (
          <div className="mt-4 pt-4 border-t border-dark-700">
            <p className="text-xs font-semibold mb-2">Workflow Proposal:</p>
            <div className="space-y-1 text-xs md:text-sm">
              <p className="break-words">
                <span className="font-medium">Request:</span>{' '}
                {proposal.user_request}
              </p>
              <p>
                <span className="font-medium">Platforms:</span>{' '}
                {proposal.target_platforms.join(', ')}
              </p>
              {proposal.estimated_cost_usd && (
                <p>
                  <span className="font-medium">Est. Cost:</span> $
                  {proposal.estimated_cost_usd.toFixed(2)}
                </p>
              )}
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              <Button size="sm" variant="primary" onClick={onApprove}>
                <CheckCircle className="w-4 h-4" />
                <span className="hidden sm:inline">Approve</span>
              </Button>
              <Button size="sm" variant="outline" onClick={onReject}>
                <XCircle className="w-4 h-4" />
                <span className="hidden sm:inline">Reject</span>
              </Button>
            </div>
          </div>
        )}

        {/* Video Display for Completed Workflows */}
        {workflowCompleted && videoUrl && (
          <div className="mt-4 pt-4 border-t border-dark-700">
            <p className="text-xs font-semibold mb-2">Generated Video:</p>
            <video
              src={`http://localhost:8006${videoUrl}`}
              controls
              className="w-full max-w-md rounded-lg"
            />

            {/* Platform Links */}
            {publishResults && (
              <div className="flex flex-wrap gap-2 mt-3">
                {publishResults.tiktok?.status === 'success' && (
                  <a
                    href={publishResults.tiktok.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1 bg-primary-500/20 text-primary-400 rounded text-xs hover:bg-primary-500/30"
                  >
                    View on TikTok →
                  </a>
                )}
                {publishResults.youtube_shorts?.status === 'success' && (
                  <a
                    href={publishResults.youtube_shorts.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1 bg-red-500/20 text-red-400 rounded text-xs hover:bg-red-500/30"
                  >
                    View on YouTube →
                  </a>
                )}
                <a
                  href={`http://localhost:8006${videoUrl}`}
                  download
                  className="px-3 py-1 bg-gray-500/20 text-gray-400 rounded text-xs hover:bg-gray-500/30"
                >
                  Download Video ↓
                </a>
              </div>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
