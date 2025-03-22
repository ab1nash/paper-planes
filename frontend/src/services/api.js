/**
 * API client for communicating with the backend services
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

/**
 * Handles HTTP errors by checking response status and throwing appropriate errors
 * @param {Response} response - Fetch Response object
 * @returns {Promise<any>} - Parsed response data
 * @throws {Error} - Error with message based on the HTTP status
 */
const handleResponse = async (response) => {
  // Parse response body
  let data;
  const contentType = response.headers.get('content-type');
  
  if (contentType && contentType.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }
  
  // Check if response is successful
  if (!response.ok) {
    // Format error message based on response
    const errorMessage = data.detail || data.message || `Error: ${response.status} ${response.statusText}`;
    throw new Error(errorMessage);
  }
  
  return data;
};

/**
 * API client with methods for all backend endpoints
 */
const api = {
  /**
   * Search for papers based on a natural language query
   * @param {Object} searchRequest - Search parameters
   * @param {string} searchRequest.query - The search query
   * @param {Object} [searchRequest.filters] - Optional metadata filters
   * @param {number} [searchRequest.limit=10] - Maximum number of results
   * @param {number} [searchRequest.offset=0] - Pagination offset
   * @returns {Promise<Object>} Search results
   */
  search: async (searchRequest) => {

    const { useParagraphs, ...requestParams } = searchRequest;
    const queryParam = useParagraphs ? '?use_paragraphs=true' : '';

    const response = await fetch(`${API_BASE_URL}/search${queryParam}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(searchRequest),
    });
    
    return handleResponse(response);
  },
  
  /**
   * Get available filter options for search
   * @returns {Promise<Object>} Available filter options
   */
  getFilterOptions: async () => {
    const response = await fetch(`${API_BASE_URL}/search/filter-options`);
    return handleResponse(response);
  },
  
  /**
   * Upload a research paper
   * @param {FormData} formData - Form data containing file and metadata
   * @returns {Promise<Object>} Upload result
   */
  uploadPaper: async (formData) => {
    const response = await fetch(`${API_BASE_URL}/papers/upload`, {
      method: 'POST',
      body: formData,
    });
    
    return handleResponse(response);
  },
  
  /**
   * Get a list of all papers
   * @param {Object} [options] - Optional parameters
   * @param {number} [options.limit=100] - Maximum number of results
   * @param {number} [options.offset=0] - Pagination offset
   * @returns {Promise<Object>} List of papers
   */
  listAllPapers: async (options = {}) => {
    const limit = options.limit || 100;
    const offset = options.offset || 0;

    const response = await fetch(`${API_BASE_URL}/papers?limit=${limit}&offset=${offset}`);
    return handleResponse(response);
  },

  /**
   * Delete a paper
   * @param {string} paperId - ID of the paper to delete
   * @returns {Promise<Object>} Delete result
   */
  deletePaper: async (paperId) => {
    const response = await fetch(`${API_BASE_URL}/papers/${paperId}`, {
      method: 'DELETE',
    });
    
    return handleResponse(response);
  },
  
  /**
   * Get the paper download URL
   * @param {string} paperId - ID of the paper
   * @returns {string} Download URL
   */
  getPaperDownloadUrl: (paperId) => {
    return `${API_BASE_URL}/papers/download/${paperId}`;
  }
};

export default api;