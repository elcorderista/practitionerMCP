import sys
import asyncio
from typing import Optional, Any
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client


class MCPClient:
    """
    Cliente MCP que se conecta a un serever ejecutado como subproceso y gestiona 
    la comunicación asíncrona mediante stdio. Utiliza AsyncExistStack para asegurar
    la liberación correcta de todos los recursos (sessión, transporte, proceso)
    """

    def __init__(
        self,
        command: str,
        args: list[str],
        env: Optional[dict] = None,
    ):
        """
        Inicializa el cliente con los parámetros necesarios para lanzar el servicio.

        Args: 
            command: Comando a ejecutar (ej: "uv", "python"),
            args: :ista de argumentos para el comando (ej. ["run", "server.py"]).
            env: Diccionario opcional con variables de entorno para el proceso hijo
        """
        self._command = command
        self._args = args
        self._env = env
        self._session: Optional[ClientSession] = None
        self._exit_stack: AsyncExitStack = AsyncExitStack()

    async def connect(self):
        """
        Establece la conexión con el servidor MCP:
        1. Crea los parámetros del servidor
        2. Lanza el proceso hijo mediante stdio_client. 
        3. Crea la sesión del cliente sobre los flujos stdio
        4. Inicializa la sesión con el servidor
        Todos los recursos se registran en AsyncExitStack para su limpieza automática
        """
        server_params = StdioServerParameters(
            command=self._command,
            args=self._args,
            env=self._env,
        )
        print("2. Abriento stdio transport...")
        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        print("3. Creando sesión...")
        _studio, _write = stdio_transport
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(_studio, _write)
        )
        print("4. Hanshake...")
        await self._session.initialize()
        print("5. Conexion exitosa...")

    def session(self) -> ClientSession:
        """
        Devuelve la sesion activa del cliente. Lanza una excepción si no se ha 
        inicializado previamente. 

        Return:     
            ClientSesion: La sesión actual del cliente
        Raises:
            ConnectionError: Si la sesión no ha sido incializada
        """
        if self._session is None:
            raise ConnectionError(
                "Client session not initialized or cache not populated. Call connect_to_server first"
            )

        return self._session

    # =========================================
    # Funciones de interación con el server
    async def list_tools(self) -> list[types.Tool]:
        """
        Obtiene la lista de herramientas disponibles en el servidor.

        Retunrs:
            list[types.Tool]: Lista de herramientas definidas por el servidor MCP.
        """
        result = await self.session().list_tools()
        return result.tools

    async def call_tool(
        self, tool_name: str, tool_input: dict
    ) -> types.CallToolResult | None:
        """
        Invoca una herramienta específica en el server

        Args:
            tool_name: Nombre de la herramienta a invocar
            tool_input: Diccionario con los argumentos de entrada de la herramienta

        Returns:
            types.CallToolResult | None: Resultado de la llamada o None si falla
        """
        return await self.session().call_tool(tool_name, tool_input)

    async def list_prompts(self) -> list[types.Prompt]:
        # TODO: Return a list of prompts defined by the MCP server
        return []

    async def read_resource(self, uri: str) -> Any:
        # TODO: Read a resoruce, parse the contents and redturn it
        return []

    async def get_prompt(self, prompt_name, args: dict[str, str]):
        # TODO: Get a particular prompt defined by the MCP server
        return []

    # =========================================
    # Limpieza

    async def cleanup(self):
        """
        Libera todos los recursos gestionados por AsyncExitStack (session, transporte, proceso)
        Después de la limpieza, la sesión queda como None
        """
        await self._exit_stack.aclose()
        self._session = None

    async def __aenter__(self):
        """
        Entrada al contexto asíncrono: establece la conexión automáticamente. 

        Returns:
            MCPClient: La instancia del cliente ya conectada. 
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Salida del contexto asíncrono: realiza la limpieza de recurso. 

        Args:
            exc_type: Tipo de excepción si ocurrió alguna.
            exc_value: Valor de la excepción. 
            exc_tb: Tracebakc de la exepción.
        """
        await self.cleanup()

# Para testing


async def main():
    """
    Función principal de prueba. Crea un cliente MCP y lo usa dentro de un bloque
    async with, lo que conecta acutomáticamente y luego limpia al salir. 
    Acutalmente no realiza ninguna operación activa. 
    """
    async with MCPClient(
        command="uv",
        args=["run", "mcp_server.py"]
    ) as _client:
        result = await _client.list_tools()
        print(result)

if __name__ == "__main__":
    print(sys.platform)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
