"""
Streaming RAG implementation for real-time responses.
Provides token-by-token streaming for better UX.
"""

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import dataclass
import json
import logging
import time
from typing import Any, Optional

from llama_index.core import Response
from llama_index.core.callbacks import TokenCountingHandler
from llama_index.core.llms import ChatMessage
from llama_index.core.query_engine import BaseQueryEngine
from llama_index.llms.openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class StreamingChunk:
    """Represents a single chunk in the streaming response"""
    token: str
    metadata: Optional[dict[str, Any]] = None
    timestamp: float = None
    is_final: bool = False

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "is_final": self.is_final
        }


class StreamingRAGEngine:
    """
    Enhanced RAG engine with streaming capabilities.
    Streams responses token-by-token for real-time UX.
    """

    def __init__(
        self,
        query_engine: BaseQueryEngine,
        llm: Optional[OpenAI] = None,
        chunk_size: int = 10,
        stream_delay: float = 0.01
    ):
        """
        Initialize streaming RAG engine.

        Args:
            query_engine: Base query engine for retrieval
            llm: Language model for generation
            chunk_size: Number of tokens to buffer before streaming
            stream_delay: Delay between chunks for smooth streaming
        """
        self.query_engine = query_engine
        self.llm = llm or OpenAI(model="gpt-3.5-turbo", streaming=True)
        self.chunk_size = chunk_size
        self.stream_delay = stream_delay
        self.token_counter = TokenCountingHandler()

    async def stream_query(
        self,
        query: str,
        **kwargs
    ) -> AsyncGenerator[StreamingChunk, None]:
        """
        Stream query response token by token.

        Args:
            query: User query
            **kwargs: Additional arguments for query engine

        Yields:
            StreamingChunk objects containing tokens and metadata
        """
        try:
            # First, get context from RAG
            logger.info(f"Streaming query: {query[:100]}...")

            # Yield initial status
            yield StreamingChunk(
                token="",
                metadata={"status": "retrieving", "message": "Searching documents..."}
            )

            # Get retrieved context
            retrieval_start = time.time()
            response = await self._async_query(query, **kwargs)
            retrieval_time = time.time() - retrieval_start

            # Extract source nodes for context
            source_nodes = []
            if hasattr(response, 'source_nodes'):
                source_nodes = [
                    {
                        "text": node.node.text[:200] + "...",
                        "score": node.score,
                        "metadata": node.node.metadata
                    }
                    for node in response.source_nodes[:3]
                ]

            # Yield retrieval complete status
            yield StreamingChunk(
                token="",
                metadata={
                    "status": "generating",
                    "message": "Generating response...",
                    "retrieval_time": retrieval_time,
                    "sources": source_nodes
                }
            )

            # Stream the response
            if hasattr(response, 'response_gen'):
                # Response is already a generator
                buffer = []
                async for token in response.response_gen:
                    buffer.append(token)

                    # Stream when buffer is full
                    if len(buffer) >= self.chunk_size:
                        chunk_text = "".join(buffer)
                        yield StreamingChunk(token=chunk_text)
                        buffer = []
                        await asyncio.sleep(self.stream_delay)

                # Yield remaining buffer
                if buffer:
                    yield StreamingChunk(token="".join(buffer))

            else:
                # Response is complete, stream it word by word
                response_text = str(response)
                words = response_text.split()

                for i in range(0, len(words), self.chunk_size):
                    chunk = " ".join(words[i:i+self.chunk_size])
                    if i + self.chunk_size < len(words):
                        chunk += " "
                    yield StreamingChunk(token=chunk)
                    await asyncio.sleep(self.stream_delay)

            # Final chunk with metadata
            yield StreamingChunk(
                token="",
                metadata={
                    "status": "complete",
                    "total_tokens": self.token_counter.total_llm_token_count,
                    "sources_count": len(source_nodes)
                },
                is_final=True
            )

        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            yield StreamingChunk(
                token="",
                metadata={"status": "error", "error": str(e)},
                is_final=True
            )

    async def _async_query(self, query: str, **kwargs) -> Response:
        """
        Execute query asynchronously.

        Args:
            query: User query
            **kwargs: Additional arguments

        Returns:
            Query response
        """
        # If query engine has async support
        if hasattr(self.query_engine, 'aquery'):
            return await self.query_engine.aquery(query, **kwargs)
        else:
            # Fall back to sync in thread pool
            import concurrent.futures
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return await loop.run_in_executor(
                    pool,
                    self.query_engine.query,
                    query
                )

    async def stream_with_sources(
        self,
        query: str,
        include_sources: bool = True,
        max_sources: int = 3,
        **kwargs
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream response with source documents.

        Args:
            query: User query
            include_sources: Whether to include source documents
            max_sources: Maximum number of sources to include
            **kwargs: Additional arguments

        Yields:
            Dictionary with response chunks and metadata
        """
        async for chunk in self.stream_query(query, **kwargs):
            result = chunk.to_dict()

            # Add sources on first content chunk
            if include_sources and chunk.metadata and chunk.metadata.get('sources'):
                result['sources'] = chunk.metadata['sources'][:max_sources]

            yield result

    def create_sse_stream(
        self,
        query: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Create Server-Sent Events (SSE) stream for web APIs.

        Args:
            query: User query
            **kwargs: Additional arguments

        Yields:
            SSE formatted strings
        """
        async def generate():
            async for chunk in self.stream_query(query, **kwargs):
                # Format as SSE
                data = json.dumps(chunk.to_dict())
                yield f"data: {data}\n\n"

                if chunk.is_final:
                    yield "event: close\ndata: {}\n\n"

        return generate()


class StreamingChatInterface:
    """
    Chat interface with streaming support for interactive conversations.
    """

    def __init__(self, streaming_engine: StreamingRAGEngine):
        """
        Initialize chat interface.

        Args:
            streaming_engine: Streaming RAG engine
        """
        self.engine = streaming_engine
        self.conversation_history: list[ChatMessage] = []

    async def chat_stream(
        self,
        message: str,
        include_history: bool = True,
        **kwargs
    ) -> AsyncGenerator[StreamingChunk, None]:
        """
        Stream chat response with conversation history.

        Args:
            message: User message
            include_history: Whether to include conversation history
            **kwargs: Additional arguments

        Yields:
            Streaming chunks
        """
        # Add user message to history
        self.conversation_history.append(
            ChatMessage(role="user", content=message)
        )

        # Build context with history
        if include_history and len(self.conversation_history) > 1:
            context = self._build_context()
            query = f"{context}\n\nUser: {message}"
        else:
            query = message

        # Stream response
        full_response = []
        async for chunk in self.engine.stream_query(query, **kwargs):
            if chunk.token:
                full_response.append(chunk.token)
            yield chunk

        # Add assistant response to history
        self.conversation_history.append(
            ChatMessage(role="assistant", content="".join(full_response))
        )

        # Trim history if too long
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]

    def _build_context(self) -> str:
        """Build context from conversation history."""
        context_parts = []
        for msg in self.conversation_history[-5:]:  # Last 5 messages
            role = msg.role.capitalize()
            context_parts.append(f"{role}: {msg.content}")
        return "\n".join(context_parts)

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
