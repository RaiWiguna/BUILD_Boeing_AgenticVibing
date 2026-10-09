"""Public HTTPX transport guard around SDK retries and response allocation.

The pinned SDK mutates HttpRetryOptions(attempts=0) to 1 before its Interactions
bridge translates that value to retry count. One application reservation must
never permit a second network send, regardless of upstream retry behavior.
"""

from collections.abc import AsyncIterator
from contextvars import ContextVar
from dataclasses import dataclass

import httpx
from flowlens.providers.gemini.models import GeminiFailure


@dataclass
class SendState:
    sends: int = 0
    status: int | None = None


class LimitedStream(httpx.AsyncByteStream):
    def __init__(self, stream: httpx.AsyncByteStream, limit: int) -> None:
        self.stream, self.limit = stream, limit

    async def __aiter__(self) -> AsyncIterator[bytes]:
        size = 0
        async for block in self.stream:
            size += len(block)
            if size > self.limit:
                raise GeminiFailure("OUTPUT_LIMIT")
            yield block

    async def aclose(self) -> None:
        await self.stream.aclose()


class SingleSendTransport(httpx.AsyncBaseTransport):
    def __init__(self, delegate: httpx.AsyncBaseTransport, limit: int) -> None:
        self.delegate, self.limit = delegate, limit
        self.state: ContextVar[SendState] = ContextVar("gemini_send_state")

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        state = self.state.get(None)
        if state is None or state.sends:
            raise GeminiFailure("SDK_RETRY_BLOCKED")
        if request.url.host != "generativelanguage.googleapis.com" or request.url.scheme != "https":
            raise GeminiFailure("ENDPOINT_INVALID")
        request.headers["accept-encoding"] = "identity"
        state.sends += 1
        response = await self.delegate.handle_async_request(request)
        state.status = response.status_code
        if response.headers.get("content-encoding", "identity") != "identity":
            await response.aclose()
            raise GeminiFailure("UNSUPPORTED_ENCODING")
        if response.is_stream_consumed and len(response.content) > self.limit:
            await response.aclose()
            raise GeminiFailure("OUTPUT_LIMIT")
        if isinstance(response.stream, httpx.AsyncByteStream):
            response.stream = LimitedStream(response.stream, self.limit)
        return response

    async def aclose(self) -> None:
        await self.delegate.aclose()
