# launches the MCP server regardless of the caller's working directory; needed because
# an MCP client (Claude Code, Claude Desktop) spawns this as a subprocess and may not
# set the working directory to this project's root, which "python -m second_brain.mcp_server"
# would otherwise require to resolve the second_brain import

import sys
import os

PROJECT_ROOT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT_DIRECTORY)

from second_brain.mcp_server import vault_server

if __name__ == "__main__":
    vault_server.run(transport="stdio")
