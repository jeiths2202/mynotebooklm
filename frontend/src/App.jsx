import React, { useEffect } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { DocumentUpload } from './components/notebook/DocumentUpload';
import { DocumentList } from './components/notebook/DocumentList';
import { ChatInterface } from './components/chat/ChatInterface';
import { useNotebooks } from './hooks/useNotebooks';
import { useChat } from './hooks/useChat';
import { AlertCircle, BookOpen } from 'lucide-react';

function App() {
  const {
    notebooks,
    currentNotebook,
    documents,
    loading: notebookLoading,
    error: notebookError,
    createNotebook,
    deleteNotebook,
    selectNotebook,
    uploadDocument,
    deleteDocument,
    clearError,
  } = useNotebooks();

  const {
    messages,
    loading: chatLoading,
    sendQuery,
    clearMessages,
  } = useChat(currentNotebook?.id);

  // Clear chat messages when notebook changes
  useEffect(() => {
    clearMessages();
  }, [currentNotebook?.id, clearMessages]);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar
        notebooks={notebooks}
        currentNotebook={currentNotebook}
        onSelectNotebook={selectNotebook}
        onCreateNotebook={createNotebook}
        onDeleteNotebook={deleteNotebook}
        loading={notebookLoading}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header notebook={currentNotebook} />

        {/* Error Banner */}
        {notebookError && (
          <div className="bg-red-50 border-b border-red-200 px-4 py-2 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-500" />
            <span className="text-sm text-red-700">{notebookError}</span>
            <button
              onClick={clearError}
              className="ml-auto text-red-500 hover:text-red-700 text-sm"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Content Area */}
        {currentNotebook ? (
          <div className="flex-1 flex overflow-hidden">
            {/* Left Panel: Documents */}
            <div className="w-80 border-r border-gray-200 bg-white p-4 overflow-y-auto">
              <DocumentUpload
                onUpload={uploadDocument}
                disabled={notebookLoading}
              />
              <DocumentList
                documents={documents}
                onDeleteDocument={deleteDocument}
                loading={notebookLoading}
              />
            </div>

            {/* Right Panel: Chat */}
            <div className="flex-1 flex flex-col bg-white">
              <ChatInterface
                messages={messages}
                loading={chatLoading}
                onSendQuery={sendQuery}
                disabled={documents.length === 0}
              />
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <BookOpen className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <h2 className="text-xl font-medium mb-2">Welcome to NotebookLM Clone</h2>
              <p className="text-sm">
                Create or select a notebook from the sidebar to get started
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
