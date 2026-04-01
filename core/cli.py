from collections.abc import Buffer
from typing import List, Optional
from prompt_toolkit import PromptSession, buffer # Crea sesión iterativa 
from prompt_toolkit.completion import Completer, Completion # Personalizar autocompletado
from prompt_toolkit.key_binding import KeyBindings # Para atajos de teclado
from prompt_toolkit.styles import Style # estilos de colores
from prompt_toolkit.history import InMemoryHistory # almacena historial de comandos
from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion # para sugerencia automática mientras se escribe
from prompt_toolkit.document import Document # Clase para manejar texto
from prompt_toolkit.buffer import Buffer #  Clase interna para manejar el buffer

from core.cli_chat import CliChat

class CommandAutoSuggest(AutoSuggest):
    """
    Proporciona sugerencias automáticas para comandos que comienzan con '/'
    Cuando el usaurio escribe un comando válido (prompt), sugiere el primer argumento esperado. 
    """
    def __init__(self, prompts: List):
        """
        
        """
        
    