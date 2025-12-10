import React, { useState, useRef, useEffect } from 'react';
import { MessageList } from './MessageList';
import { QueryInput } from './QueryInput';

export function ChatInterface({ messages, loading, onSendQuery, disabled }) {
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-500">
            <div className="text-center">
              <p className="text-lg font-medium mb-2">Ask questions about your documents</p>
              <p className="text-sm">
                Upload documents and start asking questions to get AI-powered answers
              </p>
            </div>
          </div>
        ) : (
          <>
            <MessageList messages={messages} />
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4 bg-white">
        <QueryInput onSend={onSendQuery} loading={loading} disabled={disabled} />
      </div>
    </div>
  );
}
