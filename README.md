# new-idea

Minimal Node.js API for capturing ideas during early project exploration.

## Development

```bash
npm install
npm start
npm test
```

The API listens on port 3000:

- `GET /api/health` — health check
- `GET /api/ideas` — list ideas
- `POST /api/ideas` — create an idea (`{"title": "..."}`)
