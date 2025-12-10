import { useState, useCallback, useRef } from 'react';
import { chatAPI } from '../services/api';

// Generate unique ID using counter + timestamp
let messageIdCounter = 0;
const generateMessageId = () => `msg_${Date.now()}_${++messageIdCounter}`;

export function useChat(notebookId) {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Send a query
  const sendQuery = useCallback(async (query) => {
    if (!notebookId) {
      setError('No notebook selected');
      return;
    }

    // Add user message with unique ID
    const userMessage = {
      id: generateMessageId(),
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      setLoading(true);
      setError(null);

      const response = await chatAPI.query(notebookId, query);

      // Add assistant message with unique ID
      const assistantMessage = {
        id: generateMessageId(),
        role: 'assistant',
        content: response.data.answer,
        sources: response.data.sources,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);

      return response.data;
    } catch (err) {
      const errorMessage = err.response?.data?.detail || 'Failed to get response';
      setError(errorMessage);

      // Add error message to chat with unique ID
      const errorMsg = {
        id: generateMessageId(),
        role: 'error',
        content: errorMessage,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);

      // Don't re-throw to avoid unhandled promise rejection
    } finally {
      setLoading(false);
    }
  }, [notebookId]);

  // Clear messages
  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    loading,
    error,
    sendQuery,
    clearMessages,
  };
}
