"""
HyDE (Hypothetical Document Embeddings) implementation for improved retrieval.
Generates hypothetical documents to improve semantic search quality.
"""

from dataclasses import dataclass
import logging
from typing import Any, Optional

from llama_index.core import VectorStoreIndex
from llama_index.core.prompts import PromptTemplate
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.llms.openai import OpenAI
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class HyDEConfig:
    """Configuration for HyDE retriever"""

    num_hypothetical_docs: int = 3
    hypothetical_doc_max_tokens: int = 256
    temperature: float = 0.7
    include_original_query: bool = True
    fusion_weight: float = 0.3  # Weight for original query vs hypothetical docs


class HyDERetriever(BaseRetriever):
    """
    Hypothetical Document Embeddings (HyDE) Retriever.

    Improves retrieval by generating hypothetical documents that answer
    the query, then searching for similar real documents.
    """

    # Prompt templates for different domains
    HYPOTHESIS_PROMPTS = {
        "default": """Given the following question, write a detailed, informative answer that would be found in a high-quality document.
Be specific and include relevant details.

Question: {query}

Detailed Answer:""",
        "financial": """Given the following financial question, write a comprehensive answer as it would appear in a financial report or analysis document.
Include specific metrics, calculations, and business context where relevant.

Question: {query}

Professional Financial Answer:""",
        "technical": """Given the following technical question, write a detailed technical explanation as it would appear in documentation or a technical guide.
Include implementation details and best practices.

Question: {query}

Technical Documentation Answer:""",
        "business": """Given the following business question, write a comprehensive business analysis as it would appear in a strategic report.
Include market context, implications, and actionable insights.

Question: {query}

Business Analysis:""",
    }

    def __init__(
        self,
        base_retriever: BaseRetriever,
        llm: Optional[OpenAI] = None,
        config: Optional[HyDEConfig] = None,
        domain: str = "default",
    ):
        """
        Initialize HyDE retriever.

        Args:
            base_retriever: Base retriever to enhance with HyDE
            llm: Language model for generating hypothetical documents
            config: HyDE configuration
            domain: Domain for specialized prompts
        """
        super().__init__()
        self.base_retriever = base_retriever
        self.llm = llm or OpenAI(model="gpt-3.5-turbo")
        self.config = config or HyDEConfig()
        self.domain = domain
        self._prompt_template = PromptTemplate(self.HYPOTHESIS_PROMPTS.get(domain, self.HYPOTHESIS_PROMPTS["default"]))

    def _generate_hypothetical_documents(self, query: str) -> list[str]:
        """
        Generate hypothetical documents that answer the query.

        Args:
            query: User query

        Returns:
            List of hypothetical document texts
        """
        hypothetical_docs = []

        for i in range(self.config.num_hypothetical_docs):
            try:
                # Vary temperature for diversity
                temp = self.config.temperature + (i * 0.1)

                # Generate hypothetical answer
                prompt = self._prompt_template.format(query=query)

                response = self.llm.complete(
                    prompt, temperature=min(temp, 1.0), max_tokens=self.config.hypothetical_doc_max_tokens
                )

                hypothetical_doc = response.text.strip()

                # Add variation prompt for subsequent documents
                if i > 0:
                    variation_prompt = f"Provide another perspective on: {query}\n\nAlternative answer:"
                    response = self.llm.complete(
                        variation_prompt, temperature=min(temp, 1.0), max_tokens=self.config.hypothetical_doc_max_tokens
                    )
                    hypothetical_doc = response.text.strip()

                hypothetical_docs.append(hypothetical_doc)
                logger.debug(f"Generated hypothetical doc {i + 1}: {hypothetical_doc[:100]}...")

            except Exception as e:
                logger.warning(f"Failed to generate hypothetical doc {i + 1}: {str(e)}")
                continue

        return hypothetical_docs

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        """
        Retrieve nodes using HyDE.

        Args:
            query_bundle: Query bundle containing the query

        Returns:
            List of retrieved nodes with scores
        """
        query = query_bundle.query_str
        logger.info(f"HyDE retrieval for query: {query[:100]}...")

        # Generate hypothetical documents
        hypothetical_docs = self._generate_hypothetical_documents(query)

        if not hypothetical_docs:
            logger.warning("No hypothetical documents generated, falling back to direct retrieval")
            return self.base_retriever.retrieve(query_bundle)

        # Retrieve using each hypothetical document
        node_scores = {}  # Track best score for each node

        # Retrieve with hypothetical documents
        for hypo_doc in hypothetical_docs:
            hypo_bundle = QueryBundle(query_str=hypo_doc)
            nodes = self.base_retriever.retrieve(hypo_bundle)

            for node in nodes:
                node_id = node.node.id_
                if node_id not in node_scores or node.score > node_scores[node_id][1]:
                    node_scores[node_id] = (node, node.score)

        # Optionally include results from original query
        if self.config.include_original_query:
            original_nodes = self.base_retriever.retrieve(query_bundle)

            for node in original_nodes:
                node_id = node.node.id_
                # Weighted combination of scores
                original_score = node.score * self.config.fusion_weight

                if node_id in node_scores:
                    # Combine scores
                    combined_score = node_scores[node_id][1] * (1 - self.config.fusion_weight) + original_score
                    node_scores[node_id] = (node, combined_score)
                else:
                    node_scores[node_id] = (node, original_score)

        # Sort by score and return top results
        sorted_nodes = sorted(node_scores.values(), key=lambda x: x[1], reverse=True)

        # Return nodes with updated scores
        result_nodes = []
        for node, score in sorted_nodes:
            result_node = NodeWithScore(node=node.node, score=score)
            result_nodes.append(result_node)

        logger.info(f"HyDE retrieved {len(result_nodes)} unique nodes")
        return result_nodes

    async def _aretrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        """Async retrieve - delegates to sync for now."""
        return self._retrieve(query_bundle)


