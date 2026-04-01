# ================================
# core/claude.py
"""
Módulo que proporciona una capa de abstracción sobre el cliente Anthropic
para facilitar la interacción con Claude, manejo de mensajes y herramientas
"""

from anthropic import Anthropic
from anthropic.types import Message

class Claude:
    """
    Servicio que envuelve al cliente Anthropic, simplifica la gestión 
    conversaciones, la adición de mensajes al historial y la extracción 
    de texto de las respuestas 
    """
    def __init__(self, model:str):
        """
        Inicializa el servicio con el modelo especificado. 
        
        Args:
            model: Identificador del modelo de Claude a utilizar 
                (ej: "claude-3-5-sonnet-20241022")
        """
        self.client = Anthropic()
        self.model = model
        
    def add_user_message(self, messages: list, message):
        """
        Añade un mensaje de usuario al historial 
        
        Args:
            messages: Lista que contiene el historial de la conversación 
                (se modificará in-place).
            message: Puede ser:
                - Un objeto Message devuelto por la API de Antrhipic.
                - El contenido directo del mensaje (string o lista de bloques) 
        """
        user_message = {
            "role": "user",
            "content": message.content
            if isinstance(message, Message)
            else message,
        }
        messages.append(user_message)
        
    def add_assistant_message(self, messages: list, message):
        """
        Añade un mensaje del asistente (Claude) al historial
        
        Args:
            messages: Lista que contiene el historial de la conversación
                (se modificará in-place).
            message: Puede ser:
                - Un objeto Message devuelto por la API de Anthripic. 
                - El contenido directo del mensaje (string o lista 
                de bloque).
        """
        assistance_menssage = {
            "role": "assistant", 
            "content": message.content
            if isinstance(message, Message)
            else message,
        }
        messages.append(assistance_menssage)
        
    def text_from_message(self, message:Message)->str:
        """
        Extrae un mensaje de Claude, ignorando bloques que no sean
        de tipo texto (como tool_use).
        
        Args:
            messages: Objeto Message devuelto por la API de Antropic.
            
        Returns:
            str: Texto concatenado de todos los bloques de tipo "text".
        """
        return "\n".join(
            [block.text for block in message.content if block.type == "text"]
        )
        
    def chat(
        self, 
        messages, 
        system=None,
        temperature=1.0,
        stop_sequences=[],
        tools=None,
        thinking=False,
        thinking_budget=1024,
    )-> Message:
        """
        Realiza una llamada al API de Antrhopic para obtener una respuesta
        de Claude.
        
        Args:
            messages: Lista de mensajes en el formato requerido por Anthropic
                (rol y contenido).
            system: Mensaje del sistema opcional (string).
            temperature: Temperatura para la generación (0.0 - 1.0).
            stop_sequence: Lista de secuencias que detienen la generación. 
            tools: Lista de herramientas en el formato definido por Anthropic.
            thingking: Habilita el modo "thingking" (razonamiento extendido).
            thingking_budget: Presupuesto de tokens para el modo thinking.
            
        Returns: 
            Message: Objeto Message con la respuesta Claude.
        """
        params = {
            "model": self.model,
            "max_tokens": 8000,
            "messages": messages,
            "temperature": temperature,
            "stop_sequences": stop_sequences,
        }
        
        if thinking:
            params["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget,
            }
        if tools:
            params["tools"]=tools
            
        if system:
            params["system"]=system
            
        message = self.client.messages.create(**params)
        return message
    
    
        