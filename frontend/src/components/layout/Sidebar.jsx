import React, { useState } from 'react';
import { BookOpen, Plus, Trash2, FileText } from 'lucide-react';

export function Sidebar({
  notebooks,
  currentNotebook,
  onSelectNotebook,
  onCreateNotebook,
  onDeleteNotebook,
  loading,
}) {
  const [newNotebookName, setNewNotebookName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newNotebookName.trim()) return;

    try {
      await onCreateNotebook(newNotebookName.trim());
      setNewNotebookName('');
      setIsCreating(false);
    } catch (err) {
      console.error('Failed to create notebook:', err);
    }
  };

  const handleDelete = async (e, notebookId) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this notebook?')) {
      try {
        await onDeleteNotebook(notebookId);
      } catch (err) {
        console.error('Failed to delete notebook:', err);
      }
    }
  };

  return (
    <aside className="w-64 bg-gray-900 text-white flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <BookOpen className="w-6 h-6 text-blue-400" />
          <h1 className="text-lg font-semibold">NotebookLM</h1>
        </div>
      </div>

      {/* Create Notebook */}
      <div className="p-4 border-b border-gray-700">
        {isCreating ? (
          <form onSubmit={handleCreate} className="space-y-2">
            <input
              type="text"
              value={newNotebookName}
              onChange={(e) => setNewNotebookName(e.target.value)}
              placeholder="Notebook name..."
              className="w-full px-3 py-2 bg-gray-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={!newNotebookName.trim() || loading}
                className="flex-1 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm disabled:opacity-50"
              >
                Create
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsCreating(false);
                  setNewNotebookName('');
                }}
                className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
              >
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <button
            onClick={() => setIsCreating(true)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>New Notebook</span>
          </button>
        )}
      </div>

      {/* Notebooks List */}
      <div className="flex-1 overflow-y-auto p-2">
        {notebooks.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No notebooks yet</p>
            <p className="text-xs">Create one to get started</p>
          </div>
        ) : (
          <ul className="space-y-1">
            {notebooks.map((notebook) => (
              <li key={notebook.id}>
                <button
                  onClick={() => onSelectNotebook(notebook)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-left transition-colors group ${
                    currentNotebook?.id === notebook.id
                      ? 'bg-blue-600 text-white'
                      : 'hover:bg-gray-800 text-gray-300'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm font-medium">{notebook.name}</p>
                    <p className="text-xs opacity-70">
                      {notebook.document_count} document{notebook.document_count !== 1 ? 's' : ''}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleDelete(e, notebook.id)}
                    className={`p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity ${
                      currentNotebook?.id === notebook.id
                        ? 'hover:bg-blue-700'
                        : 'hover:bg-gray-700'
                    }`}
                    title="Delete notebook"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
