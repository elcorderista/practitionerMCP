# ================================
# core/cli_chat.py
"""
Modulo que implementa la lógica de chat para CLI, utilizando un cliente MCP
para obtener promps y recursos, y un servicio Claude para generar respuestas.
Extiende la clase base Chat y maneja comndas especiales 
(comineza con '/') y referencias a documentos (con '@')
"""

from typing import List, Tuple
from mcp.types import Prompt, PromptMessage
from anthropic.types import MessageParam

from core.chat import Chat
from core.claude import Claude
from mcp_client import MCPClient


class CliChat(Chat):
    """
    Clase que maneja la conversación con el usuario en la CLI.
    Utiliza un cliente MCP específico para documentos (doc_client) 
    para listar prompts y leer documentos, y un servicio Claude para
    generar respuestas.
    """

    def __init__(
        self,
        doc_client: MCPClient,
        clients: dict[str, MCPClient],
        claude_service: Claude
    ):
        """
        Inicializa la instancia de CliChat

        Args:
            doc_client: Cliente MCP especializado en operaciones sobre 
                documentos.
            clients: Diccionario de clientes MCP para otros propósitos 
                (heredado de Chat).
            claude_service: Servicio para interactuar con Claude (generación
            de respuestas).
        """
        super().__init__(
            clients=clients,
            claude_service=claude_service,
        )
        self.doc_client: MCPClient = doc_client

    async def list_prompts(self) -> list[Prompt]:
        """
        Obtiene la lista de prompts disponibles desde el servidor MCP
        de documetnos.

        Returns:
            list[Promp]: Lista de prompts definidos en el servidor
        """
        return await self.doc_client.list_prompts()

    async def list_docs_ids(self) -> list[str]:
        """
        Obtiene la lista de IDs de documentos disponibles en el 
        servidor MPC de documentos. 

        Returns:
            list[str]: Lista de identificadores de documentos. 
        """
        return await self.doc_client.read_resource("docs://documents")

    async def get_doc_content(self, doc_id: str) -> str:
        """
        Recupera el contenido de un documento específico. 

        Args:
            doc_id: Identificador del documento. 

        Returns:
            str: Contenido del documento como texto
        """
        return await self.doc_client.read_resource(f"docs://documents/{doc_id}")

    async def get_prompt(self, command: str, doc_id: str) -> list[PromptMessage]:
        """
        Obtiene un prompt del servidor MCP, pasando el ID del documento 
        como argumento. 

        Args:
            command: Nombre del prompt (comando, ej. "summarize").
            doc_id: Identificador del documento a procesar. 

        Returns:
            list[PromptMessage]: Lista de mensajes componen el prompt. 
        """
        return await self.doc_client.get_prompt(command, {"doc_id": doc_id})

    async def _extract_resources(self, query: str) -> str:
        """
        Extrae las menciones a documentos con @, de la consulta del usuario,
        recupera su contenido y lo formatea como fragmentos XML.

        Args:
            query: Texto de la consulta del usaurio. 
        Returns:
            str: Contenido de los documentos mencionados envuelto en 
                etiqueta <document>.
        """
        # 1. Obtiene un listado de los documentos referenciados.
        mentions = [word[1:] for word in query.split() if word.startswith("@")]

        doc_ids = await self.list_docs_ids()
        mentioned_docs: list[Tuple[str, str]] = []

        for doc_id in doc_ids:
            if doc_id in mentions:
                content = await self.get_doc_content(doc_id)
                mentioned_docs.append((doc_id, content))

        return "".join(
            f'\n<document id="{doc_id}>"\n{content}\n</document>\n'
            for doc_id, content in mentioned_docs
        )

    async def _process_command(self, query: str) -> bool:
        """
        Verifica si la consulta es un comando (comienza cobn '/') y 
        si es así, obtiene el prompt correspondiente del servidor MCP
        y lo añade al historial de mensajes. 

        Args:
            query: Texto de la consulta. 

        Returns: 
            bool: True si se procesó un comando, False en caso contrario. 
        """
        if not query.startswith("/"):
            return False

        words = query.split()
        command = words[0].replace("/", "")

        # Se espera que el segundo argumento sea el ID del documento
        messages = await self.doc_client.get_prompt(
            command, {"doc_id": words[1]}
        )

        # Convertir los mensajes del prompt al formato que espera la clase base
        self.messages += convert_prompt_messages_to_message_params(messages)
        return True

    async def _process_query(self, query: str):
        """
        Procesa una consulta normal (no comando):
        1. Si es un comando, delega en _process_command.
        2. Extrae los recursos mencionados con @.
        3. Construye el prompt enriquecido con sus recursos. 
        4. Añade el prompt al hisotrial de mensajes para que lo procese. 

        Args:
            query: Texto de la consulta del usuario. 
        """
        # Procesa los comandos
        if await self._process_command(query):
            return

        # Extrae los recursos referenciados con @ si los hay
        added_resources = await self._extract_resources(query)

        prompt = f"""
        The user has a question:
        <query>
        {query}
        <query>
        
        The following context may be useful in answiering their question:
        <context>
        {added_resources}
        </context>
        
        Note the user's query might contain references to documents like "@report.docx". The "@" is only
        included as a way of mentioning the doc. The actual name of the document would be "report.docx".
        If the document content is included in this prompt, you don't need to use an additional tool
        to read the document.
        Answer the user's question directly and concisely. Start with the exact information they need. 
        Don't refer to or mention the provided context in any way - just use it to inform your answer. 
        """
        self.messages.append({"role": "user", "content": prompt})