class AdaptiveHyDERetriever(HyDERetriever):
    """
    Adaptive HyDE retriever that adjusts strategy based on query type.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_classifier = QueryClassifier()

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        """
        Retrieve with adaptive HyDE strategy.

        Args:
            query_bundle: Query bundle

        Returns:
            Retrieved nodes
        """
        query = query_bundle.query_str

        # Classify query type
        query_type = self.query_classifier.classify(query)

        # Adjust HyDE parameters based on query type
        if query_type == "factual":
            # For factual queries, use fewer but more precise hypothetical docs
            self.config.num_hypothetical_docs = 2
            self.config.temperature = 0.3
            self.config.include_original_query = True

        elif query_type == "analytical":
            # For analytical queries, generate more diverse perspectives
            self.config.num_hypothetical_docs = 4
            self.config.temperature = 0.8
            self.config.include_original_query = False

        elif query_type == "definition":
            # For definitions, generate comprehensive explanations
            self.config.num_hypothetical_docs = 3
            self.config.temperature = 0.5
            self.config.hypothetical_doc_max_tokens = 512

        return super()._retrieve(query_bundle)


class QueryClassifier:
    """Simple query classifier for adaptive HyDE."""

    def classify(self, query: str) -> str:
        """
        Classify query type.

        Args:
            query: User query

        Returns:
            Query type (factual, analytical, definition, etc.)
        """
        query_lower = query.lower()

        # Simple keyword-based classification
        if any(word in query_lower for word in ["what is", "define", "meaning of"]):
            return "definition"
        elif any(word in query_lower for word in ["how", "why", "analyze", "explain"]):
            return "analytical"
        elif any(word in query_lower for word in ["when", "where", "who", "which"]):
            return "factual"
        else:
            return "general"


class HyDEQueryEngine:
    """
    Query engine enhanced with HyDE for improved retrieval.
    """

    def __init__(
        self,
        index: VectorStoreIndex,
        llm: Optional[OpenAI] = None,
        hyde_config: Optional[HyDEConfig] = None,
        domain: str = "default",
    ):
        """
        Initialize HyDE query engine.

        Args:
            index: Vector store index
            llm: Language model
            hyde_config: HyDE configuration
            domain: Domain for specialized prompts
        """
        self.index = index
        self.llm = llm or OpenAI(model="gpt-3.5-turbo")

        # Create base retriever
        base_retriever = index.as_retriever()

        # Wrap with HyDE
        self.hyde_retriever = HyDERetriever(
            base_retriever=base_retriever, llm=self.llm, config=hyde_config, domain=domain
        )

        # Create query engine with HyDE retriever
        self.query_engine = index.as_query_engine(retriever=self.hyde_retriever, llm=self.llm)

    def query(self, query: str, **kwargs) -> Any:
        """
        Query with HyDE-enhanced retrieval.

        Args:
            query: User query
            **kwargs: Additional arguments

        Returns:
            Query response
        """
        return self.query_engine.query(query, **kwargs)

    async def aquery(self, query: str, **kwargs) -> Any:
        """Async query."""
        return await self.query_engine.aquery(query, **kwargs)

    def benchmark_improvement(self, test_queries: list[str], base_retriever: BaseRetriever) -> dict[str, float]:
        """
        Benchmark HyDE improvement over base retriever.

        Args:
            test_queries: List of test queries
            base_retriever: Base retriever for comparison

        Returns:
            Dictionary with improvement metrics
        """
        hyde_scores = []
        base_scores = []

        for query in test_queries:
            query_bundle = QueryBundle(query_str=query)

            # Get HyDE results
            hyde_nodes = self.hyde_retriever.retrieve(query_bundle)
            if hyde_nodes:
                hyde_scores.append(np.mean([n.score for n in hyde_nodes[:5]]))

            # Get base results
            base_nodes = base_retriever.retrieve(query_bundle)
            if base_nodes:
                base_scores.append(np.mean([n.score for n in base_nodes[:5]]))

        # Calculate improvement
        avg_hyde = np.mean(hyde_scores) if hyde_scores else 0
        avg_base = np.mean(base_scores) if base_scores else 0

        improvement = ((avg_hyde - avg_base) / avg_base * 100) if avg_base > 0 else 0

        return {
            "hyde_avg_score": avg_hyde,
            "base_avg_score": avg_base,
            "improvement_percentage": improvement,
            "queries_tested": len(test_queries),
        }
