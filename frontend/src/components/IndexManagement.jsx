import React, { useState, useEffect } from 'react';
import api from '../services/api';

const IndexManagement = ({ onSuccess, onError }) => {
  const [isRebuildingIndex, setIsRebuildingIndex] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [showRebuildConfirmation, setShowRebuildConfirmation] = useState(false);
  const [showRollbackConfirmation, setShowRollbackConfirmation] = useState(false);
  const [indexStatus, setIndexStatus] = useState(null);
  const [useParagraphs, setUseParagraphs] = useState(false);
  const [isLoadingStatus, setIsLoadingStatus] = useState(false);
  
  useEffect(() => {
    fetchIndexStatus();
  }, []);
  
  const fetchIndexStatus = async () => {
    try {
      setIsLoadingStatus(true);
      const status = await api.getIndexStatus();
      setIndexStatus(status);
    } catch (err) {
      onError(`Error fetching index status: ${err.message}`);
    } finally {
      setIsLoadingStatus(false);
    }
  };
  
  const handleRebuildClick = () => {
    setShowRebuildConfirmation(true);
  };
  
  const handleRollbackClick = () => {
    setShowRollbackConfirmation(true);
  };
  
  const cancelRebuild = () => {
    setShowRebuildConfirmation(false);
  };
  
  const cancelRollback = () => {
    setShowRollbackConfirmation(false);
  };
  
  const confirmRebuild = async () => {
    try {
      setIsRebuildingIndex(true);
      
      const result = await api.rebuildIndexes(useParagraphs);
      
      onSuccess(`Index rebuilt successfully. ${result.message || ''}`);
      fetchIndexStatus(); // Refresh status
    } catch (err) {
      onError(`Error rebuilding index: ${err.message}`);
    } finally {
      setIsRebuildingIndex(false);
      setShowRebuildConfirmation(false);
    }
  };
  
  const confirmRollback = async () => {
    try {
      setIsRollingBack(true);
      
      const result = await api.rollbackIndex();
      
      onSuccess(`Index rolled back successfully. ${result.message || ''}`);
      fetchIndexStatus(); // Refresh status
    } catch (err) {
      onError(`Error rolling back index: ${err.message}`);
    } finally {
      setIsRollingBack(false);
      setShowRollbackConfirmation(false);
    }
  };
  
  // Format date string
  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };
  
  return (
    <div className="bg-white shadow-md rounded-lg p-6 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-medium">Index Management</h2>
        <button 
          onClick={fetchIndexStatus}
          disabled={isLoadingStatus}
          className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          {isLoadingStatus ? 'Loading...' : 'Refresh Status'}
        </button>
      </div>
      
      {/* Index Status */}
      {indexStatus ? (
        <div className="mb-4 p-3 bg-gray-50 rounded-md">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Current Index Status</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>Documents indexed:</div>
            <div className="font-medium">{indexStatus.index.total_documents}</div>
            
            <div>Last updated:</div>
            <div className="font-medium">{formatDate(indexStatus.index.last_updated)}</div>
            
            {indexStatus.index.using_hybrid !== undefined && (
              <>
                <div>Index type:</div>
                <div className="font-medium">
                  {indexStatus.index.using_hybrid ? 'Hybrid (HNSW+Flat)' : 'Flat'}
                </div>
              </>
            )}
            
            <div>Backup available:</div>
            <div className="font-medium">
              {indexStatus.has_backup ? (
                <span className="text-green-600">Yes</span>
              ) : (
                <span className="text-gray-500">No</span>
              )}
            </div>
            
            {indexStatus.has_backup && indexStatus.backup_info && (
              <>
                <div>Backup created:</div>
                <div className="font-medium">{formatDate(indexStatus.backup_info.timestamp)}</div>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="mb-4 p-3 bg-gray-50 rounded-md text-center text-gray-500">
          {isLoadingStatus ? 'Loading index status...' : 'Index status not available'}
        </div>
      )}
      
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Rebuild Index Button */}
        <div className="flex-1">
          <button
            onClick={handleRebuildClick}
            disabled={isRebuildingIndex || isRollingBack}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-blue-300"
          >
            Rebuild Index
          </button>
          <p className="text-xs text-gray-500 mt-1">
            Rebuilds the search index. This may take time for large collections.
          </p>
        </div>
        
        {/* Rollback Index Button */}
        <div className="flex-1">
          <button
            onClick={handleRollbackClick}
            disabled={isRebuildingIndex || isRollingBack || !indexStatus?.has_backup}
            className={`w-full px-4 py-2 rounded ${
              indexStatus?.has_backup 
                ? 'bg-amber-600 text-white hover:bg-amber-700' 
                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
            }`}
          >
            Rollback to Previous Index
          </button>
          <p className="text-xs text-gray-500 mt-1">
            Restores the previous index version from backup.
          </p>
        </div>
      </div>
      
      {/* Rebuild Confirmation Dialog */}
      {showRebuildConfirmation && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Confirm Index Rebuild</h3>
            <p className="text-sm text-gray-500 mb-4">
              This will rebuild the vector search index for all documents. The operation may take 
              several minutes depending on your collection size. A backup of the current index 
              will be created first.
            </p>
            
            {/* Paragraph option */}
            <div className="mb-4">
              <label className="flex items-center text-sm">
                <input
                  type="checkbox"
                  checked={useParagraphs}
                  onChange={(e) => setUseParagraphs(e.target.checked)}
                  className="mr-2 h-4 w-4"
                />
                Rebuild with paragraph-level indexing
              </label>
              <p className="text-xs text-gray-500 mt-1 ml-6">
                Enable for more precise search results at paragraph level
              </p>
            </div>
            
            <div className="flex justify-end space-x-4">
              <button
                onClick={cancelRebuild}
                disabled={isRebuildingIndex}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={confirmRebuild}
                disabled={isRebuildingIndex}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                {isRebuildingIndex ? 'Rebuilding...' : 'Rebuild Index'}
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Rollback Confirmation Dialog */}
      {showRollbackConfirmation && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Confirm Index Rollback</h3>
            <p className="text-sm text-gray-500 mb-4">
              This will restore the previous version of the search index from backup. 
              Any changes made since the backup was created will be lost.
            </p>
            {indexStatus?.backup_info && (
              <p className="text-sm bg-blue-50 p-2 rounded mb-4">
                Backup created: {formatDate(indexStatus.backup_info.timestamp)}
              </p>
            )}
            <div className="flex justify-end space-x-4">
              <button
                onClick={cancelRollback}
                disabled={isRollingBack}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={confirmRollback}
                disabled={isRollingBack}
                className="px-4 py-2 bg-amber-600 text-white rounded hover:bg-amber-700"
              >
                {isRollingBack ? 'Rolling Back...' : 'Rollback Index'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IndexManagement;