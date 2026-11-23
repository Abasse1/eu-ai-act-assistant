
from mcp.server import MCPServer

mcp = MCPServer(
    name="eu-ai-act-mcp-server",
    title="EU AI Act Assistant",
    version="0.1.0",
    instructions=(
        "Provides tools for searching and retrieving authoritative "
        "European Union Artificial Intelligence Act documents."
    ),
    log_level="INFO",
)
