import React from 'react';
import { BookOpen, Settings } from 'lucide-react';

export function Header({ notebook }) {
  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      <div className="flex items-center gap-3">
        {notebook ? (
          <>
            <BookOpen className="w-5 h-5 text-blue-600" />
            <h2 className="text-lg font-semibold text-gray-800">{notebook.name}</h2>
            <span className="text-sm text-gray-500">
              ({notebook.document_count} document{notebook.document_count !== 1 ? 's' : ''})
            </span>
          </>
        ) : (
          <h2 className="text-lg font-semibold text-gray-500">Select a notebook</h2>
        )}
      </div>
    </header>
  );
}
