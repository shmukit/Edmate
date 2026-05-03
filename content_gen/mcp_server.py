import sys
import json
import os
from typing import Dict, Any, List, Optional
from content_gen.core.model_router import ModelRoutingEngine
from content_gen.core.config import CoreConfig


class EdmateMCPServer:
    """
    A Model Context Protocol (MCP) server for the Edmate Content Engine.
    Exposes intelligence and metrics as tools for AI Agents.
    """

    def __init__(self):
        self.router = ModelRoutingEngine()
        self.running = True

    def run(self):
        """Main loop for reading MCP messages from stdin."""
        print("Edmate MCP Server Started (JSON-RPC over Stdio)", file=sys.stderr)

        while self.running:
            line = sys.stdin.readline()
            if not line:
                break

            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = request.get("method")
        params = request.get("params", {})
        req_id = request.get("id")

        # MCP Handshake / Capability Discovery
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": True
                        }
                    },
                    "serverInfo": {
                        "name": "edmate-content-engine",
                        "version": "1.0.0"
                    }
                }
            }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": [
                        {
                            "name": "generate_edmate_content",
                            "description": "Generate curriculum-aligned educational content using the modular Edmate router.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "prompt": {"type": "string"},
                                    "task_type": {"type": "string", "enum": ["extraction", "generation", "validation"]},
                                    "json_mode": {"type": "boolean"}
                                },
                                "required": ["prompt"]
                            }
                        },
                        {
                            "name": "get_pipeline_metrics",
                            "description": "Retrieve real-time cost and token usage for the current session.",
                            "inputSchema": {"type": "object", "properties": {}}
                        }
                    ]
                }
            }

        if method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if tool_name == "generate_edmate_content":
                try:
                    result = self.router.generate_content(
                        prompt=tool_args["prompt"],
                        task_type=tool_args.get("task_type", "generation"),
                        json_mode=tool_args.get("json_mode", False)
                    )
                    return self._tool_response(req_id, result)
                except Exception as e:
                    return self._error_response(req_id, f"Router Error: {str(e)}")

            elif tool_name == "get_pipeline_metrics":
                metrics = self.router.get_summary()
                return self._tool_response(req_id, json.dumps(metrics, indent=2))

        return None

    def _tool_response(self, req_id: Any, text: str) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": text}]
            }
        }

    def _error_response(self, req_id: Any, message: str) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32000, "message": message}
        }


if __name__ == "__main__":
    server = EdmateMCPServer()
    server.run()
