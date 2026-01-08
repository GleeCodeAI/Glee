"""Entry point for Glee"""

import sys
import asyncio

from .server import main


def run():
    """Run the Glee MCP server"""
    if "--help" in sys.argv or "-h" in sys.argv:
        print("""
Glee - Multi-Agent Code Collaboration Platform

Usage:
  python -m glee          Start the MCP server (default)
  python -m glee --help   Show this help message

The MCP server provides the following tools:
  - start_review      Start a code review session using Codex
  - continue_review   Continue a review after human input
  - get_review_status Get the status of a review session

Configuration:
  Add to your Claude Code MCP config (~/.claude/settings.json):

  {
    "mcpServers": {
      "glee": {
        "command": "uv",
        "args": ["run", "--directory", "/path/to/clean-code-agent", "python", "-m", "glee"]
      }
    }
  }
""")
        sys.exit(0)

    asyncio.run(main())


if __name__ == "__main__":
    run()
