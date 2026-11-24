# LYFTR AI Chatbot

A full-stack AI chatbot built using React, FastAPI, LiteLLM
and SQLite, designed to support conversational AI, automatic
API key failover, response caching and session management.

## Live URLs

- Frontend: Deployment pending
- Backend: Deployment pending
- GitHub Repository: To be updated
- Demo Video: To be updated

## Features

- Interactive and responsive chat interface
- Multiple API key configuration
- Automatic API key failover
- LiteLLM response caching
- Persistent conversation history
- Session-based conversation management
- Custom system prompts
- Per-message token usage tracking
- Response latency monitoring
- Failure simulation
- Docker-based deployment

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | React, Vite, CSS |
| Backend | Python, FastAPI |
| LLM Gateway | LiteLLM |
| AI Model | Google Gemini |
| Database | SQLite |
| Containerization | Docker |
| Web Server | Nginx |

## Run locally

### With Docker

Prerequisites:

- Docker Desktop
- Docker Compose
- Authorized LLM API credentials

Create a `.env` file using `.env.example` as a reference.

Start the application:

```bash
docker compose up --build -d
```

Alternatively:

```bash
make up
```

Access the application:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Health: http://localhost:8000/health

Stop the application:

```bash
docker compose down
```

Alternatively:

```bash
make down
```

### Without Docker

#### Backend

```bash
cd backend
python -m venv venv
```

Windows:

```bash
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

#### Frontend

Open a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend development URL:

http://localhost:5173

## Environment Variables

| Variable | Description |
|----------|-------------|
| LLM_API_KEYS | Comma-separated API key pool |
| LLM_MODEL | LiteLLM model identifier |
| DATABASE_URL | SQLite database location |
| ALLOWED_ORIGINS | Allowed frontend origins |
| ENABLE_FAILURE_SIMULATION | Enables failure testing |
| VITE_API_URL | Backend API URL |

API credentials must remain in environment variables
and must never be committed to GitHub.

## API Endpoints

### GET /health

Returns the application health status, configured
API key count and cache status.

### POST /chat

Processes a user message and returns the assistant
response along with inference metadata.

Example request:

```json
{
  "session_id": "demo-session",
  "message": "What is artificial intelligence?"
}
```

Response metadata includes:

- Resolution source
- Model name
- Latency in milliseconds
- Input tokens
- Output tokens
- API key identifier
- Fallback attempts

### GET /sessions/{session_id}/messages

Retrieves conversation history for a specific session
in chronological order.

## Design decisions

### Key fallback

API credentials are maintained as an ordered key pool.

When a provider request fails, the backend attempts
the next configured key.

If all configured providers fail, the backend returns
HTTP 503 with an appropriate error message.

### Caching

The application uses LiteLLM's built-in local cache.

Caching is based on the model and complete conversation
message context.

Cached responses are identified using LLM_CACHE,
while fresh responses use LIVE_INFERENCE.

The current local cache is process-local and does not
persist across backend restarts.

### SQLite session storage

SQLite stores session information and conversation history.

Only successful user-assistant exchanges are saved.

A named Docker volume mounted at /data preserves
conversation history across container restarts.

## Verification

### Health endpoint

Open:

http://localhost:8000/health

Verify that the application reports two configured
keys and enabled caching.

### Cache hits

1. Start a new chat session.
2. Send a message.
3. Start another new session.
4. Send the exact same message with the same system prompt.
5. Check whether the metadata displays LLM_CACHE.

### Key failover

Enable failure simulation using:

ENABLE_FAILURE_SIMULATION=true

Supported simulation headers:

- X-Simulate-Failure: key_1=429
- X-Simulate-Failure: key_1=429,key_2=500
- X-Simulate-Failure: *=429

When the primary key fails, verify that the secondary
key is attempted.

When all keys fail, verify that HTTP 503 is returned.

### Per-message token usage

Each assistant response displays:

- Input token count
- Output token count
- Response latency
- Model identifier
- Resolution source

### Session persistence

Send messages in a session and retrieve them using
the session history endpoint.

For Docker deployments, restart the containers and
verify that the stored conversation remains available.

## Project Structure

```text
LYFTR-AI-Chatbot/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── llm_service.py
│   ├── requirements.txt
│   ├── test_main.py
│   ├── Dockerfile
│   └── .dockerignore
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   ├── package.json
│   ├── index.html
│   ├── nginx.conf
│   ├── Dockerfile
│   └── .dockerignore
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
└── README.md
```

## Setup Used

- Editor: Visual Studio Code
- Operating System: Windows
- Terminal: PowerShell
- AI Assistance: ChatGPT for development guidance,
  implementation support and documentation

## Bonus features

- Dark-themed responsive interface
- Backend connection status indicator
- Session analytics dashboard
- Custom system prompt configuration
- Failure simulation controls
- Loading indicators
- User-friendly error handling
- New conversation functionality

## Development Status

Core implementation and local health endpoint completed.

Automated tests, live inference verification, cache
verification, failover testing and deployment are pending.

## Author

Developed as part of the LYFTR AI Full Stack Developer
Hiring Assignment.