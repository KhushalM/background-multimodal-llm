#!/usr/bin/env python3
"""
Demo script showing the enhanced tool calling response format
compared to the original basic format.
"""

import json
from typing import Dict, Any


def show_original_tool_response() -> Dict[str, Any]:
    """Shows the original basic tool calling response"""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "perplexity_research", "arguments": {"messages": [{"role": "user", "content": "How much does an average Dunkin' store earn?"}]}},
    }


def show_enhanced_tool_response() -> Dict[str, Any]:
    """Shows the enhanced DSPy + LangGraph tool calling response"""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "metadata": {
            "dspy_intent_confidence": 0.94,
            "tool_selection_reasoning": ("Financial research query requires deep web search with citations"),
            "parameter_optimization": {"query_enhancement": "Applied financial data specificity optimization", "context_expansion": "Added industry context and geographic scope"},
            "execution_strategy": "research_with_validation",
        },
        "params": {
            "name": "perplexity_research",
            "arguments": {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are researching financial performance data for "
                            "franchise businesses. Focus on verified financial "
                            "reports, industry studies, and authoritative business "
                            "sources. Provide specific revenue ranges and cite "
                            "your sources."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "What is the average annual revenue and profit margin "
                            "for a Dunkin' Donuts franchise location in the "
                            "United States? Include data on initial investment "
                            "requirements and break-even timeframes."
                        ),
                    },
                ],
                "search_parameters": {"domain_preference": ["franchising.com", "bfa.org", "sec.gov", "dunkinbrands.com"], "date_range": "2022-2024", "result_type": "comprehensive_analysis"},
            },
        },
        "fallback_strategy": {"if_tool_fails": "perplexity_ask", "retry_count": 2, "alternative_query": "Dunkin Donuts franchise financial performance"},
    }


def compare_responses():
    """Compare original vs enhanced responses"""
    print("=== ORIGINAL BASIC TOOL CALLING ===")
    original = show_original_tool_response()
    print(json.dumps(original, indent=2))
    print(f"Size: {len(json.dumps(original))} characters")

    print("\n" + "=" * 50 + "\n")

    print("=== ENHANCED DSPy + LangGraph TOOL CALLING ===")
    enhanced = show_enhanced_tool_response()
    print(json.dumps(enhanced, indent=2))
    print(f"Size: {len(json.dumps(enhanced))} characters")

    print("\n=== KEY IMPROVEMENTS ===")
    improvements = [
        "✅ Intelligent intent classification with confidence scores",
        "✅ Automated tool selection with reasoning",
        "✅ Query optimization and enhancement",
        "✅ Comprehensive search parameters",
        "✅ Fallback strategies for error handling",
        "✅ Execution metadata for debugging",
        "✅ Context-aware system prompts",
        "✅ Quality assessment and validation",
    ]

    for improvement in improvements:
        print(improvement)


if __name__ == "__main__":
    compare_responses()
