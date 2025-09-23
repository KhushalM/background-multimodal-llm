from .client import PerplexityClient
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Optional shared client that can be prewarmed at app startup
shared_client: Optional[PerplexityClient] = None


class PerplexityToolHandle:
    def __init__(self):
        global shared_client
        self.perplexity_client = shared_client if shared_client else PerplexityClient()

    async def handle_tool_call(self, response: str) -> str:
        """Handle tool call"""
        # Extract JSON content
        json_content = response.strip()
        if response.startswith("```json"):
            json_content = response.split("```json")[1].split("```")[0].strip()

        try:
            await self.perplexity_client.connect()
            logger.info(f"Connected: {self.perplexity_client.is_connected}")

            tool_response = await self.perplexity_client.tool_call(json_content)
            logger.info(f"Tool response type: {type(tool_response)}")

            # Extract text from tool response
            if isinstance(tool_response, dict):
                if "result" in tool_response and "content" in tool_response["result"]:
                    content = tool_response["result"]["content"]
                    if isinstance(content, list) and len(content) > 0:
                        if "text" in content[0]:
                            response_text = content[0]["text"]
                        else:
                            response_text = str(content[0])
                    else:
                        response_text = str(tool_response)
                else:
                    response_text = str(tool_response)
            elif isinstance(tool_response, str):
                response_text = tool_response
            else:
                response_text = str(tool_response)

        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            response_text = response

        return response_text

    def parse_perplexity_response(self, response: str) -> tuple[str, str]:
        """Parse perplexity response"""
        logger.info(f"Response: {response}")

        # Check for the actual Perplexity citation format
        if "Citations:" in response:
            parts = response.split("Citations:")
            if len(parts) >= 2:
                response_text = parts[0].strip()
                citation_info = "Citations:" + parts[1].strip()

                # Clean up the response text
                response_text = self._clean_perplexity_text(response_text)

                logger.info(f"Citation info: {citation_info}")
                logger.info(f"Cleaned response: {response_text}")
                return response_text, citation_info

        # If delimiter doesn't exist, still try to clean the text
        cleaned_response = self._clean_perplexity_text(response)
        logger.info("No citations delimiter found, returning cleaned original response")
        return cleaned_response, ""

    def _clean_perplexity_text(self, text: str) -> str:
        """Clean up Perplexity response text by removing excessive formatting"""
        import re

        # Remove citation references like [1], [2], [3] etc.
        text = re.sub(r"\[\d+\]", "", text)

        # Reduce excessive bold formatting - keep some but not too much
        # Replace **text** with text (remove bold completely for cleaner look)
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)

        # Clean up extra whitespace and newlines
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text
