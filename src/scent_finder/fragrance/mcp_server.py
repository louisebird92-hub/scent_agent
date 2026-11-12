"""Scent Finder MCP server (stdio) over the shared tools, for Omnigent or any MCP client.

Run: python -m scent_finder.fragrance.mcp_server
"""

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import tools

mcp = MCPServer(
    "scent-finder",
    instructions="Fragrance search, similarity, personal collection, scent DNA and wear log. "
    "Data is approximate and for demo purposes only.",
)

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False)

for fn in (tools.search_by_notes, tools.find_similar, tools.get_my_collection, tools.get_scent_dna):
    mcp.tool(annotations=READ_ONLY)(fn)
for fn in (tools.log_wear, tools.add_to_collection):
    mcp.tool(annotations=WRITE)(fn)

if __name__ == "__main__":
    mcp.run("stdio")
