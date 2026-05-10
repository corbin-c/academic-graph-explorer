# Academic Graph Explorer

A web application for exploring relationships between academic contributions, people, publications, projects, institutions, datasets, and other scholarly entities.

The application uses **RDF and SPARQL as its primary data layer**. Rather than importing the entire dataset into the application, it queries semantic-web data sources dynamically and exposes a small, domain-oriented API for exploring the resulting graph.

The central interaction is **progressive graph exploration**: a user starts from an academic entity and explores its surrounding network of relationships. The application retrieves a bounded neighborhood of the graph, presents it visually, and allows the user to expand the graph by exploring connected entities.

## Architecture

The application consists of two main parts:

- A **React + TypeScript frontend**, responsible for the user interface, interaction, graph state, and visualization.
- A **Python + FastAPI backend**, responsible for querying and transforming semantic data and exposing the application's API.

The frontend uses **D3.js** to render and interact with the graph. D3 operates on an application-level graph model rather than directly on RDF or SPARQL responses.

The backend sits between the frontend and external semantic-data sources:

```text
RDF / Linked Data sources
          │
        SPARQL
          │
          ▼
   Python / FastAPI
          │
   domain transformation
          │
          ▼
      JSON API
          │
          ▼
   React / TypeScript
          │
          ▼
         D3.js
```

The backend is deliberately thin. It does not attempt to become a general-purpose data platform; its role is to provide a stable application-level interface over potentially heterogeneous semantic data sources.

## API

The API is organized around three primary operations:

- **Entities** — retrieve information about a specific scholarly entity.
- **Search** — find entities matching a user's query.
- **Graph** — traverse and retrieve the relationships surrounding an entity.

For example:

```text
GET /api/entities/{id}
GET /api/search?q=...
GET /api/graph/{id}?depth=2
```

The graph endpoint represents a specific graph operation: starting from a root entity and retrieving a bounded neighborhood of connected entities and relationships.

The API exposes typed responses using **Pydantic models**, with the resulting OpenAPI schema used to generate corresponding TypeScript types/client code for the frontend. This keeps the Python backend and TypeScript frontend synchronized without duplicating type definitions manually.

## Backend organization

The Python application is separated into three conceptual layers:

```text
api/
    HTTP interface

domain/
    application-level entities and graph models

sparql/
    communication with RDF/SPARQL sources
```

The `api` layer handles HTTP concerns.

The `domain` layer defines the concepts the application works with independently of the underlying data source.

The `sparql` layer handles SPARQL queries and communication with external RDF endpoints.

This separation means that the frontend does not need to understand RDF, and the rest of the backend does not need to depend directly on FastAPI or a particular SPARQL provider.

## Data flow

A typical graph exploration looks like this:

```text
User selects an entity
        │
        ▼
Frontend requests its graph neighborhood
        │
        ▼
FastAPI graph endpoint
        │
        ▼
SPARQL query
        │
        ▼
RDF endpoint
        │
        ▼
SPARQL results
        │
        ▼
Python domain transformation
        │
        ▼
Typed JSON response
        │
        ▼
Frontend graph state
        │
        ▼
D3 visualization
```

The backend can cache expensive or frequently requested queries, reducing dependence on the availability and performance of external SPARQL endpoints.

## Deployment

The project is maintained as a **single repository** containing the frontend and backend:

```text
academic-graph/
├── frontend/
├── backend/
├── Dockerfile
├── docker-compose.yml
└── README.md
```

For production, the React application can be built into static assets and served alongside the FastAPI application from a single Docker container.

The application can therefore be deployed on a small VPS with minimal infrastructure:

```text
                    Internet
                       │
                       ▼
                Reverse proxy
                       │
                       ▼
              Docker container
              ┌────────────────┐
              │ FastAPI        │
              │ React          │
              │ SQLite cache   │
              └───────┬────────┘
                      │
                      ▼
                SPARQL endpoint
```

The architecture deliberately avoids unnecessary infrastructure. The interesting engineering work is in **semantic data integration, graph traversal, domain modelling, API design, and interactive visualization**, rather than in operating a large distributed system.

## Purpose

The project serves both as a usable exploration tool and as a technical portfolio project demonstrating experience with:

- Python and FastAPI
- TypeScript and React
- D3.js and interactive visualization
- RDF and Linked Data
- SPARQL
- semantic data modelling
- graph traversal and exploration
- API design
- data transformation and integration
- containerized deployment

The project is intended to sit at the intersection of **software engineering, research infrastructure, digital humanities, and interactive data visualization**.

## Development & Deployment

### First setup

```bash
cd backend
uv sync

cd ../frontend
npm install
```

### Development

```bash
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm run dev
```

Open:

```text
http://localhost:5173
```

### Production

```bash
git pull
docker compose up -d --build
```
