import React, { useState } from 'react';

const ResultList = ({ results, totalCount, query, executionTime, useParagraphs = false }) => {
  const [expandedId, setExpandedId] = useState(null);
  const [expandedParagraphs, setExpandedParagraphs] = useState({});
  
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
  
  // Toggle showing all paragraphs for a paper
  const toggleParagraphs = (paperId) => {
    setExpandedParagraphs({
      ...expandedParagraphs,
      [paperId]: !expandedParagraphs[paperId]
    });
  };

  // Format similarity score as percentage
  const formatScore = (score) => {
    return `${Math.round(score * 100)}%`;
  };
  
  // Highlight query terms in text
  const highlightText = (text, query) => {
    if (!query || !text) return text;

    // Create a regex to match all query terms
    const queryTerms = query.split(/\s+/).filter(term => term.length > 2);
    if (queryTerms.length === 0) return text;

    const regex = new RegExp(`(${queryTerms.join('|')})`, 'gi');

    // Split by matches and map to spans with highlighting
    const parts = text.split(regex);

    return parts.map((part, i) => {
      // Check if this part matches any query term (case insensitive)
      const isMatch = queryTerms.some(term =>
        part.toLowerCase() === term.toLowerCase()
      );

      return isMatch ?
        <span key={i} className="bg-yellow-200">{part}</span> :
        <span key={i}>{part}</span>;
    });
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
                {/* Paper Abstract */}
                {result.abstract && (
                  <div className="mb-3">
                    <h4 className="text-sm font-semibold text-gray-700 mb-1">Abstract</h4>
                    <p className="text-sm text-gray-600">
                      {useParagraphs
                        ? highlightText(result.abstract, query)
                        : result.abstract}
                    </p>
                  </div>
                )}
                
                {/* Keyword Tags */}
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
                
                {/* Matching Paragraphs - Only shown for paragraph search */}
                {useParagraphs && result.matching_paragraphs && result.matching_paragraphs.length > 0 && (
                  <div className="mb-3">
                    <h4 className="text-sm font-semibold text-gray-700 mb-1">
                      Matching Paragraphs
                    </h4>
                    <div className="space-y-3 mt-2">
                      {/* Show first paragraphs or all based on expanded state */}
                      {(expandedParagraphs[result.paper_id]
                        ? result.matching_paragraphs
                        : result.matching_paragraphs.slice(0, 2)
                      ).map((paragraph, idx) => (
                        <div key={idx} className="bg-white p-3 border border-blue-100 rounded-md">
                          <div className="flex justify-between items-start mb-1">
                            <span className="text-xs text-blue-600 font-medium">
                              {paragraph.section || 'Section'} - Paragraph {paragraph.paragraph_index + 1}
                            </span>
                            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
                              {formatScore(paragraph.score)}
                            </span>
                          </div>
                          <p className="text-sm text-gray-700">
                            {highlightText(paragraph.text, query)}
                          </p>
                        </div>
                      ))}

                      {/* Show/Hide More button */}
                      {result.matching_paragraphs.length > 2 && (
                        <button
                          className="text-sm text-blue-600 mt-1 hover:underline flex items-center"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleParagraphs(result.paper_id);
                          }}
                        >
                          {expandedParagraphs[result.paper_id] ? (
                            <>
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                              </svg>
                              Show fewer paragraphs
                            </>
                          ) : (
                            <>
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                              Show {result.matching_paragraphs.length - 2} more matching paragraphs
                            </>
                          )}
                        </button>
                      )}
                    </div>
                  </div>
                )}

                {/* Paragraph Context - Only shown when viewing a specific paragraph */}
                {useParagraphs && expandedParagraphs[result.paper_id] && result.matching_paragraphs &&
                  result.matching_paragraphs.some(p => p.context && p.context !== p.text) && (
                    <div className="mb-3">
                      <div className="flex items-center mb-1">
                        <h4 className="text-sm font-semibold text-gray-700">Paragraph Context</h4>
                        <span className="ml-2 text-xs text-gray-500">(Surrounding paragraphs for better understanding)</span>
                      </div>
                      <div className="bg-gray-100 p-3 rounded-md text-sm text-gray-700 whitespace-pre-wrap">
                        {result.matching_paragraphs[0].context}
                      </div>
                    </div>
                  )}

                {/* Download Button */}
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