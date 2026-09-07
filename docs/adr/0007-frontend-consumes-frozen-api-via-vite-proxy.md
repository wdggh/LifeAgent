# Frontend V1 consumes the frozen backend through a Vite dev proxy; no CORS is added in V1

Status: accepted

The backend MVP API is accepted and frozen, so Frontend V1 must not change it. During development the browser only talks to the Vite dev server (5173), which proxies `/api/v1` unchanged to FastAPI on host port 8080, so no cross-origin request ever happens and the backend does not need CORS middleware for the dev loop. Deployment topology (same-origin Nginx routing of `/api/`, or a direct API origin plus CORS) is deliberately deferred until real deployment; with a relative `VITE_API_BASE_URL=/api/v1` the frontend code stays compatible with the same-origin option.
