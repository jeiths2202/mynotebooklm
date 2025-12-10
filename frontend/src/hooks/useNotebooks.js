import { useState, useEffect, useCallback } from 'react';
import { notebooksAPI, documentsAPI } from '../services/api';

export function useNotebooks() {
  const [notebooks, setNotebooks] = useState([]);
  const [currentNotebook, setCurrentNotebook] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch all notebooks
  const fetchNotebooks = useCallback(async () => {
    try {
      setLoading(true);
      const response = await notebooksAPI.list();
      setNotebooks(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch notebooks');
    } finally {
      setLoading(false);
    }
  }, []);

  // Create a new notebook
  const createNotebook = useCallback(async (name) => {
    try {
      setLoading(true);
      const response = await notebooksAPI.create(name);
      setNotebooks((prev) => [response.data, ...prev]);
      setError(null);
      return response.data;
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create notebook');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Delete a notebook
  const deleteNotebook = useCallback(async (notebookId) => {
    try {
      setLoading(true);
      await notebooksAPI.delete(notebookId);
      setNotebooks((prev) => prev.filter((n) => n.id !== notebookId));
      if (currentNotebook?.id === notebookId) {
        setCurrentNotebook(null);
        setDocuments([]);
      }
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete notebook');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [currentNotebook]);

  // Select a notebook
  const selectNotebook = useCallback(async (notebook) => {
    setCurrentNotebook(notebook);
    if (notebook) {
      try {
        const response = await documentsAPI.list(notebook.id);
        setDocuments(response.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Failed to fetch documents');
        setDocuments([]);
      }
    } else {
      setDocuments([]);
    }
  }, []);

  // Upload a document
  const uploadDocument = useCallback(async (file, onProgress) => {
    if (!currentNotebook) {
      throw new Error('No notebook selected');
    }

    try {
      setLoading(true);
      const response = await documentsAPI.upload(currentNotebook.id, file, onProgress);
      setDocuments((prev) => [response.data, ...prev]);
      // Update notebook document count
      setNotebooks((prev) =>
        prev.map((n) =>
          n.id === currentNotebook.id
            ? { ...n, document_count: n.document_count + 1 }
            : n
        )
      );
      setError(null);
      return response.data;
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload document');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [currentNotebook]);

  // Delete a document
  const deleteDocument = useCallback(async (documentId) => {
    try {
      setLoading(true);
      await documentsAPI.delete(documentId);
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
      // Update notebook document count
      if (currentNotebook) {
        setNotebooks((prev) =>
          prev.map((n) =>
            n.id === currentNotebook.id
              ? { ...n, document_count: Math.max(0, n.document_count - 1) }
              : n
          )
        );
      }
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete document');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [currentNotebook]);

  // Fetch notebooks on mount
  useEffect(() => {
    fetchNotebooks();
  }, [fetchNotebooks]);

  return {
    notebooks,
    currentNotebook,
    documents,
    loading,
    error,
    fetchNotebooks,
    createNotebook,
    deleteNotebook,
    selectNotebook,
    uploadDocument,
    deleteDocument,
    clearError: () => setError(null),
  };
}
