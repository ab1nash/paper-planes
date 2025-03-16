import React, { useState, useEffect } from 'react';
import api from '../services/api';

const PaperList = ({ onDeleteSuccess }) => {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPapers, setSelectedPapers] = useState([]);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // Fetch all papers on component mount
  useEffect(() => {
    fetchPapers();
  }, []);
  
  // Fetch all papers from the API
  const fetchPapers = async () => {
    try {
      setLoading(true);
      const result = await api.listAllPapers();
      setPapers(result.papers);
      setError(null);
    } catch (err) {
      setError(`Error loading papers: ${err.message}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  // Toggle paper selection
  const togglePaperSelection = (paperId) => {
    setSelectedPapers(prev => {
      if (prev.includes(paperId)) {
        return prev.filter(id => id !== paperId);
      } else {
        return [...prev, paperId];
      }
    });
  };
  
  // Select or deselect all papers
  const toggleSelectAll = () => {
    if (selectedPapers.length === papers.length) {
      setSelectedPapers([]);
    } else {
      setSelectedPapers(papers.map(paper => paper.id));
    }
  };
  
  // Open confirmation dialog
  const handleDeleteClick = () => {
    if (selectedPapers.length === 0) {
      return;
    }
    setShowConfirmation(true);
  };
  
  // Cancel deletion
  const cancelDelete = () => {
    setShowConfirmation(false);
  };
  
  // Confirm and execute deletion
  const confirmDelete = async () => {
    try {
      setIsDeleting(true);
      
      // Delete each selected paper
      const deletePromises = selectedPapers.map(paperId => 
        api.deletePaper(paperId)
      );
      
      await Promise.all(deletePromises);
      
      // Clear selection and refetch papers
      setSelectedPapers([]);
      fetchPapers();
      
      // Notify parent component
      if (onDeleteSuccess) {
        onDeleteSuccess(`Successfully deleted ${selectedPapers.length} paper(s)`);
      }
    } catch (err) {
      setError(`Error deleting papers: ${err.message}`);
    } finally {
      setIsDeleting(false);
      setShowConfirmation(false);
    }
  };
  
  // Format the list of authors
  const formatAuthors = (authors) => {
    if (!authors || authors.length === 0) return 'Unknown Authors';
    if (authors.length === 1) return authors[0];
    if (authors.length === 2) return `${authors[0]} and ${authors[1]}`;
    return `${authors[0]} et al.`;
  };
  
  // Show loading state
  if (loading) {
    return (
      <div className="bg-white shadow-md rounded-lg p-6 text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
        <p className="mt-2 text-gray-600">Loading papers...</p>
      </div>
    );
  }
  
  // Show error state
  if (error) {
    return (
      <div className="bg-white shadow-md rounded-lg p-6 text-center">
        <p className="text-red-500">{error}</p>
        <button 
          onClick={fetchPapers}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Try Again
        </button>
      </div>
    );
  }
  
  // Show empty state
  if (papers.length === 0) {
    return (
      <div className="bg-white shadow-md rounded-lg p-6 text-center">
        <p className="text-gray-600">No papers have been uploaded yet.</p>
      </div>
    );
  }
  
  return (
    <div className="bg-white shadow-md rounded-lg p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-medium">Manage Papers</h2>
        <div className="flex space-x-4">
          <button
            onClick={toggleSelectAll}
            className="px-3 py-1 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
          >
            {selectedPapers.length === papers.length ? 'Deselect All' : 'Select All'}
          </button>
          <button
            onClick={handleDeleteClick}
            disabled={selectedPapers.length === 0}
            className={`px-3 py-1 rounded ${
              selectedPapers.length === 0
                ? 'bg-red-300 cursor-not-allowed'
                : 'bg-red-600 text-white hover:bg-red-700'
            }`}
          >
            Delete Selected
          </button>
        </div>
      </div>
      
      {/* Papers list */}
      <div className="border rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Select
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Title
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Authors
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Year
              </th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {papers.map((paper) => (
              <tr key={paper.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={selectedPapers.includes(paper.id)}
                    onChange={() => togglePaperSelection(paper.id)}
                    className="h-4 w-4 text-blue-600 rounded"
                  />
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm font-medium text-gray-900">{paper.title}</div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-500">{formatAuthors(paper.authors)}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-500">{paper.publication_year || 'Unknown'}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <a
                    href={api.getPaperDownloadUrl(paper.id)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-900 mr-4"
                  >
                    Download
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {/* Confirmation Dialog */}
      {showConfirmation && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Confirm Deletion</h3>
            <p className="text-sm text-gray-500 mb-6">
              Are you sure you want to delete {selectedPapers.length} selected paper(s)? 
              This action cannot be undone.
            </p>
            <div className="flex justify-end space-x-4">
              <button
                onClick={cancelDelete}
                disabled={isDeleting}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                disabled={isDeleting}
                className={`px-4 py-2 rounded ${
                  isDeleting
                    ? 'bg-red-400 cursor-not-allowed'
                    : 'bg-red-600 text-white hover:bg-red-700'
                }`}
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PaperList;