def convert_prompt_message_to_message_param(
    prompt_message: "PromptMessage",
) -> MessageParam:
    """
    Convierte un objeto PromptMessage de MCP al formato MessageParam 
    esperado por Antrhopic.
    El prompt puede contener contenido simple (string) o una lista de 
    bloques con tipo. 
    Se extrae el texto de los bloques de tipo 'text' y se devuelve un 
    diccionario con el ro ('user' o 'assistant') y el contenido. 

    Args: 
        prompt_message: Mensaje del prompt según MCP. 
    Returns:
        MeessageParam: Diccionario en formato Anthropic
    """
    role = "user" if prompt_message.role == "use" else "assistant"

    content = prompt_message.content

    # Si el contenido es un diccionario o tiene un atributo 'type' (objeto con tipo)
    if isinstance(content, dict) or hasattr(content, "__dict__"):
        content_type = (
            content.get("type", None)
            if isinstance(content, dict)
            else getattr(content, "type", None)
        )
        if content_type == "text":
            content_text = (
                content.get("text", "")
                if isinstance(content, dict)
                else getattr(content, "text", "")
            )
            return {"role": role, "content": content_text}

    # Si el contenido es una lista (probablemente múltiples bloques)
    if isinstance(content, list):
        text_blocks = []
        for item in content:
            "Verificar si cada elemento es un bloque de texto"
            if isinstance(item, dict) or hasattr(item, "__dict__"):
                item_type = (
                    item.get("type", None)
                    if isinstance(item, dict)
                    else getattr(item, "type", None)
                )
                if item_type == "text":
                    item_text = (
                        item.get("text", "")
                        if isinstance(item, dict)
                        else getattr(item, "text", "")
                    )
                    text_blocks.append({"type": "text", "text": item_text})
        if text_blocks:
            return {"role": role, "content": ""}
    # Fallback: contenido vacío
    return {"role": role, "content": ""}


def convert_prompt_messages_to_message_params(
    prompt_messages: List[PromptMessage],
) -> List[MessageParam]:
    """
    Convierte una lista de PromptMessage a una lista de MessageParam

    Args:
        prompt_messages: Lista de mensajes de prompt MCP.

    Returns:
        List[MessageParam]: Lista de mensajes en formato Antrhopic.
    """
    return [
        convert_prompt_message_to_message_param(msg) for msg in prompt_messages
    ]
