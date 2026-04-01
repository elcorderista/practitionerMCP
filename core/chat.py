# ================================
# core/chat.py
"""
Módulo que define la clase base Chat para gestionar conversaciones con Claude,
incluyendo el uso de tools proporcionadas por clientes MCP.
"""

from email import message
from core.claude import Claude
from mcp_client import MCPClient
from core.tools import ToolManager
from anthropic.types import MessageParam 

class Chat:
    """
    Clase base para manejar una conversación con Claude, con soporte para 
    herramientas definidas en servidores MCP. Mantiene el historial de mensajes
    y ejecuta un bucle que procesa respuestas de Claude, manejando llamadas a 
    herramientas cuando son solicitadas. 
    """
    def __init__(self, claude_service: Claude, clients: dict[str, MCPClient]):
        self.claude_service: Claude = claude_service
        self.clients: dict[str, MCPClient] = clients
        self.messages: list[MessageParam] = []

    async def _process_query(self, query: str):
        """
        Procesa una consulta del usuario antes de enviarla a Claude. 
        Por defecto, simplemente añade el mensaje del usuario al historial. 
        Las subclases pueden sobrescribir este método para enriquecer el prompt,
        por ejemplo, añadiendo contexto de documentos. 
        
        Args:
            query: Texto de la consulta del usuario. 
        """
        self.messages.append({"role": "user", "content": query})
    
    async def run(
        self,
        query: str,
    ) -> str:
        """
        Ejecuta el ciclo de conversación para una consulta específica. 
        Envía la consulta (tras procesarla) a Claude y maneja iterativamente las
        solicitudes de uso de herramientas hasta que Claude devuelve una 
        respuesta de texto final. 
        
        Args:
            query: La entrada del usuario. 
        Returns:
            str: La respuesta de texto final de Claude
        """
        final_text_response = ""
        
        await self._process_query(query)
        
        # Respuesta del agente mas bloques de respuesta de tools
        while True:
            response = self.claude_service.chat(
                messages=self.messages,
                tools=await ToolManager.get_all_tools(self.clients),
            )
            
            # Agrega la respuesta del agente a la lista de mensajes
            self.claude_service.add_assistant_message(self.messages, response)
            
            # Si claude solicita usar Tools
            if response.stop_reason == "tool_use":
                print(self.claude_service.text_from_message(response))
                tool_result_parts = await ToolManager.execute_tool_request(
                    self.clients, response
                )
                
                # Add resultados de las herramientas como mensaje de usuario
                self.claude_service.add_user_message(
                    self.messages, tool_result_parts
                )
            else:
                # Si va solo texto
                final_text_response = self.claude_service.text_from_message(response)
                break
        return final_text_response
                
                
            
            
            
            
        
    
    


