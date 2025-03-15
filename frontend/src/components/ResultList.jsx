import React, { useState } from 'react';

const ResultList = ({ results, totalCount, query, executionTime }) => {
  const [expandedId, setExpandedId] = useState(null);
  
  // Format authors list
  const formatAuthors = (authors) => {
    if (!authors || authors.length === 0) return 'Unknown Authors';
    if (authors.length === 1) return authors[0];
    if (authors.length === 2) return `${authors[0]} and ${authors[1]}`;
    return `${authors[0]} et al.`;
  };
  
  // Toggle expanded view for a result
  const toggleExpanded = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };
  
  // Format similarity score as percentage
  const formatScore = (score) => {
    return `${Math.round(score * 100)}%`;
  };
  
  // If no results, show message
  if (results.length === 0) {
    return (
      <div className="bg-white shadow-md rounded-lg p-6 text-center">
        <p className="text-gray-600">No results found for "{query}"</p>
        <p className="text-sm text-gray-500 mt-2">Try adjusting your search terms or filters</p>
      </div>
    );
  }
  
  return (
    <div className="bg-white shadow-md rounded-lg p-6">
      <div className="mb-4 text-sm text-gray-600">
        Found {totalCount} {totalCount === 1 ? 'result' : 'results'} for "{query}" 
        ({(executionTime / 1000).toFixed(2)} seconds)
      </div>
      
      <div className="space-y-4">
        {results.map((result) => (
          <div 
            key={result.paper_id}
            className="border rounded-lg overflow-hidden hover:shadow-md transition-shadow"
          >
            <div 
              className="flex items-center justify-between p-4 cursor-pointer"
              onClick={() => toggleExpanded(result.paper_id)}
            >
              <div className="flex-1">
                <h3 className="text-lg font-medium text-gray-900">{result.title}</h3>
                <p className="text-sm text-gray-600 mt-1">
                  {formatAuthors(result.authors)}
                  {result.publication_year && ` • ${result.publication_year}`}
                  {result.conference && ` • ${result.conference}`}
                  {result.journal && ` • ${result.journal}`}
                </p>
              </div>
              <div className="ml-4 flex flex-col items-end">
                <span className="text-blue-600 font-semibold">
                  {formatScore(result.similarity_score)}
                </span>
                <span className="text-sm text-gray-500">match</span>
              </div>
            </div>
            
            {expandedId === result.paper_id && (
              <div className="p-4 border-t bg-gray-50">
                {result.abstract && (
                  <div className="mb-3">
                    <h4 className="text-sm font-semibold text-gray-700 mb-1">Abstract</h4>
                    <p className="text-sm text-gray-600">{result.abstract}</p>
                  </div>
                )}
                
                {result.keywords && result.keywords.length > 0 && (
                  <div className="mb-3">
                    <h4 className="text-sm font-semibold text-gray-700 mb-1">Keywords</h4>
                    <div className="flex flex-wrap gap-1">
                      {result.keywords.map(keyword => (
                        <span 
                          key={keyword} 
                          className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full"
                        >
                          {keyword}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                <div className="flex justify-end mt-3">
                  <a
                    href={`/api/papers/download/${result.paper_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
                  >
                    Download PDF
                  </a>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ResultList;