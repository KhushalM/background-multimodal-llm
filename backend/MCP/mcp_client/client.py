import subprocess
import json
import os
import asyncio
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Load config
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "your-api-key")


class PerplexityClient:
    """
    MCP Client for Perplexity Ask server integration with Gemini LLM.
    Provides web research capabilities through the Perplexity API.
    """

    def __init__(self):
        self.proc: Optional[subprocess.Popen] = None
        self.is_connected = False

    async def connect(self) -> bool:
        """Start the MCP Perplexity server"""
        try:
            if self.is_connected:
                logger.info("MCP server already connected")
                return True

            logger.info("Starting MCP Perplexity server...")
            docker_cmd = ["docker", "run", "-i", "--rm", "-e", f"PERPLEXITY_API_KEY={PERPLEXITY_API_KEY}", "mcp/perplexity-ask"]
            self.proc = subprocess.Popen(
                docker_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
            )

            self.is_connected = True
            logger.info("MCP Perplexity server started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            self.is_connected = False
            return False

    def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a request to the MCP server"""
        if not self.is_connected or not self.proc or not self.proc.stdin or not self.proc.stdout:
            logger.error("MCP server not connected or stdin/stdout not available")
            return None

        try:
            request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}

            request_json = json.dumps(request) + "\n"
            self.proc.stdin.write(request_json)
            self.proc.stdin.flush()

            # Read response
            response_line = self.proc.stdout.readline()
            if response_line:
                return json.loads(response_line.strip())
            return None

        except Exception as e:
            logger.error(f"Error sending request: {e}")
            return None

    async def list_tools(self) -> Optional[List[str]]:
        """List available tools from the MCP server"""
        try:
            response = self._send_request("tools/list", {})
            if response and "result" in response:
                tools = response["result"].get("tools", [])
                return [tool["name"] for tool in tools]
            return None
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return None

    async def tool_call(self, json_rpc_request: str) -> Optional[str]:
        """Send a JSON-RPC request to the MCP server"""
        if not self.is_connected or not self.proc:
            logger.error("MCP server not connected")
            return None
        try:
            request = json.loads(json_rpc_request)
            request_json = json.dumps(request) + "\n"
            self.proc.stdin.write(request_json)
            self.proc.stdin.flush()

            response_line = self.proc.stdout.readline()
            if response_line:
                return json.loads(response_line.strip())
            return None

        except Exception as e:
            logger.error(f"Error sending request: {e}")
            logger.error(f"Response: {json_rpc_request}")
            return None

    async def ask(self, question: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """
        Ask a question using the Perplexity Ask tool

        Args:
            question: The question to ask
            conversation_history: Optional conversation context

        Returns:
            The response from Perplexity or None if failed
        """
        try:
            # Prepare messages for Perplexity
            messages = []

            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history)

            # Add the current question
            messages.append({"role": "user", "content": question})

            params = {"name": "perplexity_ask", "arguments": {"messages": messages}}

            response = self._send_request("tools/call", params)

            if response and "result" in response:
                content = response["result"].get("content", [])
                if content and len(content) > 0:
                    return content[0].get("text", "")

            return None

        except Exception as e:
            logger.error(f"Error asking question: {e}")
            return None

    async def research(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """
        Perform deep research using the Perplexity Research tool

        Args:
            query: The research query
            conversation_history: Optional conversation context

        Returns:
            The research response from Perplexity or None if failed
        """
        try:
            messages = []

            if conversation_history:
                messages.extend(conversation_history)

            messages.append({"role": "user", "content": query})

            params = {"name": "perplexity_research", "arguments": {"messages": messages}}

            response = self._send_request("tools/call", params)

            if response and "result" in response:
                content = response["result"].get("content", [])
                if content and len(content) > 0:
                    return content[0].get("text", "")

            return None

        except Exception as e:
            logger.error(f"Error performing research: {e}")
            return None

    async def reason(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
        """
        Perform reasoning using the Perplexity Reason tool

        Args:
            query: The reasoning query
            conversation_history: Optional conversation context

        Returns:
            The reasoning response from Perplexity or None if failed
        """
        try:
            messages = []

            if conversation_history:
                messages.extend(conversation_history)

            messages.append({"role": "user", "content": query})

            params = {"name": "perplexity_reason", "arguments": {"messages": messages}}

            response = self._send_request("tools/call", params)

            if response and "result" in response:
                content = response["result"].get("content", [])
                if content and len(content) > 0:
                    return content[0].get("text", "")

            return None

        except Exception as e:
            logger.error(f"Error performing reasoning: {e}")
            return None

    def close(self):
        """Close the MCP server connection"""
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            finally:
                self.proc = None
                self.is_connected = False
                logger.info("MCP server connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


async def test_perplexity_client():
    """Test function for the Perplexity client"""
    client = PerplexityClient()

    try:
        # Connect to server
        if not await client.connect():
            print("❌ Failed to connect to MCP server")
            return

        print("✅ Connected to MCP server")

        # List available tools
        tools = await client.list_tools()
        print(f"📋 Available tools: {tools}")

        # Test ask function
        response = await client.ask("What's the capital of Japan?")
        print(f"🔍 Ask response: {response}")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    print(f"Perplexity API Key: {PERPLEXITY_API_KEY}")
    asyncio.run(test_perplexity_client())
