import React, { useState } from 'react';
import SearchForm from './components/SearchForm';
import ResultList from './components/ResultList';
import UploadForm from './components/UploadForm';
import PaperList from './components/PaperList';
import api from './services/api';

/**
 * Main application component
 */
const App = () => {
  // Application state
  const [activeTab, setActiveTab] = useState('search');
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [notification, setNotification] = useState(null);
  
  /**
   * Handle search submission
   * @param {Object} searchRequest - Search parameters
   */
  const handleSearch = async (searchRequest) => {
    try {
      setIsSearching(true);
      setSearchResults(null);
      
      const results = await api.search(searchRequest);
      setSearchResults(results);
    } catch (error) {
      showNotification('error', `Search failed: ${error.message}`);
    } finally {
      setIsSearching(false);
    }
  };
  
  /**
   * Handle paper upload
   * @param {FormData} formData - Form data with file and metadata
   */
  const handleUpload = async (formData) => {
    try {
      setIsUploading(true);
      
      const result = await api.uploadPaper(formData);
      
      showNotification('success', `Paper "${result.metadata.title}" uploaded successfully`);
      
      // Reset upload form (implementation depends on your form design)
      // You might need to pass a callback to the UploadForm component
    } catch (error) {
      showNotification('error', `Upload failed: ${error.message}`);
    } finally {
      setIsUploading(false);
    }
  };
  
  /**
   * Display a notification message
   * @param {string} type - Notification type ('success', 'error', 'info')
   * @param {string} message - Notification message
   */
  const showNotification = (type, message) => {
    setNotification({ type, message });
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      setNotification(null);
    }, 5000);
  };
  
  /**
   * Dismiss the current notification
   */
  const dismissNotification = () => {
    setNotification(null);
  };
  
  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-2xl font-bold text-gray-900">Paper Planes v0.1</h1>
          <p className="mt-1 text-sm text-gray-600">
            An offline semantic search for research papers
          </p>
        </div>
      </header>
      
      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tabs */}
        <div className="mb-8 border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('search')}
              className={`${
                activeTab === 'search'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              Search Papers
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              className={`${
                activeTab === 'upload'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              Upload Papers
            </button>
            <button
              onClick={() => setActiveTab('manage')}
              className={`${activeTab === 'manage'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
            >
              Manage Papers
            </button>
          </nav>
        </div>
        
        {/* Notification */}
        {notification && (
          <div className={`mb-6 p-4 rounded-md ${
            notification.type === 'error' 
              ? 'bg-red-50 text-red-800' 
              : notification.type === 'success'
                ? 'bg-green-50 text-green-800'
                : 'bg-blue-50 text-blue-800'
          }`}>
            <div className="flex">
              <div className="flex-1">
                {notification.message}
              </div>
              <button 
                onClick={dismissNotification}
                className="ml-4 text-sm font-medium"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}
        
        {/* Tab content */}
        {activeTab === 'search' && (
          <div>
            <SearchForm onSearch={handleSearch} isLoading={isSearching} />
            
            {isSearching && (
              <div className="text-center py-8">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
                <p className="mt-2 text-gray-600">Searching...</p>
              </div>
            )}
            
            {!isSearching && searchResults && (
              <ResultList 
                results={searchResults.results} 
                totalCount={searchResults.total_count}
                query={searchResults.query}
                executionTime={searchResults.execution_time_ms}
              />
            )}
            
            {!isSearching && !searchResults && (
              <div className="text-center py-12">
                <p className="text-gray-500">
                  Enter your search query above to find relevant research papers.
                </p>
              </div>
            )}
          </div>
        )}
        
        {activeTab === 'upload' && (
          <UploadForm onUpload={handleUpload} isUploading={isUploading} />
        )}

        {activeTab === 'manage' && (
          <PaperList onDeleteSuccess={(message) => showNotification('success', message)} />
        )}
      </main>
      
      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-center">
            <p className="text-sm text-gray-500 mr-3">
              paper-planes - 2025
            </p>
            {/* Indian Flag Image */}
            <div className="h-6 w-9 shadow-sm border border-gray-200 rounded overflow-hidden">
              <img
                src="https://flagcdn.com/h40/in.png"
                width="100%"
                height="100%"
                alt="Flag of India"
                className="object-fill"
                style={{ aspectRatio: '3/2' }}
              />
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;