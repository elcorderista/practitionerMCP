# ================================
# core/tools.py
"""
Módulo que gestiona herramientas definidas en servidores MCP.
Permite obtener todas las herramientas de múltiples clientes, encontrar
qué cliente posee una herramienta específica y ejecutar las solicitudes
de herramientas que Claude devuelve en sus respuestas. 
"""

import json
from typing import Optional, Literal, List
from mcp.types import CallToolResult, Tool, TextContent
from mcp_client import MCPClient
from anthropic.types import Message, ToolResultBlockParam


class ToolManager:
    """
    Clase utilitaria que centraliza la interacción con herramientas de MCP.
    Todos los métodos son de clase (no se necesita instanciar.)
    """
    @classmethod
    async def get_all_tools(
        cls,
        clients: dict[str, MCPClient]
    ) -> list[Tool]:
        """
        Obtiene todas las herramientas disponibles en los clientes MCP 
        proporcionados. 

        Args:
            clients: Diccionario de clientes MCP (clave: nombre o identificador,
                valor: instancia de MCPClient).
        Return:
            list[Tool]: Lista de herramientas en el formato requerido por 
                Anthropic, cada una con nombre, descripción y esquema de entrada.
        """
        tools = []
        for client in clients.values():
            tool_models = await client.list_tools()
            tools += [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema
                }
                for t in tool_models
            ]
        return tools

    @classmethod
    async def _find_client_with_tool(
        cls,
        clients: list[MCPClient],
        tool_name: str
    ) -> Optional[MCPClient]:
        """
        Busca el primer cliente que tenga una herramienta con el nombre edad.

        Args:
            clients: Lista de clientes MCP.
            tool_name: Nombre de la herramienta a buscar.

        Returns:
            MCPClient: El cliente que posee la herramienta, o None si no se
                encuentra.
        """
        for client in clients:
            tools = await client.list_tools()
            tool = next((t for t in tools if t.name == tool_name), None)
            if tool:
                return client
        return None

    @classmethod
    def _build_tool_result_part(
        cls,
        tool_use_id: str,
        text: str,
        status: Literal["success"] | Literal["error"],
    ) -> ToolResultBlockParam:
        """
        Construye un bloque de resultado de herramietna en el foramto 
        esperado por Anthripic. 

        Args:
            tool_use_id: Identificador único de la solicitud de herramienta. 
            text: Contenido del resultado (texto).
            status: Indica si la ejecución fue exitosa o no. 

        Returns:
            ToolResultBlockParam: Diccionario con la estructura de un resultado
            de una herramienta. 
        """
        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": text,
            "is_error": status == "error"
        }

    @classmethod
    async def execute_tool_request(
        cls,
        clients: dict[str, MCPClient],
        message: Message
    ) -> List[ToolResultBlockParam]:
        """
        Ejecuta todas las solicitudes de herramientas contenidas en un 
        mensaje de Claude. 

        Para cada bloque tipo `tool_use` en el mensaje:
        1. Encuntra el cliente MCP que tiene esa herramienta. 
        2. Si no existe, construye un resultado de error. 
        3. Si existe, llama a la herramienta con los argumentos 
        proporcionados. 
        4. Extrae el texto de la respuesta (soportaa contenido de tipo 
        TextContent).
        5. Construye un bloque de resultado con el texto (JSON serializado 
        si hay múltiples ítems) y el estado. 

        Args:
            clients: Diccionario de clientes MCP. 
            message: Mensaje de Claude que contiene bloques de tipo `tool_use`

        Returns:
            List[ToolResultBlockParam]: Lista de bloques de resultado de 
                herramientas, listos para ser añadidos a la conversación. 
        """
        tool_requests = [
            block for block in message.content if block.type == "tool_use"
        ]
        tool_result_blocks: list[ToolResultBlockParam] = []
        for tool_request in tool_requests:
            tool_use_id = tool_request.id
            tool_name = tool_request.name
            tool_input = tool_request.input
            print(f"tool request: {tool_name}")

            client = await cls._find_client_with_tool(
                list(clients.values()), tool_name
            )

            if not client:
                tool_result_part = cls._build_tool_result_part(
                    tool_use_id, "Could not find that tool", "error"
                )
                tool_result_blocks.append(tool_result_part)
                continue

            tool_output: CallToolResult | None = None
            try:
                tool_output = await client.call_tool(
                    tool_name, tool_input
                )
                items = []
                if tool_output:
                    items = tool_output.content

                # Extraer solo contenido de texto (ignorar otros tipos, como imagenes)
                content_list = [
                    item.text for item in items if isinstance(item, TextContent)
                ]
                content_json = json.dumps(content_list)
                tool_result_part = cls._build_tool_result_part(
                    tool_use_id,
                    content_json,
                    "error"
                    if tool_output and tool_output.isError
                    else "success",
                )
                tool_result_blocks.append(tool_result_part)
            except Exception as e:
                error_message = f"Error executing tool '{tool_name}': {e}"
                print(error_message)
                tool_result_part = cls._build_tool_result_part(
                    tool_use_id,
                    json.dumps({"error": error_message}),
                    "error",
                )
                tool_result_blocks.append(tool_result_part)
        return tool_result_blocks
