"""
Enhanced Tool Calling System using DSPy and LangGraph
Improves perplexity tool calling with intelligent optimization and workflow
management.
"""

import logging
import json
from typing import Dict, Any, List, Optional, TypedDict
from datetime import datetime

import dspy
from langgraph.graph import StateGraph, END

from MCP.mcp_client.client import PerplexityClient
from MCP.mcp_client.perplexity_tool_handle import PerplexityToolHandle

logger = logging.getLogger(__name__)

# ==================== DSPy Signatures ====================


class ToolIntentSignature(dspy.Signature):
    """Determine if user query requires external tool usage"""

    user_query = dspy.InputField(desc="User's question or request")
    conversation_context = dspy.InputField(desc="Recent conversation history")
    screen_context = dspy.InputField(desc="Screen analysis or context from image if available")

    needs_tool = dspy.OutputField(desc="Boolean: does this require a tool?")
    intent_type = dspy.OutputField(desc="ask|none")
    confidence = dspy.OutputField(desc="Confidence score 0-1")
    reasoning = dspy.OutputField(desc="Why this decision was made")


class ToolSelectionSignature(dspy.Signature):
    """Select the optimal tool for the given intent"""

    intent_type = dspy.InputField(desc="Type of intent: ask")
    user_query = dspy.InputField(desc="Original user query")
    available_tools = dspy.InputField(desc="List of available tools")
    conversation_context = dspy.InputField(desc="Recent conversation context")

    selected_tool = dspy.OutputField(desc="Name of selected tool")
    reasoning = dspy.OutputField(desc="Why this tool was selected")
    confidence = dspy.OutputField(desc="Confidence in selection 0-1")


class ParameterOptimizationSignature(dspy.Signature):
    """Optimize parameters for tool execution"""

    tool_name = dspy.InputField(desc="Selected tool name")
    user_query = dspy.InputField(desc="Original user query with screen context if available")
    context = dspy.InputField(desc="All available context including conversation and screen analysis")
    intent_type = dspy.InputField(desc="ask|none")

    optimized_query = dspy.OutputField(desc="Enhanced query incorporating screen context and conversation history for better results")
    system_prompt = dspy.OutputField(desc="System prompt requesting concise response under 150 words with key information only")
    search_parameters = dspy.OutputField(desc="Additional search parameters JSON")


class ResponseParsingSignature(dspy.Signature):
    """Parse and validate tool response"""

    tool_response = dspy.InputField(desc="Raw response from tool")
    original_query = dspy.InputField(desc="Original user query")
    tool_name = dspy.InputField(desc="Tool that was used")

    parsed_content = dspy.OutputField(desc="Extracted main content")
    citations = dspy.OutputField(desc="Extracted citations if any")
    quality_score = dspy.OutputField(desc="Quality assessment 0-1")
    issues = dspy.OutputField(desc="Any issues found")


class ResultSynthesisSignature(dspy.Signature):
    """Synthesize tool results with conversational context"""

    tool_result = dspy.InputField(desc="Parsed tool result")
    original_query = dspy.InputField(desc="Original user query")
    conversation_context = dspy.InputField(desc="Conversation history")
    screen_context = dspy.InputField(desc="Screen analysis and context if available")

    synthesized_response = dspy.OutputField(desc="Natural conversational response incorporating screen context when relevant")
    confidence = dspy.OutputField(desc="Confidence in response 0-1")


# ==================== DSPy Modules ====================


class ToolIntentClassifier(dspy.Module):
    """Classifies user intent and determines if tools are needed"""

    def __init__(self):
        super().__init__()
        self.classify = dspy.ChainOfThought(ToolIntentSignature)

    def forward(self, user_query: str, conversation_context: str = "", screen_context: str = ""):
        result = self.classify(user_query=user_query, conversation_context=conversation_context, screen_context=screen_context)
        return result


class ToolSelector(dspy.Module):
    """Selects the best tool for the given intent"""

    def __init__(self):
        super().__init__()
        self.select = dspy.ChainOfThought(ToolSelectionSignature)

    def forward(self, intent_type: str, user_query: str, available_tools: List[str], conversation_context: str = ""):
        tools_str = ", ".join(available_tools)
        result = self.select(intent_type=intent_type, user_query=user_query, available_tools=tools_str, conversation_context=conversation_context)
        return result


