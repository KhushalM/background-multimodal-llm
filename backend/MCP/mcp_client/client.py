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
                # verify the process is still alive
                if not self.proc or self.proc.poll() is not None:
                    self.is_connected = False
                else:
                    logger.info("MCP server already connected")
                    return True

            logger.info("Starting MCP Perplexity server...")
            docker_cmd = ["docker", "run", "-i", "--rm", "-e", f"PERPLEXITY_API_KEY={PERPLEXITY_API_KEY}", "mcp/perplexity-ask"]
            self.proc = subprocess.Popen(
                docker_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # use binary mode for proper framing
                bufsize=0,
            )

            # perform handshake: tools/list
            handshake = self._send_framed({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {},
            })

            if handshake and isinstance(handshake, dict) and "result" in handshake:
                self.is_connected = True
                logger.info("MCP Perplexity server started successfully")
                return True
            else:
                stderr_output = b""
                if self.proc and self.proc.stderr:
                    try:
                        stderr_output = self.proc.stderr.read() or b""
                    except Exception:
                        pass
                logger.error(f"Handshake failed. Server stderr: {stderr_output.decode('utf-8', 'ignore')}")
                self.close()
                return False

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            self.is_connected = False
            return False

    def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a request to the MCP server using framed stdio"""
        if not self.is_connected or not self.proc or not self.proc.stdin or not self.proc.stdout:
            logger.error("MCP server not connected or stdin/stdout not available")
            return None

        try:
            request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            return self._send_framed(request)
        except Exception as e:
            logger.error(f"Error sending request: {e}")
            return None

    def _send_framed(self, obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send Content-Length framed JSON-RPC over stdio and read response"""
        if not self.proc or not self.proc.stdin or not self.proc.stdout:
            return None

        body = json.dumps(obj).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")

        # write header and body
        self.proc.stdin.write(header)
        self.proc.stdin.flush()
        self.proc.stdin.write(body)
        self.proc.stdin.flush()

        # read headers
        r = self.proc.stdout
        content_length: Optional[int] = None
        while True:
            line = r.readline()
            if not line:
                return None
            # lines are bytes in binary mode
            line = line.rstrip(b"\r\n")
            if line == b"":
                break
            if line.lower().startswith(b"content-length:"):
                try:
                    content_length = int(line.split(b":", 1)[1].strip())
                except Exception:
                    return None
        if content_length is None:
            return None

        remaining = content_length
        chunks: list[bytes] = []
        while remaining > 0:
            chunk = r.read(remaining)
            if not chunk:
                return None
            chunks.append(chunk)
            remaining -= len(chunk)
        try:
            return json.loads(b"".join(chunks).decode("utf-8"))
        except Exception:
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
            return self._send_framed(request)

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
