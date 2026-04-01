# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup & Running

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Install dependencies (devcontainer runs this automatically)
uv sync

# Run the app
uv run main.py

# Run the MCP server standalone (for testing)
python mcp_server.py

# Run the MCP client standalone (lists available tools)
python mcp_client.py
```

No lint or type checks are configured.

## Environment

Set `ANTHROPIC_API_KEY` in `.env` before running.

## Architecture

This is an MCP (Model Context Protocol) chat application. The intended data flow:

1. User input is captured via `prompt-toolkit` in `core/cli.py` / `core/cli_chat.py`
2. User message is sent to Claude via `core/claude.py` (`Claude` class wraps the Anthropic SDK)
3. Claude may respond with tool calls; `core/tools.py` (`ToolManager`) routes them to the appropriate `MCPClient`
4. `mcp_client.py` (`MCPClient`) launches `mcp_server.py` as a subprocess and communicates over stdio
5. `mcp_server.py` uses FastMCP to expose two tools: `read_doc_contents` and `edit_document`
6. Tool results are returned to Claude for a final response

**Key relationships:**
- `mcp_server.py` — runs as a child process; defines the document store (6 in-memory docs) and tools
- `mcp_client.py` — async context manager that manages the subprocess lifecycle via `AsyncExitStack`
- `core/claude.py` — stateful conversation history + Anthropic API call (supports tools, thinking mode)
- `core/tools.py` — `ToolManager` (class-method only) routes Claude's tool-use responses to the right `MCPClient`
- `core/chat.py`, `core/cli.py`, `core/cli_chat.py` — incomplete; these wire everything together into a CLI

## Current State

Archivos completos y funcionales:
- `mcp_server.py`, `mcp_client.py`, `core/claude.py` — completamente funcionales
- `core/tools.py` — completo; `_build_tool_result_part()` y `execute_tool_request()` funcionan correctamente
- `core/chat.py` — completo; implementa la clase base `Chat` con `_process_query` y `run`
- `core/cli_chat.py` — mayormente completo; implementa `CliChat(Chat)` con soporte para comandos `/`, referencias `@doc_id`, prompts MCP y conversión de mensajes

Archivos incompletos:
- `main.py` — solo imports, sin implementación
- `core/cli.py` — stub; `CommandAutoSuggest.__init__` no tiene cuerpo

Bugs conocidos en `core/cli_chat.py`:
- Línea 205: typo `"use"` debería ser `"user"` en `convert_prompt_message_to_message_param`
- Línea 243: devuelve `content: ""` en vez de `content: text_blocks` cuando hay bloques de texto

## Documents

The MCP server's in-memory document store (`mcp_server.py`) contains six sample documents referenced by name (e.g., `deposition.md`, `report.pdf`). New documents are added by editing the `docs` dict in that file.
