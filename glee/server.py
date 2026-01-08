"""MCP Server for Glee"""

import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .types import MCPReviewResult, ReviewStatus
from .state.storage import LocalStorage
from .state.session import SessionManager
from .graph.review_graph import run_single_review
from .services.codex_cli import get_changed_files


def create_server() -> Server:
    """Create the MCP server"""
    storage = LocalStorage()
    session_manager = SessionManager(storage)
    server = Server("glee-code-review")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="start_review",
                description="Start a code review session using Codex for the specified files. "
                           "If no files are specified, reviews all changed files in the current git repository.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of file paths to review. If not specified, uses git to find changed files.",
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context about the code changes.",
                        },
                        "focus_areas": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific areas to focus on (e.g., 'security', 'performance').",
                        },
                        "max_iterations": {
                            "type": "integer",
                            "description": "Maximum number of review iterations (default: 10).",
                        },
                    },
                },
            ),
            Tool(
                name="continue_review",
                description="Continue a review after providing human input to answer questions.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "review_id": {
                            "type": "string",
                            "description": "The review session ID.",
                        },
                        "human_answer": {
                            "type": "string",
                            "description": "The human answer to the pending questions.",
                        },
                    },
                    "required": ["review_id", "human_answer"],
                },
            ),
            Tool(
                name="get_review_status",
                description="Get the status of a review session.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "review_id": {
                            "type": "string",
                            "description": "The review session ID. If not specified, returns the most recent active session.",
                        },
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        project_path = os.getcwd()

        if name == "start_review":
            # Get files to review
            files = arguments.get("files", [])
            if not files:
                files = get_changed_files(project_path)
                if not files:
                    return [TextContent(
                        type="text",
                        text='{"status": "error", "message": "No changed files found to review."}',
                    )]

            # Create session
            max_iterations = arguments.get("max_iterations", 10)
            session = session_manager.create_session(
                files=files,
                project_path=project_path,
                max_iterations=max_iterations,
            )

            # Run review
            result = run_single_review(session, session_manager)

            response = MCPReviewResult(
                status=result.status,
                iteration=result.iteration,
                max_iterations=session.max_iterations,
                feedback=result.summary,
                issues=result.issues,
                questions=result.questions,
                summary=result.summary,
                review_id=session.review_id,
            )

            return [TextContent(type="text", text=response.model_dump_json(indent=2))]

        elif name == "continue_review":
            review_id = arguments.get("review_id")
            human_answer = arguments.get("human_answer")

            if not review_id or not human_answer:
                return [TextContent(
                    type="text",
                    text='{"status": "error", "message": "review_id and human_answer are required."}',
                )]

            # Get session
            session = session_manager.get_session(review_id)
            if not session:
                return [TextContent(
                    type="text",
                    text=f'{{"status": "error", "message": "Review session {review_id} not found."}}',
                )]

            # Answer questions
            session_manager.answer_questions(review_id, {"answer": human_answer})

            # Get updated session
            updated_session = session_manager.get_session(review_id)
            if not updated_session:
                return [TextContent(
                    type="text",
                    text='{"status": "error", "message": "Failed to update session."}',
                )]

            # Run review again
            result = run_single_review(updated_session, session_manager)

            response = MCPReviewResult(
                status=result.status,
                iteration=result.iteration,
                max_iterations=updated_session.max_iterations,
                feedback=result.summary,
                issues=result.issues,
                questions=result.questions,
                summary=result.summary,
                review_id=updated_session.review_id,
            )

            return [TextContent(type="text", text=response.model_dump_json(indent=2))]

        elif name == "get_review_status":
            review_id = arguments.get("review_id")

            if review_id:
                session = session_manager.get_session(review_id)
            else:
                session = session_manager.get_active_session(project_path)

            if not session:
                return [TextContent(
                    type="text",
                    text='{"status": "no_session", "message": "No active review session found."}',
                )]

            return [TextContent(
                type="text",
                text=session.model_dump_json(indent=2),
            )]

        else:
            return [TextContent(
                type="text",
                text=f'{{"status": "error", "message": "Unknown tool: {name}"}}',
            )]

    return server


async def main():
    """Main entry point"""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
