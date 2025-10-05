"""
Lexer for the Lapis Programming Language
Converts source code into tokens
"""

from typing import List
from tokens import Token, TokenType, KEYWORDS
from errors import LexError
from source_map import get_source_map, Span

class Lexer:
    def __init__(self, source: str, file_path: str = "<string>"):
        self.source = source
        self.file_path = file_path
        self.tokens = []
        self.current = 0
        self.line = 1
        self.column = 1
        self.start = 0  # Start of current token
        
        # Register file with source map
        source_map = get_source_map()
        self.file_id = source_map.add_file(file_path, source)
    
    def tokenize(self) -> List[Token]:
        """Tokenize the source code and return a list of tokens"""
        while not self.is_at_end():
            self.start = self.current
            self.scan_token()
        
        self.tokens.append(Token(TokenType.EOF, "", None, self.line, self.column))
        return self.tokens
    
    def is_at_end(self) -> bool:
        """Check if we've reached the end of the source"""
        return self.current >= len(self.source)
    
    def scan_token(self):
        """Scan and create a token from current position"""
        c = self.advance()
        
        # Single-character tokens
        if c == '(':
            self.add_token(TokenType.LEFT_PAREN)
        elif c == ')':
            self.add_token(TokenType.RIGHT_PAREN)
        elif c == '{':
            self.add_token(TokenType.LEFT_BRACE)
        elif c == '}':
            self.add_token(TokenType.RIGHT_BRACE)
        elif c == '[':
            self.add_token(TokenType.LEFT_BRACKET)
        elif c == ']':
            self.add_token(TokenType.RIGHT_BRACKET)
        elif c == ',':
            self.add_token(TokenType.COMMA)
        elif c == '.':
            self.add_token(TokenType.DOT)
        elif c == ';':
            self.add_token(TokenType.SEMICOLON)
        elif c == ':':
            self.add_token(TokenType.COLON)
        elif c == '%':
            self.add_token(TokenType.MODULO)
        
        # Multi-character operators
        elif c == '+':
            if self.match('+'):
                self.add_token(TokenType.PLUS_PLUS)
            else:
                self.add_token(TokenType.PLUS)
        elif c == '-':
            if self.match('-'):
                self.add_token(TokenType.MINUS_MINUS)
            else:
                self.add_token(TokenType.MINUS)
        elif c == '*':
            if self.match('*'):
                self.add_token(TokenType.POWER)
            else:
                self.add_token(TokenType.MULTIPLY)
        elif c == '/':
            if self.match('/'):
                # Single-line comment - consume until end of line
                while self.peek() != '\n' and not self.is_at_end():
                    self.advance()
            elif self.match('*'):
                # Multi-line comment - consume until */
                self.multi_line_comment()
            else:
                self.add_token(TokenType.DIVIDE)
        elif c == '=':
            if self.match('='):
                self.add_token(TokenType.EQUAL)
            else:
                self.add_token(TokenType.ASSIGN)
        elif c == '!':
            if self.match('='):
                self.add_token(TokenType.NOT_EQUAL)
            else:
                self.add_token(TokenType.NOT)
        elif c == '<':
            if self.match('='):
                self.add_token(TokenType.LESS_EQUAL)
            else:
                self.add_token(TokenType.LESS)
        elif c == '>':
            if self.match('='):
                self.add_token(TokenType.GREATER_EQUAL)
            else:
                self.add_token(TokenType.GREATER)
        elif c == '&':
            if self.match('&'):
                self.add_token(TokenType.AND)
            else:
                span = self.create_span()
                raise LexError.unexpected_character(span, c)
        elif c == '|':
            if self.match('|'):
                self.add_token(TokenType.OR)
            else:
                span = self.create_span()
                raise LexError.unexpected_character(span, c)
        
        # Whitespace
        elif c == ' ' or c == '\r':
            pass  # Ignore spaces and carriage returns
        elif c == '\t':
            self.add_token(TokenType.TAB)
        elif c == '\n':
            self.add_token(TokenType.NEWLINE)
            self.line += 1
            self.column = 1
        
        # String literals
        elif c == '"':
            self.string('"')
        elif c == "'":
            self.string("'")
        elif c == '`':
            self.template_literal()
        
        # Numeric literals
        elif c.isdigit():
            self.number()
        
        # Identifiers and keywords
        elif c.isalpha() or c == '_':
            self.identifier()
        
        else:
            span = self.create_span()
            raise LexError.unexpected_character(span, c)
    
    def advance(self) -> str:
        """Consume and return the current character"""
        if self.is_at_end():
            return '\0'
        
        char = self.source[self.current]
        self.current += 1
        self.column += 1
        return char
    
    def match(self, expected: str) -> bool:
        """Check if current character matches expected, consume if so"""
        if self.is_at_end():
            return False
        if self.source[self.current] != expected:
            return False
        
        self.current += 1
        self.column += 1
        return True
    
    def peek(self) -> str:
        """Look at current character without consuming"""
        if self.is_at_end():
            return '\0'
        return self.source[self.current]
    
    def peek_next(self) -> str:
        """Look at next character without consuming"""
        if self.current + 1 >= len(self.source):
            return '\0'
        return self.source[self.current + 1]
    
    def string(self, quote_char='"'):
        """Handle string literals with escape sequences"""
        start_line = self.line
        start_column = self.column - 1
        
        result = ""
        while self.peek() != quote_char and not self.is_at_end():
            if self.peek() == '\\':
                self.advance()  # consume backslash
                if self.is_at_end():
                    span = Span(self.file_id, self.start, self.current)
                    raise LexError.unterminated_string(span)
                
                # Handle escape sequences
                escaped = self.advance()
                if escaped == 'n':
                    result += '\n'
                elif escaped == 't':
                    result += '\t'
                elif escaped == '\\':
                    result += '\\'
                elif escaped == '"':
                    result += '"'
                elif escaped == "'":
                    result += "'"
                elif escaped == quote_char:
                    result += quote_char
                else:
                    # For unrecognized escape sequences, keep the backslash
                    result += '\\' + escaped
            else:
                if self.peek() == '\n':
                    self.line += 1
                    self.column = 1
                result += self.advance()
        
        if self.is_at_end():
            span = Span(self.file_id, self.start, self.current)
            raise LexError.unterminated_string(span)
        
        # Consume closing quote
        self.advance()
        
        self.add_token(TokenType.STRING, result)
    
    def template_literal(self):
        """Handle template literals with {variable} syntax"""
        start_line = self.line
        start_column = self.column - 1
        
        # Parse the template literal content
        parts = []  # List of (text, variable_name) tuples
        current_text = ""
        
        while self.peek() != '`' and not self.is_at_end():
            if self.peek() == '\\':
                self.advance()  # consume backslash
                if self.is_at_end():
                    span = Span(self.file_id, self.start, self.current)
                    raise LexError.unterminated_string(span)
                
                # Handle escape sequences
                escaped = self.advance()
                if escaped == 'n':
                    current_text += '\n'
                elif escaped == 't':
                    current_text += '\t'
                elif escaped == '\\':
                    current_text += '\\'
                elif escaped == '`':
                    current_text += '`'
                elif escaped == '{':
                    current_text += '{'
                elif escaped == '}':
                    current_text += '}'
                else:
                    # For unrecognized escape sequences, keep the backslash
                    current_text += '\\' + escaped
            elif self.peek() == '{':
                # Start of variable placeholder
                self.advance()  # consume '{'
                
                # Add current text part
                if current_text:
                    parts.append((current_text, None))
                    current_text = ""
                
                # Extract variable name
                var_name = ""
                while self.peek() != '}' and not self.is_at_end():
                    if self.peek() == '\n':
                        self.line += 1
                        self.column = 1
                    var_name += self.advance()
                
                if self.is_at_end():
                    span = Span(self.file_id, self.start, self.current)
                    raise LexError.from_simple(
                        "LAP2006", "Unterminated template literal variable", span
                    )
                
                self.advance()  # consume '}'
                
                # Add variable part
                parts.append((None, var_name.strip()))
            else:
                if self.peek() == '\n':
                    self.line += 1
                    self.column = 1
                current_text += self.advance()
        
        if self.is_at_end():
            span = Span(self.file_id, self.start, self.current)
            raise LexError.from_simple(
                "LAP2006", "Unterminated template literal", span
            )
        
        # Add final text part
        if current_text:
            parts.append((current_text, None))
        
        # Consume closing backtick
        self.advance()
        
        self.add_token(TokenType.TEMPLATE_LITERAL, parts)
    
    def number(self):
        """Handle numeric literals"""
        while self.peek().isdigit():
            self.advance()
        
        # Look for decimal part
        if self.peek() == '.' and self.peek_next().isdigit():
            # Consume the '.'
            self.advance()
            
            while self.peek().isdigit():
                self.advance()
        
        value_str = self.source[self.start:self.current]
        value = float(value_str)
        # If it's a whole number, make it an int
        if value.is_integer():
            value = int(value)
        
        self.add_token(TokenType.NUMBER, value)
    
    def identifier(self):
        """Handle identifiers and keywords"""
        while (self.peek().isalnum() or self.peek() == '_'):
            self.advance()
        
        text = self.source[self.start:self.current]
        token_type = KEYWORDS.get(text, TokenType.IDENTIFIER)
        
        # Handle boolean literals and null
        if token_type == TokenType.TRUE:
            self.add_token(token_type, True)
        elif token_type == TokenType.FALSE:
            self.add_token(token_type, False)
        elif token_type == TokenType.NULL:
            self.add_token(token_type, None)
        else:
            literal = text if token_type == TokenType.IDENTIFIER else None
            self.add_token(token_type, literal)
    
    def add_token(self, token_type: TokenType, literal=None):
        """Add a token to the tokens list"""
        text = self.source[self.start:self.current]
        span = self.create_span()
        token = Token(token_type, text, literal, self.line, self.column - len(text), span)
        self.tokens.append(token)
    
    def multi_line_comment(self):
        """Handle multi-line comments /* ... */"""
        nesting_level = 1  # Track nesting for /* /* */ */
        
        while nesting_level > 0 and not self.is_at_end():
            if self.peek() == '/' and self.peek_next() == '*':
                # Found nested comment start
                self.advance()  # consume '/'
                self.advance()  # consume '*'
                nesting_level += 1
            elif self.peek() == '*' and self.peek_next() == '/':
                # Found comment end
                self.advance()  # consume '*'
                self.advance()  # consume '/'
                nesting_level -= 1
            elif self.peek() == '\n':
                # Track line numbers in multi-line comments
                self.line += 1
                self.column = 1
                self.advance()
            else:
                self.advance()
        
        # Check for unterminated comment
        if nesting_level > 0:
            span = self.create_span()
            raise LexError.from_simple(
                "LAP2005", "Unterminated multi-line comment", span
            )
    
    def create_span(self) -> Span:
        """Create a span for the current token"""
        return Span(self.file_id, self.start, self.current)
