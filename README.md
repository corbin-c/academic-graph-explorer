## Development

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
