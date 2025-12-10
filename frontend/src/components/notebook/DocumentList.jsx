import React from 'react';
import { FileText, File, Trash2, Calendar, Layers } from 'lucide-react';

const FILE_ICONS = {
  '.pdf': FileText,
  '.txt': File,
  '.docx': FileText,
};

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function DocumentList({ documents, onDeleteDocument, loading }) {
  if (documents.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No documents yet</p>
        <p className="text-xs">Upload documents to start asking questions</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-gray-700 mb-3">Documents</h3>
      <ul className="space-y-2">
        {documents.map((doc) => {
          const IconComponent = FILE_ICONS[doc.file_type] || File;

          return (
            <li
              key={doc.id}
              className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
            >
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <IconComponent className="w-5 h-5 text-blue-600" />
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate">
                  {doc.filename}
                </p>
                <div className="flex items-center gap-3 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <Layers className="w-3 h-3" />
                    {doc.chunk_count} chunks
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {formatDate(doc.uploaded_at)}
                  </span>
                </div>
              </div>

              <button
                onClick={() => onDeleteDocument(doc.id)}
                disabled={loading}
                className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg opacity-0 group-hover:opacity-100 transition-all disabled:opacity-50"
                title="Delete document"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
