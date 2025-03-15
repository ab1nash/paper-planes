# Research Paper Search System

An offline semantic search system for research papers that works on a local area network without requiring internet connectivity.

## Overview

This system enables users to:

1. **Upload and index research papers**: Upload PDF research papers and automatically extract metadata and semantic embeddings.
2. **Search semantically**: Find relevant papers based on natural language queries, not just keywords.
3. **Run completely offline**: All processing happens locally with no internet requirement.

## Architecture

The system consists of two main components:

### 1. Backend (Python/FastAPI)
- PDF text extraction
- Metadata extraction (titles, authors, abstracts, etc.)
- Embedding generation using local LLM
- Vector database for semantic search
- Metadata database for filtering

### 2. Frontend (React)
- Paper search interface with filters
- Paper upload/ingestion UI
- Results display with relevance scores

## Technical Stack

### Backend
- **FastAPI**: Web framework for APIs
- **PyPDF2**: PDF text extraction
- **SentenceTransformers**: Lightweight embedding model
- **FAISS**: Vector search engine
- **SQLite**: Metadata storage
- **Uvicorn**: ASGI server

### Frontend
- **React**: UI framework
- **TailwindCSS**: Styling
- **Vite**: Build tool
- **Nginx**: Static file serving and proxying

### Deployment
- **Docker**: Containerization
- **Docker Compose**: Service orchestration

## Getting Started

### Prerequisites
- Docker and Docker Compose
- 8GB+ RAM (recommended for running the LLM)
- 10GB+ storage space

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/ab1nash/paper-planes.git
   cd paper-planes
   ```

2. Start the system using Docker Compose:
   ```
   sudo docker-compose up -d
   ```

3. Access the application:
   - Web interface: http://localhost:3000
   - API: http://localhost:8000/api/docs

### First-time Setup

When first running the system, it will:

1. Download the lightweight LLM model (requires temporary internet connection or pre-downloaded model)
2. Initialize the vector and metadata databases
3. Create necessary storage directories

## Usage Guide

### Uploading Papers

1. Navigate to the "Upload Papers" tab
2. Select a PDF file and click "Upload"
3. The system will extract:
   - Text content
   - Metadata (title, authors, year, etc.)
   - Semantic embeddings
4. Optionally provide custom metadata if extraction fails

### Searching Papers

1. Navigate to the "Search Papers" tab
2. Enter a natural language query
3. Optionally add filters:
   - Publication year range
   - Authors
   - Keywords
   - Conference/Journal
4. View results sorted by relevance
5. Expand papers to see abstracts and other details
6. Download papers as needed

## Directory Structure

```
paper-planes/
├── backend/               # Python FastAPI application
│   ├── app/               # Application code
│   ├── models/            # LLM models directory
│   └── storage/           # Paper storage and databases
├── frontend/              # React application
│   ├── public/            # Static assets
│   └── src/               # React components and services
├── docker/                # Docker configuration
└── README.md              # This documentation
```

## Configuration

The system can be configured through environment variables:

### Backend Configuration
- `DEBUG`: Enable debug mode (default: false)
- `UPLOAD_DIR`: Directory for storing papers
- `LLM_MODEL_NAME`: Name of the embedding model
- `SIMILARITY_THRESHOLD`: Minimum similarity score for results

### Frontend Configuration
- `VITE_API_BASE_URL`: API endpoint URL

## Offline Use

To use the system completely offline:

1. Ensure the LLM model is downloaded during initial setup
2. Configure your local network to allow connections to the server
3. Connect devices to the same local network
4. Access the system via the server's local IP address

## Development Setup

For development:

1. Set up the backend:
   ```
   cd backend
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

2. Set up the frontend:
   ```
   cd frontend
   npm install
   npm run dev
   ```

## Extending the System

### Adding a New Filter Type
1. Add the filter field to the `SearchFilter` model in `backend/app/core/models.py`
2. Update the `_apply_filters` method in `SearchService`
3. Add the UI component in `frontend/src/components/SearchForm.jsx`

### Using a Different LLM Model
1. Update the `LLM_MODEL_NAME` in configuration
2. Ensure the model is compatible with SentenceTransformers
3. Update the `EMBEDDING_DIMENSION` to match the new model

## License

This project is licensed under the GPLv3 License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.