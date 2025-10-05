"""
Token definitions for the Lapis Programming Language
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Any, Optional
from source_map import Span

class TokenType(Enum):
    # Literals
    NUMBER = auto()
    STRING = auto()
    TEMPLATE_LITERAL = auto()
    IDENTIFIER = auto()
    BOOLEAN = auto()
    
    # Keywords
    PACKAGE = auto()
    USE = auto()
    VAR = auto()
    FUNC = auto()
    CLASS = auto()
    IF = auto()
    ELSE = auto()
    ELIF = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    RETURN = auto()
    END = auto()
    THIS = auto()
    INIT = auto()
    PUBLIC = auto()
    PRIVATE = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    BREAK = auto()
    CONTINUE = auto()
    TRY = auto()
    CATCH = auto()
    FINALLY = auto()
    SWITCH = auto()
    CASE = auto()
    DEFAULT = auto()
    
    # Operators
    PLUS = auto()           # +
    MINUS = auto()          # -
    MULTIPLY = auto()       # *
    DIVIDE = auto()         # /
    POWER = auto()          # **
    MODULO = auto()         # %
    
    ASSIGN = auto()         # =
    PLUS_PLUS = auto()      # ++
    MINUS_MINUS = auto()    # --
    
    # Comparison
    EQUAL = auto()          # ==
    NOT_EQUAL = auto()      # !=
    LESS = auto()           # <
    LESS_EQUAL = auto()     # <=
    GREATER = auto()        # >
    GREATER_EQUAL = auto()  # >=
    
    # Logical
    AND = auto()            # &&
    OR = auto()             # ||
    NOT = auto()            # !
    
    # Delimiters
    LEFT_PAREN = auto()     # (
    RIGHT_PAREN = auto()    # )
    LEFT_BRACE = auto()     # {
    RIGHT_BRACE = auto()    # }
    LEFT_BRACKET = auto()   # [
    RIGHT_BRACKET = auto()  # ]
    COMMA = auto()          # ,
    SEMICOLON = auto()      # ;
    DOT = auto()            # .
    COLON = auto()          # :
    
    # Special
    NEWLINE = auto()
    TAB = auto()
    EOF = auto()
    
    # Comments
    COMMENT = auto()

@dataclass
class Token:
    type: TokenType
    lexeme: str
    literal: Any = None
    line: int = 1
    column: int = 1
    span: Optional[Span] = None  # Source span for this token
    
    def __repr__(self):
        if self.literal is not None:
            return f"Token({self.type.name}, '{self.lexeme}', {self.literal})"
        return f"Token({self.type.name}, '{self.lexeme}')"

# Keywords mapping
KEYWORDS = {
    'package': TokenType.PACKAGE,
    'use': TokenType.USE,
    'var': TokenType.VAR,
    'func': TokenType.FUNC,
    'class': TokenType.CLASS,
    'if': TokenType.IF,
    'else': TokenType.ELSE,
    'elif': TokenType.ELIF,
    'while': TokenType.WHILE,
    'for': TokenType.FOR,
    'in': TokenType.IN,
    'return': TokenType.RETURN,
    'end': TokenType.END,
    'this': TokenType.THIS,
    'init': TokenType.INIT,
    'public': TokenType.PUBLIC,
    'private': TokenType.PRIVATE,
    'true': TokenType.TRUE,
    'false': TokenType.FALSE,
    'null': TokenType.NULL,
    'break': TokenType.BREAK,
    'continue': TokenType.CONTINUE,
    'try': TokenType.TRY,
    'catch': TokenType.CATCH,
    'finally': TokenType.FINALLY,
    'switch': TokenType.SWITCH,
    'case': TokenType.CASE,
    'default': TokenType.DEFAULT,
}