class ParameterOptimizer(dspy.Module):
    """Optimizes tool parameters and query enhancement"""

    def __init__(self):
        super().__init__()
        self.optimize = dspy.ChainOfThought(ParameterOptimizationSignature)

    def forward(self, tool_name: str, user_query: str, context: str, intent_type: str):
        result = self.optimize(tool_name=tool_name, user_query=user_query, context=context, intent_type=intent_type)
        return result


class ResponseParser(dspy.Module):
    """Parses and validates tool responses"""

    def __init__(self):
        super().__init__()
        self.parse = dspy.ChainOfThought(ResponseParsingSignature)

    def forward(self, tool_response: str, original_query: str, tool_name: str):
        result = self.parse(tool_response=tool_response, original_query=original_query, tool_name=tool_name)
        return result


class ResultSynthesizer(dspy.Module):
    """Synthesizes tool results with conversational context"""

    def __init__(self):
        super().__init__()
        self.synthesize = dspy.ChainOfThought(ResultSynthesisSignature)

    def forward(self, tool_result: str, original_query: str, conversation_context: str = "", screen_context: str = ""):
        result = self.synthesize(tool_result=tool_result, original_query=original_query, conversation_context=conversation_context, screen_context=screen_context)
        return result


# ==================== LangGraph State ====================


class ToolCallingState(TypedDict):
    # Input data
    user_query: str
    conversation_context: str
    screen_context: str
    session_id: str
    available_tools: List[str]

    # Decision tracking
    intent_classification: Dict[str, Any]
    tool_selection: Dict[str, Any]
    parameter_optimization: Dict[str, Any]

    # Execution tracking
    tool_execution_history: List[Dict[str, Any]]
    current_tool: Optional[str]
    retry_count: int
    max_retries: int

    # Results
    tool_response: Optional[str]
    parsed_response: Optional[Dict[str, Any]]
    final_response: Optional[str]

    # Metrics and learning
    execution_success: bool
    response_quality_score: float
    error_messages: List[str]


# ==================== Enhanced Tool Calling Service ====================


