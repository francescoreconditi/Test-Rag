"""
Test and benchmark HyDE (Hypothetical Document Embeddings) performance.
Compares retrieval quality between standard and HyDE-enhanced retrieval.
"""

import logging
import os
import statistics
import sys
import time
from typing import Any

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from services.rag_engine import RAGEngine

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HyDEBenchmark:
    """Benchmark suite for HyDE retrieval improvement."""

    def __init__(self):
        """Initialize benchmark with RAG engine."""
        logger.info("Initializing RAG engine for benchmark...")
        self.rag_engine = RAGEngine()

        # Test queries for financial documents
        self.test_queries = [
            "Qual è il fatturato totale dell'azienda?",
            "Come calcolare il ROE dell'azienda?",
            "Quali sono i principali indicatori di liquidità?",
            "Analizza la crescita anno su anno dei ricavi",
            "Spiega la posizione finanziaria netta",
            "Quali sono i margini operativi dell'azienda?",
            "Descrivi le principali voci di costo",
            "Come si è evoluto l'EBITDA negli ultimi anni?",
            "Quali sono i principali rischi finanziari?",
            "Analizza il capitale circolante netto",
        ]

    def run_benchmark(self) -> dict[str, Any]:
        """
        Run comprehensive benchmark comparing standard vs HyDE retrieval.

        Returns:
            Dictionary with benchmark results
        """
        results = {"standard": [], "hyde": [], "improvements": [], "summary": {}}

        logger.info(f"Running benchmark with {len(self.test_queries)} queries...")

        for i, query in enumerate(self.test_queries, 1):
            logger.info(f"Testing query {i}/{len(self.test_queries)}: {query[:50]}...")

            # Standard retrieval
            start_time = time.time()
            standard_result = self.rag_engine.query(query, top_k=3)
            standard_time = time.time() - start_time

            standard_score = self._calculate_retrieval_score(standard_result)
            results["standard"].append(
                {
                    "query": query,
                    "time": standard_time,
                    "score": standard_score,
                    "sources_count": len(standard_result.get("sources", [])),
                }
            )

            # HyDE retrieval
            start_time = time.time()
            hyde_result = self.rag_engine.query_with_hyde(query, top_k=3)
            hyde_time = time.time() - start_time

            hyde_score = self._calculate_retrieval_score(hyde_result)
            results["hyde"].append(
                {
                    "query": query,
                    "time": hyde_time,
                    "score": hyde_score,
                    "sources_count": len(hyde_result.get("sources", [])),
                }
            )

            # Calculate improvement
            improvement = ((hyde_score - standard_score) / standard_score * 100) if standard_score > 0 else 0
            results["improvements"].append(improvement)

            logger.info(f"  Standard: {standard_score:.3f} ({standard_time:.2f}s)")
            logger.info(f"  HyDE: {hyde_score:.3f} ({hyde_time:.2f}s)")
            logger.info(f"  Improvement: {improvement:.1f}%")

        # Calculate summary statistics
        results["summary"] = self._calculate_summary(results)

        return results

    def _calculate_retrieval_score(self, result: dict[str, Any]) -> float:
        """
        Calculate retrieval quality score.

        Args:
            result: Query result

        Returns:
            Quality score (0-1)
        """
        score = 0.0

        # Check if answer exists and is meaningful
        if result.get("answer"):
            answer_length = len(result["answer"])
            if answer_length > 100:
                score += 0.3
            elif answer_length > 50:
                score += 0.2
            elif answer_length > 0:
                score += 0.1

        # Check source quality
        sources = result.get("sources", [])
        if sources:
            # Average source score
            source_scores = [s.get("score", 0) for s in sources]
            avg_source_score = sum(source_scores) / len(source_scores) if source_scores else 0
            score += avg_source_score * 0.5

            # Bonus for multiple relevant sources
            if len(sources) >= 3:
                score += 0.2
            elif len(sources) >= 2:
                score += 0.1

        # Check confidence
        confidence = result.get("confidence", 0)
        score += confidence * 0.2

        return min(score, 1.0)

    def _calculate_summary(self, results: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate summary statistics.

        Args:
            results: Benchmark results

        Returns:
            Summary statistics
        """
        standard_scores = [r["score"] for r in results["standard"]]
        hyde_scores = [r["score"] for r in results["hyde"]]
        standard_times = [r["time"] for r in results["standard"]]
        hyde_times = [r["time"] for r in results["hyde"]]

        summary = {
            "standard": {
                "avg_score": statistics.mean(standard_scores),
                "median_score": statistics.median(standard_scores),
                "avg_time": statistics.mean(standard_times),
                "total_time": sum(standard_times),
            },
            "hyde": {
                "avg_score": statistics.mean(hyde_scores),
                "median_score": statistics.median(hyde_scores),
                "avg_time": statistics.mean(hyde_times),
                "total_time": sum(hyde_times),
            },
            "improvements": {
                "avg_improvement": statistics.mean(results["improvements"]),
                "median_improvement": statistics.median(results["improvements"]),
                "max_improvement": max(results["improvements"]),
                "min_improvement": min(results["improvements"]),
                "queries_improved": sum(1 for i in results["improvements"] if i > 0),
            },
        }

        # Overall improvement percentage
        overall_improvement = (
            ((summary["hyde"]["avg_score"] - summary["standard"]["avg_score"]) / summary["standard"]["avg_score"] * 100)
            if summary["standard"]["avg_score"] > 0
            else 0
        )

        summary["overall_improvement_percentage"] = overall_improvement

        return summary

    def print_results(self, results: dict[str, Any]):
        """
        Print formatted benchmark results.

        Args:
            results: Benchmark results
        """
        print("\n" + "=" * 60)
        print("HyDE BENCHMARK RESULTS")
        print("=" * 60)

        summary = results["summary"]

        print("\n📊 STANDARD RETRIEVAL:")
        print(f"  Average Score: {summary['standard']['avg_score']:.3f}")
        print(f"  Median Score: {summary['standard']['median_score']:.3f}")
        print(f"  Average Time: {summary['standard']['avg_time']:.2f}s")
        print(f"  Total Time: {summary['standard']['total_time']:.2f}s")

        print("\n🚀 HyDE RETRIEVAL:")
        print(f"  Average Score: {summary['hyde']['avg_score']:.3f}")
        print(f"  Median Score: {summary['hyde']['median_score']:.3f}")
        print(f"  Average Time: {summary['hyde']['avg_time']:.2f}s")
        print(f"  Total Time: {summary['hyde']['total_time']:.2f}s")

        print("\n📈 IMPROVEMENTS:")
        print(f"  Overall Improvement: {summary['overall_improvement_percentage']:.1f}%")
        print(f"  Average Improvement: {summary['improvements']['avg_improvement']:.1f}%")
        print(f"  Median Improvement: {summary['improvements']['median_improvement']:.1f}%")
        print(f"  Max Improvement: {summary['improvements']['max_improvement']:.1f}%")
        print(f"  Queries Improved: {summary['improvements']['queries_improved']}/{len(self.test_queries)}")

        print("\n" + "=" * 60)

        # Show per-query results
        print("\n📝 PER-QUERY RESULTS:")
        for i, improvement in enumerate(results["improvements"]):
            query = self.test_queries[i][:50] + "..." if len(self.test_queries[i]) > 50 else self.test_queries[i]
            symbol = "✅" if improvement > 0 else "❌"
            print(f"  {symbol} {query}: {improvement:+.1f}%")

        print("\n" + "=" * 60)

        # Final verdict
        if summary["overall_improvement_percentage"] > 20:
            print("✨ VERDICT: HyDE shows SIGNIFICANT improvement! (>20%)")
        elif summary["overall_improvement_percentage"] > 10:
            print("👍 VERDICT: HyDE shows GOOD improvement (10-20%)")
        elif summary["overall_improvement_percentage"] > 0:
            print("📊 VERDICT: HyDE shows MODEST improvement (<10%)")
        else:
            print("⚠️ VERDICT: HyDE shows NO improvement")

        print("=" * 60 + "\n")


def main():
    """Run HyDE benchmark."""
    try:
        benchmark = HyDEBenchmark()

        print("\n🔍 Starting HyDE Benchmark...")
        print(f"Testing {len(benchmark.test_queries)} queries")
        print("This may take a few minutes...\n")

        results = benchmark.run_benchmark()
        benchmark.print_results(results)

        # Also run built-in benchmark if available
        if hasattr(benchmark.rag_engine, "benchmark_hyde"):
            print("\n🔬 Running built-in benchmark...")
            built_in_results = benchmark.rag_engine.benchmark_hyde(benchmark.test_queries)
            if "error" not in built_in_results:
                print(f"Built-in benchmark improvement: {built_in_results.get('improvement_percentage', 0):.1f}%")

    except Exception as e:
        logger.error(f"Benchmark failed: {str(e)}")
        print(f"\n❌ Error running benchmark: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
