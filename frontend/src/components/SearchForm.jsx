import React, { useState } from 'react';

const SearchForm = ({ onSearch, isLoading }) => {
  const [query, setQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    year_min: '',
    year_max: '',
    authors: [],
    keywords: [],
    conference: '',
    journal: ''
  });
  
  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch({
        query,
        filters: {
          year_min: filters.year_min ? parseInt(filters.year_min) : null,
          year_max: filters.year_max ? parseInt(filters.year_max) : null,
          authors: filters.authors.length > 0 ? filters.authors : null,
          keywords: filters.keywords.length > 0 ? filters.keywords : null,
          conference: filters.conference || null,
          journal: filters.journal || null
        }
      });
    }
  };
  
  // Handle filter changes
  const handleFilterChange = (name, value) => {
    setFilters(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  // Add an author filter
  const addAuthorFilter = (author) => {
    if (author && !filters.authors.includes(author)) {
      setFilters(prev => ({
        ...prev,
        authors: [...prev.authors, author]
      }));
    }
  };
  
  // Remove an author filter
  const removeAuthorFilter = (author) => {
    setFilters(prev => ({
      ...prev,
      authors: prev.authors.filter(a => a !== author)
    }));
  };
  
  // Add a keyword filter
  const addKeywordFilter = (keyword) => {
    if (keyword && !filters.keywords.includes(keyword)) {
      setFilters(prev => ({
        ...prev,
        keywords: [...prev.keywords, keyword]
      }));
    }
  };
  
  // Remove a keyword filter
  const removeKeywordFilter = (keyword) => {
    setFilters(prev => ({
      ...prev,
      keywords: prev.keywords.filter(k => k !== keyword)
    }));
  };
  
  // Reset all filters
  const resetFilters = () => {
    setFilters({
      year_min: '',
      year_max: '',
      authors: [],
      keywords: [],
      conference: '',
      journal: ''
    });
  };
  
  return (
    <div className="bg-white shadow-md rounded-lg p-6 mb-6">
      <form onSubmit={handleSubmit}>
        <div className="flex items-center">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for research papers..."
            className="flex-1 px-4 py-2 bg-white text-black border border-gray-300 rounded-l-md"
            required
          />
          <button
            type="submit"
            disabled={isLoading}
            className="px-4 py-2 rounded-r-md bg-gray-600 text-white"
          >
            {isLoading ? 'Searching...' : 'Search'}
          </button>
        </div>
        
        <div className="mt-4 flex justify-between items-center">
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className="text-gray-600 text-sm font-medium flex items-center"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
            </svg>
            {showFilters ? 'Hide Filters' : 'Show Filters'}
          </button>
          
          {showFilters && (
            <button
              type="button"
              onClick={resetFilters}
              className="text-gray-600 text-sm font-medium"
            >
              Reset Filters
            </button>
          )}
        </div>
        
        {showFilters && (
          <div className="mt-4 border-t pt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Year Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Publication Year
              </label>
              <div className="flex space-x-2">
                <input
                  type="number"
                  placeholder="From"
                  value={filters.year_min}
                  onChange={(e) => handleFilterChange('year_min', e.target.value)}
                  className="w-1/2 px-3 py-2 bg-white text-black border border-gray-300 rounded-md text-sm"
                  min="1900"
                  max="2030"
                />
                <input
                  type="number"
                  placeholder="To"
                  value={filters.year_max}
                  onChange={(e) => handleFilterChange('year_max', e.target.value)}
                  className="w-1/2 px-3 py-2 bg-white text-black border border-gray-300 rounded-md text-sm"
                  min="1900"
                  max="2030"
                />
              </div>
            </div>
            
            {/* Conference/Journal */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Conference/Journal
              </label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  placeholder="Conference"
                  value={filters.conference}
                  onChange={(e) => handleFilterChange('conference', e.target.value)}
                  className="w-1/2 px-3 py-2 bg-white text-black border border-gray-300 rounded-md text-sm"
                />
                <input
                  type="text"
                  placeholder="Journal"
                  value={filters.journal}
                  onChange={(e) => handleFilterChange('journal', e.target.value)}
                  className="w-1/2 px-3 py-2 bg-white text-black border border-gray-300 rounded-md text-sm"
                />
              </div>
            </div>
            
            {/* Authors */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Authors
              </label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  placeholder="Add author name"
                  id="author-input"
                  className="flex-1 px-3 py-2 bg-white text-black border border-gray-300 rounded-l-md text-sm"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      addAuthorFilter(e.target.value);
                      e.target.value = '';
                    }
                  }}
                />
                <button
                  type="button"
                  onClick={() => {
                    const input = document.getElementById('author-input');
                    addAuthorFilter(input.value);
                    input.value = '';
                  }}
                  className="px-3 py-2 bg-gray-200 text-gray-800 rounded-r-md"
                >
                  Add
                </button>
              </div>
              {filters.authors.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {filters.authors.map(author => (
                    <span
                      key={author}
                      className="inline-flex items-center bg-blue-100 text-blue-800 text-xs font-medium px-2 py-1 rounded-full"
                    >
                      {author}
                      <button
                        type="button"
                        onClick={() => removeAuthorFilter(author)}
                        className="ml-1 text-blue-500"
                      >
                        &times;
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
            
            {/* Keywords */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Keywords
              </label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  placeholder="Add keyword"
                  id="keyword-input"
                  className="flex-1 px-3 py-2 bg-white text-black border border-gray-300 rounded-l-md text-sm"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      addKeywordFilter(e.target.value);
                      e.target.value = '';
                    }
                  }}
                />
                <button
                  type="button"
                  onClick={() => {
                    const input = document.getElementById('keyword-input');
                    addKeywordFilter(input.value);
                    input.value = '';
                  }}
                  className="px-3 py-2 bg-gray-200 text-gray-800 rounded-r-md"
                >
                  Add
                </button>
              </div>
              {filters.keywords.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {filters.keywords.map(keyword => (
                    <span
                      key={keyword}
                      className="inline-flex items-center bg-green-100 text-green-800 text-xs font-medium px-2 py-1 rounded-full"
                    >
                      {keyword}
                      <button
                        type="button"
                        onClick={() => removeKeywordFilter(keyword)}
                        className="ml-1 text-green-500"
                      >
                        &times;
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </form>
    </div>
  );
};

export default SearchForm;