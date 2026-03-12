# Agent Instructions

## Project Overview
AG_CoverMaestro is a full-stack application with a FastAPI backend and a React (Vite/TypeScript) frontend.

## Commands

### Lint
- Backend: `flake8 app`
- Frontend: `cd client && npm run lint`

### Test
- Backend: `pytest`
- Frontend: `cd client && npm run test`

### Build
- Frontend: `cd client && npm run build`

## Environment Setup
The backend requires several environment variables for Supabase and Database connections. These should be configured in the Codex Cloud environment settings.
The frontend is located in the `client/` directory and uses `npm`.
