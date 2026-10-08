# HTTP adapter (not implemented)

After G-BE, implement `ApiClient` (`src/api/client.ts`) here using the client generated
from the frozen OpenAPI contract, plus a WebSocket `StreamClient` for `/sessions/{id}/stream`.
Swap the provider in `src/app/providers/ApiProvider.tsx`; screens must not change.
Remove `src/api/adapters/mock` (and its server-behaviour simulation) at that point.