class EnhancedToolCallingService:
    """Enhanced tool calling service using DSPy and LangGraph"""

    def __init__(self, gemini_api_key: str):
        # Initialize DSPy with Gemini
        import os

        os.environ["GOOGLE_API_KEY"] = gemini_api_key
        dspy.settings.configure(lm=dspy.LM(model="gemini/gemini-2.0-flash-exp", max_tokens=8000, temperature=0.3))

        # Initialize DSPy modules
        self.intent_classifier = ToolIntentClassifier()
        self.tool_selector = ToolSelector()
        self.parameter_optimizer = ParameterOptimizer()
        self.response_parser = ResponseParser()
        self.result_synthesizer = ResultSynthesizer()

        # Initialize perplexity clients
        self.perplexity_client = PerplexityClient()
        self.perplexity_tool_handle = PerplexityToolHandle()

        # Build LangGraph workflow
        self.workflow = self._build_workflow()

        logger.info("Enhanced tool calling service initialized")

    def _build_workflow(self):
        """Build the LangGraph workflow for tool calling"""

        workflow = StateGraph(ToolCallingState)

        # Add nodes
        workflow.add_node("classify_intent", self._classify_intent_node)
        workflow.add_node("select_tool", self._select_tool_node)
        workflow.add_node("optimize_parameters", self._optimize_parameters_node)
        workflow.add_node("execute_tool", self._execute_tool_node)
        workflow.add_node("parse_response", self._parse_response_node)
        workflow.add_node("synthesize_result", self._synthesize_result_node)
        workflow.add_node("handle_error", self._handle_error_node)
        workflow.add_node("direct_response", self._direct_response_node)

        # Set entry point
        workflow.set_entry_point("classify_intent")

        # Add conditional edges
        workflow.add_conditional_edges("classify_intent", self._should_use_tool, {"use_tool": "select_tool", "direct_response": "direct_response"})

        workflow.add_edge("select_tool", "optimize_parameters")
        workflow.add_edge("optimize_parameters", "execute_tool")

        workflow.add_conditional_edges("execute_tool", self._check_execution_success, {"success": "parse_response", "retry": "optimize_parameters", "error": "handle_error"})

        workflow.add_edge("parse_response", "synthesize_result")
        workflow.add_edge("synthesize_result", END)
        workflow.add_edge("handle_error", END)
        workflow.add_edge("direct_response", END)

        return workflow.compile()

    async def _classify_intent_node(self, state: ToolCallingState) -> ToolCallingState:
        """Classify user intent using DSPy"""
        try:
            result = self.intent_classifier(user_query=state["user_query"], conversation_context=state["conversation_context"], screen_context=state["screen_context"])

            state["intent_classification"] = {
                "needs_tool": result.needs_tool.lower() == "true",
                "intent_type": result.intent_type,
                "confidence": float(result.confidence),
                "reasoning": result.reasoning,
            }

            logger.info(f"Intent classified: {state['intent_classification']}")

        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            state["intent_classification"] = {"needs_tool": False, "intent_type": "none", "confidence": 0.0, "reasoning": f"Error: {e}"}

        return state

    async def _select_tool_node(self, state: ToolCallingState) -> ToolCallingState:
        """Select tool using DSPy"""
        try:
            result = self.tool_selector(
                intent_type=state["intent_classification"]["intent_type"], user_query=state["user_query"], available_tools=state["available_tools"], conversation_context=state["conversation_context"]
            )

            state["tool_selection"] = {"selected_tool": result.selected_tool, "reasoning": result.reasoning, "confidence": float(result.confidence)}
            state["current_tool"] = result.selected_tool

            logger.info(f"Tool selected: {state['tool_selection']}")

        except Exception as e:
            logger.error(f"Error in tool selection: {e}")
            state["error_messages"].append(f"Tool selection error: {e}")

        return state

    async def _optimize_parameters_node(self, state: ToolCallingState) -> ToolCallingState:
        """Optimize parameters using DSPy"""
        try:
            # Build comprehensive context
            context_parts = []
            if state["conversation_context"]:
                context_parts.append(f"Conversation: {state['conversation_context']}")
            if state["screen_context"] and state["screen_context"] != "No screen context available":
                context_parts.append(f"Screen Analysis: {state['screen_context']}")

            context = "\n".join(context_parts) if context_parts else "No additional context available"

            result = self.parameter_optimizer(tool_name=state["current_tool"], user_query=state["user_query"], context=context, intent_type=state["intent_classification"]["intent_type"])

            # Parse search parameters if they're JSON
            search_params = {}
            try:
                search_params = json.loads(result.search_parameters)
            except json.JSONDecodeError:
                search_params = {"enhanced": True}

            state["parameter_optimization"] = {"optimized_query": result.optimized_query, "system_prompt": result.system_prompt, "search_parameters": search_params}

            logger.info(f"Parameters optimized with context: {state['parameter_optimization']}")

        except Exception as e:
            logger.error(f"Error in parameter optimization: {e}")
            state["error_messages"].append(f"Parameter optimization error: {e}")

        return state

    async def _execute_tool_node(self, state: ToolCallingState) -> ToolCallingState:
        """Execute the selected tool"""
        try:
            # Prepare the enhanced request
            optimized = state.get("parameter_optimization", {})

            messages = []
            # Add concise system prompt
            system_prompt = optimized.get(
                "system_prompt", "Provide a concise, focused answer. Keep the response under 100 words keeping it like a natural conversation. Include only the most relevant and current information."
            )
            messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": optimized.get("optimized_query", state["user_query"])})

            # Create standard JSON-RPC request (MCP compatible)
            # Note: Enhanced metadata is logged but not sent to preserve MCP compatibility
            logger.info(f"Enhanced tool call metadata: intent_confidence={state['intent_classification']['confidence']}, tool_reasoning={state['tool_selection']['reasoning']}")

            standard_request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": state["current_tool"], "arguments": {"messages": messages}}}

            # Execute tool call
            await self.perplexity_client.connect()
            logger.info(f"Sending tool request: {json.dumps(standard_request)}")
            tool_response = await self.perplexity_client.tool_call(json.dumps(standard_request))
            logger.info(f"Received tool response: {tool_response}")

            if tool_response:
                state["tool_response"] = str(tool_response)
                state["execution_success"] = True

                # Track execution history
                state["tool_execution_history"].append(
                    {"tool": state["current_tool"], "query": optimized.get("optimized_query", state["user_query"]), "success": True, "timestamp": datetime.now().isoformat()}
                )

                logger.info(f"Tool execution successful: {state['current_tool']}")
            else:
                state["execution_success"] = False
                state["error_messages"].append("Tool returned no response")

        except Exception as e:
            logger.error(f"Error executing tool: {e}")
            state["execution_success"] = False
            state["error_messages"].append(f"Tool execution error: {e}")
            state["retry_count"] += 1

        return state

    async def _parse_response_node(self, state: ToolCallingState) -> ToolCallingState:
        """Parse tool response using DSPy"""
        try:
            result = self.response_parser(tool_response=state["tool_response"], original_query=state["user_query"], tool_name=state["current_tool"])

            state["parsed_response"] = {"parsed_content": result.parsed_content, "citations": result.citations, "quality_score": float(result.quality_score), "issues": result.issues}
            state["response_quality_score"] = float(result.quality_score)

            logger.info(f"Response parsed with quality score: {result.quality_score}")

        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            state["error_messages"].append(f"Response parsing error: {e}")

        return state

    async def _synthesize_result_node(self, state: ToolCallingState) -> ToolCallingState:
        """Synthesize final result using DSPy"""
        try:
            tool_result = state["parsed_response"]["parsed_content"]

            result = self.result_synthesizer(tool_result=tool_result, original_query=state["user_query"], conversation_context=state["conversation_context"], screen_context=state["screen_context"])

            state["final_response"] = result.synthesized_response

            logger.info("Result synthesized successfully")

        except Exception as e:
            logger.error(f"Error synthesizing result: {e}")
            state["final_response"] = state.get("tool_response", "Sorry, I couldn't process the response.")

        return state

    async def _handle_error_node(self, state: ToolCallingState) -> ToolCallingState:
        """Handle errors and provide fallback response"""
        error_summary = "; ".join(state["error_messages"])
        state["final_response"] = f"I encountered some issues while processing your request: {error_summary}. Please try rephrasing your question."
        return state

    async def _direct_response_node(self, state: ToolCallingState) -> ToolCallingState:
        """Provide direct response without tools - analyze user query and screen context directly"""
        try:
            # For direct responses, we can analyze the query and screen context without external tools
            if state.get("screen_context") and state["screen_context"] != "No screen context available":
                # Use the screen analysis in the response
                state["final_response"] = f"Based on your query and what I can see on your screen: {state['screen_context']}\n\nRegarding '{state['user_query']}', I can help with that directly."
            else:
                state["final_response"] = f"I can help with that directly. Regarding: {state['user_query']}"

            logger.info("Providing direct response with screen context analysis")

        except Exception as e:
            logger.error(f"Error in direct response: {e}")
            state["final_response"] = f"I can help with that directly. Regarding: {state['user_query']}"

        return state

    def _should_use_tool(self, state: ToolCallingState) -> str:
        """Determine if we should use a tool"""
        return "use_tool" if state["intent_classification"].get("needs_tool", False) else "direct_response"

    def _check_execution_success(self, state: ToolCallingState) -> str:
        """Check if tool execution was successful"""
        if state["execution_success"]:
            return "success"
        elif state["retry_count"] < state["max_retries"]:
            return "retry"
        else:
            return "error"

    async def process_query(
        self, user_query: str, conversation_context: str = "", screen_context: str = "", session_id: str = "default", available_tools: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Process a query using the enhanced tool calling system"""

        if available_tools is None:
            available_tools = ["perplexity_ask", "perplexity_research", "perplexity_reason"]

        # Initialize state
        initial_state: ToolCallingState = {
            "user_query": user_query,
            "conversation_context": conversation_context,
            "screen_context": screen_context,
            "session_id": session_id,
            "available_tools": available_tools,
            "intent_classification": {},
            "tool_selection": {},
            "parameter_optimization": {},
            "tool_execution_history": [],
            "current_tool": None,
            "retry_count": 0,
            "max_retries": 2,
            "tool_response": None,
            "parsed_response": None,
            "final_response": None,
            "execution_success": False,
            "response_quality_score": 0.0,
            "error_messages": [],
        }

        # Execute workflow
        try:
            final_state = await self.workflow.ainvoke(initial_state)

            return {
                "response": final_state["final_response"],
                "intent_classification": final_state["intent_classification"],
                "tool_selection": final_state.get("tool_selection", {}),
                "execution_success": final_state["execution_success"],
                "quality_score": final_state["response_quality_score"],
                "execution_history": final_state["tool_execution_history"],
                "errors": final_state["error_messages"],
            }

        except Exception as e:
            logger.error(f"Error in enhanced tool calling workflow: {e}")
            return {
                "response": f"I apologize, but I encountered an error processing your request: {e}",
                "intent_classification": {},
                "tool_selection": {},
                "execution_success": False,
                "quality_score": 0.0,
                "execution_history": [],
                "errors": [str(e)],
            }


# ==================== Factory Function ====================


async def create_enhanced_tool_calling_service(gemini_api_key: str) -> EnhancedToolCallingService:
    """Create and initialize enhanced tool calling service"""
    service = EnhancedToolCallingService(gemini_api_key)
    return service
