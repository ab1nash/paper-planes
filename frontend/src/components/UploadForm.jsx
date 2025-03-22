import React, { useState } from 'react';

const UploadForm = ({ onUpload, isUploading }) => {
  const [file, setFile] = useState(null);
  const [extractMetadata, setExtractMetadata] = useState(true);
  const [useCustomMetadata, setUseCustomMetadata] = useState(false);
  const [useParagraphProcessing, setUseParagraphProcessing] = useState(true);
  const [customMetadata, setCustomMetadata] = useState({
    title: '',
    authors: [],
    abstract: '',
    publication_year: '',
    doi: '',
    keywords: [],
    conference: '',
    journal: ''
  });
  
  // Handle file selection
  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
    } else {
      setFile(null);
      alert('Please select a PDF file.');
    }
  };
  
  // Handle form submission
  const handleSubmit = (event) => {
    event.preventDefault();
    
    if (!file) {
      alert('Please select a PDF file to upload.');
      return;
    }
    
    // Prepare form data
    const formData = new FormData();
    formData.append('file', file);
    formData.append('extract_metadata', extractMetadata);
    
    // Add custom metadata if enabled
    if (useCustomMetadata) {
      // Clean the metadata before sending
      const cleanedMetadata = {
        ...customMetadata,
        publication_year: customMetadata.publication_year ? 
          parseInt(customMetadata.publication_year) : null
      };
      
      formData.append('custom_metadata', JSON.stringify(cleanedMetadata));
    }
    
    // Call the upload function from props with paragraph flag
    onUpload(formData, useParagraphProcessing);
  };
  
  // Handle custom metadata changes
  const handleMetadataChange = (field, value) => {
    setCustomMetadata(prev => ({
      ...prev,
      [field]: value
    }));
  };
  
  // Handle author input
  const handleAuthorChange = (index, value) => {
    const updatedAuthors = [...customMetadata.authors];
    updatedAuthors[index] = value;
    handleMetadataChange('authors', updatedAuthors);
  };
  
  // Add a new author input field
  const addAuthorField = () => {
    handleMetadataChange('authors', [...customMetadata.authors, '']);
  };
  
  // Remove an author field
  const removeAuthorField = (index) => {
    const updatedAuthors = customMetadata.authors.filter((_, i) => i !== index);
    handleMetadataChange('authors', updatedAuthors);
  };
  
  // Handle keyword input 
  const handleKeywordChange = (index, value) => {
    const updatedKeywords = [...customMetadata.keywords];
    updatedKeywords[index] = value;
    handleMetadataChange('keywords', updatedKeywords);
  };
  
  // Add a new keyword input field
  const addKeywordField = () => {
    handleMetadataChange('keywords', [...customMetadata.keywords, '']);
  };
  
  // Remove a keyword field
  const removeKeywordField = (index) => {
    const updatedKeywords = customMetadata.keywords.filter((_, i) => i !== index);
    handleMetadataChange('keywords', updatedKeywords);
  };
  
  return (
    <div className="bg-white shadow-md rounded-lg p-6">
      <h2 className="text-lg font-medium mb-4">Upload Research Paper</h2>
      
      <form onSubmit={handleSubmit}>
        {/* File Input */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            PDF File
          </label>
          <input
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-500
                      file:mr-4 file:py-2 file:px-4
                      file:rounded-md file:border-0
                      file:text-sm file:font-medium
                      file:bg-blue-50 file:text-blue-700
                      hover:file:bg-blue-100"
            required
          />
          {file && (
            <p className="mt-1 text-sm text-gray-500">
              Selected file: {file.name}
            </p>
          )}
        </div>
        
        {/* Metadata Options */}
        <div className="mb-4">
          <div className="flex items-center mb-2">
            <input
              type="checkbox"
              id="extract-metadata"
              checked={extractMetadata}
              onChange={(e) => setExtractMetadata(e.target.checked)}
              className="h-4 w-4 text-blue-600 rounded"
            />
            <label htmlFor="extract-metadata" className="ml-2 text-sm text-gray-700">
              Extract metadata from PDF
            </label>
          </div>
          
          <div className="flex items-center">
            <input
              type="checkbox"
              id="use-custom-metadata"
              checked={useCustomMetadata}
              onChange={(e) => setUseCustomMetadata(e.target.checked)}
              className="h-4 w-4 text-blue-600 rounded"
            />
            <label htmlFor="use-custom-metadata" className="ml-2 text-sm text-gray-700">
              Provide custom metadata
            </label>
          </div>
        </div>
        
        {/* Custom Metadata Form */}
        {useCustomMetadata && (
          <div className="border-t pt-4 space-y-4 mb-4">
            <h3 className="text-sm font-medium text-gray-700">Custom Metadata</h3>
            
            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Title
              </label>
              <input
                type="text"
                value={customMetadata.title}
                onChange={(e) => handleMetadataChange('title', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
            
            {/* Authors */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Authors
              </label>
              {customMetadata.authors.map((author, index) => (
                <div key={index} className="flex mb-2">
                  <input
                    type="text"
                    value={author}
                    onChange={(e) => handleAuthorChange(index, e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-l-md text-sm"
                    placeholder="Author name"
                  />
                  <button
                    type="button"
                    onClick={() => removeAuthorField(index)}
                    className="px-3 py-2 bg-red-100 text-red-700 rounded-r-md hover:bg-red-200"
                  >
                    Remove
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={addAuthorField}
                className="px-3 py-1 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200"
              >
                Add Author
              </button>
            </div>
            
            {/* Abstract */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Abstract
              </label>
              <textarea
                value={customMetadata.abstract || ''}
                onChange={(e) => handleMetadataChange('abstract', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                rows="4"
              />
            </div>
            
            {/* Publication Year */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Publication Year
              </label>
              <input
                type="number"
                value={customMetadata.publication_year || ''}
                onChange={(e) => handleMetadataChange('publication_year', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                min="1900"
                max="2030"
              />
            </div>
            
            {/* DOI */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                DOI
              </label>
              <input
                type="text"
                value={customMetadata.doi || ''}
                onChange={(e) => handleMetadataChange('doi', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                placeholder="10.xxxx/xxxxx"
              />
            </div>
            
            {/* Keywords */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Keywords
              </label>
              {customMetadata.keywords.map((keyword, index) => (
                <div key={index} className="flex mb-2">
                  <input
                    type="text"
                    value={keyword}
                    onChange={(e) => handleKeywordChange(index, e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-l-md text-sm"
                    placeholder="Keyword"
                  />
                  <button
                    type="button"
                    onClick={() => removeKeywordField(index)}
                    className="px-3 py-2 bg-red-100 text-red-700 rounded-r-md hover:bg-red-200"
                  >
                    Remove
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={addKeywordField}
                className="px-3 py-1 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200"
              >
                Add Keyword
              </button>
            </div>
            
            {/* Conference */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Conference
              </label>
              <input
                type="text"
                value={customMetadata.conference || ''}
                onChange={(e) => handleMetadataChange('conference', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
            
            {/* Journal */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Journal
              </label>
              <input
                type="text"
                value={customMetadata.journal || ''}
                onChange={(e) => handleMetadataChange('journal', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
          </div>
        )}
        
        {/* Paragraph Processing Toggle */}
        <div className="mb-4">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="use-paragraphs"
              checked={useParagraphProcessing}
              onChange={(e) => setUseParagraphProcessing(e.target.checked)}
              className="h-4 w-4 text-blue-600 rounded"
            />
            <label htmlFor="use-paragraphs" className="ml-2 text-sm text-gray-700">
              Process at paragraph level for more precise search
            </label>
            <div className="ml-2">
              <span className="inline-block rounded-full w-4 h-4 bg-gray-200 text-gray-600 text-xs font-bold text-center cursor-help" title="Processing at paragraph level breaks the paper into sections and paragraphs, enabling more precise search results.">?</span>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="mt-6">
          <button
            type="submit"
            disabled={isUploading || !file}
            className={`w-full px-4 py-2 rounded-md text-white font-medium 
                      ${(isUploading || !file) 
                        ? 'bg-blue-400 cursor-not-allowed' 
                        : 'bg-blue-600 hover:bg-blue-700'}`}
          >
            {isUploading ? 'Uploading...' : 'Upload Paper'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default UploadForm;