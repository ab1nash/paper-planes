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
  const [useParagraphs, setUseParagraphs] = useState(false);
  
  /**
   * Handle search submission
   * @param {Object} searchRequest - Search parameters
   */
  const handleSearch = async (searchRequest) => {
    try {
      setIsSearching(true);
      setSearchResults(null);
      
      // Store paragraph search mode for display
      setUseParagraphs(searchRequest.useParagraphs);

      // Send search request to API with paragraph flag
      const results = await api.search({
        query: searchRequest.query,
        filters: searchRequest.filters,
        useParagraphs: searchRequest.useParagraphs
      });

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
   * @param {boolean} useParagraphs - Whether to process at paragraph level
   */
  const handleUpload = async (formData, useParagraphProcessing) => {
    try {
      setIsUploading(true);
      
      // Add paragraph flag to form data
      formData.append('use_paragraphs', useParagraphProcessing);

      const result = await api.uploadPaper(formData);
      
      const paragraphMsg = useParagraphProcessing ?
        ` with ${result.message || 'paragraph-level processing'}` : '';

      showNotification('success', `Paper "${result.metadata.title}" uploaded successfully${paragraphMsg}`);
      
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
              <>
                {/* Search mode indicator */}
                {useParagraphs && (
                  <div className="mb-4 px-4 py-2 bg-blue-50 text-blue-700 rounded-md flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    <span>
                      Results are using paragraph-level search, showing the most relevant passages from each paper.
                    </span>
                  </div>
                )}

                <ResultList
                  results={searchResults.results}
                  totalCount={searchResults.total_count}
                  query={searchResults.query}
                  executionTime={searchResults.execution_time_ms}
                  useParagraphs={useParagraphs}
                />
              </>
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