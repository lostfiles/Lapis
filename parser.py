"""
Recursive descent parser for the Lapis Programming Language
"""

from typing import List, Optional, Union
from tokens import Token, TokenType
from ast_nodes import *
from errors import ParseError
from source_map import Span

class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current = 0
    
    def parse(self) -> Program:
        """Parse tokens into an AST"""
        statements = []
        while not self.is_at_end():
            # Skip newlines and tabs at top level
            if self.check(TokenType.NEWLINE) or self.check(TokenType.TAB):
                self.advance()
                continue
            
            stmt = self.declaration()
            if stmt:
                statements.append(stmt)
        
        return Program(statements)
    
    def declaration(self) -> Optional[Statement]:
        """Parse declarations (var, func, class, package)"""
        try:
            if self.match(TokenType.PACKAGE):
                return self.package_statement()
            if self.match(TokenType.VAR):
                return self.var_declaration()
            if self.match(TokenType.FUNC):
                return self.function_declaration()
            if self.match(TokenType.CLASS):
                return self.class_declaration()
            if self.match(TokenType.PUBLIC):
                return self.access_modified_declaration(AccessModifier.PUBLIC)
            if self.match(TokenType.PRIVATE):
                return self.access_modified_declaration(AccessModifier.PRIVATE)
            
            return self.statement()
        except ParseError as e:
            self.synchronize()
            return None
    
    def access_modified_declaration(self, access_modifier: AccessModifier) -> Statement:
        """Parse public/private declarations"""
        if self.match(TokenType.VAR):
            return self.var_declaration(access_modifier)
        elif self.match(TokenType.FUNC):
            return self.function_declaration(access_modifier)
        elif self.match(TokenType.CLASS):
            return self.class_declaration(access_modifier)
        else:
            raise ParseError("Expected 'var', 'func', or 'class' after access modifier", 
                           self.peek().line, self.peek().column)
    
    def package_statement(self) -> PackageStatement:
        """Parse package import statement"""
        path = self.consume(TokenType.STRING, "Expected string path after 'package'").literal
        
        imports = None  # None means import all public symbols
        
        # Check if 'use' clause is present
        if self.match(TokenType.USE):
            imports = []
            imports.append(self.consume(TokenType.IDENTIFIER, "Expected identifier after 'use'").literal)
            
            while self.match(TokenType.COMMA):
                imports.append(self.consume(TokenType.IDENTIFIER, "Expected identifier after ','").literal)
        
        self.consume(TokenType.SEMICOLON, "Expected ';' after package statement")
        return PackageStatement(path, imports)
    
    def var_declaration(self, access_modifier: AccessModifier = AccessModifier.PRIVATE) -> VarStatement:
        """Parse variable declaration"""
        name = self.consume(TokenType.IDENTIFIER, "Expected variable name").literal
        
        initializer = None
        if self.match(TokenType.ASSIGN):
            initializer = self.expression()
        
        self.consume(TokenType.SEMICOLON, "Expected ';' after variable declaration")
        return VarStatement(name, initializer, access_modifier)
    
    def function_declaration(self, access_modifier: AccessModifier = AccessModifier.PRIVATE) -> FunctionStatement:
        """Parse function declaration with optional variadic parameter using 'args**' syntax"""
        name = self.consume(TokenType.IDENTIFIER, "Expected function name").literal
        
        self.consume(TokenType.LEFT_PAREN, "Expected '(' after function name")
        params = []
        variadic_param = None
        if not self.check(TokenType.RIGHT_PAREN):
            # First parameter
            ident = self.consume(TokenType.IDENTIFIER, "Expected parameter name")
            param_name = ident.literal
            if self.match(TokenType.POWER):  # '**' for variadic
                variadic_param = param_name
            else:
                params.append(param_name)
            
            # Subsequent parameters
            while self.match(TokenType.COMMA):
                if variadic_param is not None:
                    raise ParseError("Variadic parameter must be the last parameter", self.peek().line, self.peek().column)
                ident = self.consume(TokenType.IDENTIFIER, "Expected parameter name")
                param_name = ident.literal
                if self.match(TokenType.POWER):
                    variadic_param = param_name
                else:
                    params.append(param_name)
        
        self.consume(TokenType.RIGHT_PAREN, "Expected ')' after parameters")
        
        # Skip newlines before function body
        while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
            pass
        
        body = []
        while not self.check(TokenType.END) and not self.is_at_end():
            # Skip whitespace in function body
            if self.check(TokenType.NEWLINE) or self.check(TokenType.TAB):
                self.advance()
                continue
            
            stmt = self.declaration()
            if stmt:
                body.append(stmt)
        
        self.consume(TokenType.END, "Expected 'end' after function body")
        return FunctionStatement(name, params, body, access_modifier, variadic_param)
    
    def class_declaration(self, access_modifier: AccessModifier = AccessModifier.PRIVATE) -> ClassStatement:
        """Parse class declaration"""
        name = self.consume(TokenType.IDENTIFIER, "Expected class name").literal
        
        # Optional constructor parameters - skip for now, handle in init method
        if self.match(TokenType.LEFT_PAREN):
            self.consume(TokenType.RIGHT_PAREN, "Expected ')' after class name")
        
        # Skip newlines before class body
        while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
            pass
        
        methods = []
        constructor = None
        
        while not self.check(TokenType.END) and not self.is_at_end():
            if self.check(TokenType.NEWLINE) or self.check(TokenType.TAB):
                self.advance()
                continue
            
            if self.match(TokenType.FUNC):
                # Handle init method specially
                if self.check(TokenType.INIT):
                    self.advance()  # consume INIT token
                    method_name = "init"
                else:
                    method_name = self.consume(TokenType.IDENTIFIER, "Expected method name").literal
                
                # Parse method parameters and body (support variadic)
                self.consume(TokenType.LEFT_PAREN, "Expected '(' after method name")
                params = []
                variadic_param = None
                if not self.check(TokenType.RIGHT_PAREN):
                    ident = self.consume(TokenType.IDENTIFIER, "Expected parameter name")
                    param_name = ident.literal
                    if self.match(TokenType.POWER):
                        variadic_param = param_name
                    else:
                        params.append(param_name)
                    while self.match(TokenType.COMMA):
                        if variadic_param is not None:
                            raise ParseError("Variadic parameter must be the last parameter", self.peek().line, self.peek().column)
                        ident = self.consume(TokenType.IDENTIFIER, "Expected parameter name")
                        param_name = ident.literal
                        if self.match(TokenType.POWER):
                            variadic_param = param_name
                        else:
                            params.append(param_name)
                self.consume(TokenType.RIGHT_PAREN, "Expected ')' after parameters")
                
                
                # Skip newlines before method body
                while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
                    pass
                
                body = []
                while not self.check(TokenType.END) and not self.is_at_end():
                    if self.check(TokenType.NEWLINE) or self.check(TokenType.TAB):
                        self.advance()
                        continue
                    
                    stmt = self.declaration()
                    if stmt:
                        body.append(stmt)
                
                self.consume(TokenType.END, "Expected 'end' after method body")
                
                # Create method statement
                method = FunctionStatement(method_name, params, body, AccessModifier.PUBLIC, variadic_param)
                
                if method.name == "init":
                    constructor = method
                else:
                    methods.append(method)
            else:
                raise ParseError("Expected method declaration in class body", 
                               self.peek().line, self.peek().column)
        
        self.consume(TokenType.END, "Expected 'end' after class body")
        return ClassStatement(name, methods, constructor, access_modifier)
    
    def statement(self) -> Optional[Statement]:
        """Parse statements"""
        if self.match(TokenType.IF):
            return self.if_statement()
        if self.match(TokenType.WHILE):
            return self.while_statement()
        if self.match(TokenType.FOR):
            return self.for_statement()
        if self.match(TokenType.RETURN):
            return self.return_statement()
        if self.match(TokenType.BREAK):
            return self.break_statement()
        if self.match(TokenType.CONTINUE):
            return self.continue_statement()
        if self.match(TokenType.TRY):
            return self.try_statement()
        if self.match(TokenType.SWITCH):
            return self.switch_statement()
        
        return self.expression_statement()
    
    def if_statement(self) -> IfStatement:
        """Parse if statement"""
        self.consume(TokenType.LEFT_PAREN, "Expected '(' after 'if'")
        condition = self.expression()
        self.consume(TokenType.RIGHT_PAREN, "Expected ')' after if condition")
        
        # Skip newlines before body
        while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
            pass
        
        then_branch = self.statement_block_until([TokenType.ELIF, TokenType.ELSE, TokenType.END])
        
        elif_branches = []
        while self.match(TokenType.ELIF):
            self.consume(TokenType.LEFT_PAREN, "Expected '(' after 'elif'")
            elif_condition = self.expression()
            self.consume(TokenType.RIGHT_PAREN, "Expected ')' after elif condition")
            
            while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
                pass
            
            elif_body = self.statement_block_until([TokenType.ELIF, TokenType.ELSE, TokenType.END])
            elif_branches.append(ElifBranch(elif_condition, elif_body))
        
        else_branch = None
        if self.match(TokenType.ELSE):
            while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
                pass
            else_branch = self.statement_block_until([TokenType.END])
        
        self.consume(TokenType.END, "Expected 'end' after if statement")
        return IfStatement(condition, then_branch, else_branch, elif_branches)
    
    def statement_block_until(self, stop_tokens: List[TokenType]) -> BlockStatement:
        """Parse a block of statements until one of the stop tokens"""
        statements = []
        while not self.check_any(stop_tokens) and not self.is_at_end():
            if self.check(TokenType.NEWLINE) or self.check(TokenType.TAB):
                self.advance()
                continue
            
            stmt = self.declaration()
            if stmt:
                statements.append(stmt)
        
        return BlockStatement(statements)
    
    def while_statement(self) -> WhileStatement:
        """Parse while loop"""
        self.consume(TokenType.LEFT_PAREN, "Expected '(' after 'while'")
        condition = self.expression()
        self.consume(TokenType.RIGHT_PAREN, "Expected ')' after while condition")
        
        while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
            pass
        
        body = self.statement_block_until([TokenType.END])
        self.consume(TokenType.END, "Expected 'end' after while body")
        
        return WhileStatement(condition, body)
    
    def for_statement(self) -> ForStatement:
        """Parse for loop"""
        variable = self.consume(TokenType.IDENTIFIER, "Expected variable name after 'for'").literal
        self.consume(TokenType.IN, "Expected 'in' after for variable")
        iterable = self.expression()
        
        while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
            pass
        
        body = self.statement_block_until([TokenType.END])
        self.consume(TokenType.END, "Expected 'end' after for body")
        
        return ForStatement(variable, iterable, body)
    
    def return_statement(self) -> ReturnStatement:
        """Parse return statement"""
        value = None
        if not self.check(TokenType.SEMICOLON) and not self.check(TokenType.NEWLINE):
            value = self.expression()
        
        self.consume(TokenType.SEMICOLON, "Expected ';' after return value")
        return ReturnStatement(value)
    
    def break_statement(self) -> BreakStatement:
        """Parse break statement"""
        self.consume(TokenType.SEMICOLON, "Expected ';' after 'break'")
        return BreakStatement()
    
    def continue_statement(self) -> ContinueStatement:
        """Parse continue statement"""
        self.consume(TokenType.SEMICOLON, "Expected ';' after 'continue'")
        return ContinueStatement()
    
    def try_statement(self) -> TryStatement:
        """Parse try-catch-finally statement"""
        # Skip newlines before try body
        while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
            pass
        
        try_body = []
        while not self.check(TokenType.CATCH) and not self.check(TokenType.FINALLY) and not self.check(TokenType.END) and not self.is_at_end():
            if self.check(TokenType.NEWLINE) or self.check(TokenType.TAB):
                self.advance()
                continue
            
            stmt = self.declaration()
            if stmt:
                try_body.append(stmt)
        
        catch_clauses = []
        while self.match(TokenType.CATCH):
            variable = None
            if self.match(TokenType.LEFT_PAREN):
                variable = self.consume(TokenType.IDENTIFIER, "Expected variable name in catch clause").literal
                self.consume(TokenType.RIGHT_PAREN, "Expected ')' after catch variable")
            
            # Skip newlines before catch body
            while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
                pass
            
            catch_body = []
            while not self.check(TokenType.CATCH) and not self.check(TokenType.FINALLY) and not self.check(TokenType.END) and not self.is_at_end():
                if self.check(TokenType.NEWLINE) or self.check(TokenType.TAB):
                    self.advance()
                    continue
                
                stmt = self.declaration()
                if stmt:
                    catch_body.append(stmt)
            
            catch_clauses.append(CatchClause(variable, catch_body))
        
        finally_body = None
        if self.match(TokenType.FINALLY):
            # Skip newlines before finally body
            while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
                pass
            
            finally_body = []
            while not self.check(TokenType.END) and not self.is_at_end():
                if self.check(TokenType.NEWLINE) or self.check(TokenType.TAB):
                    self.advance()
                    continue
                
                stmt = self.declaration()
                if stmt:
                    finally_body.append(stmt)
        
        self.consume(TokenType.END, "Expected 'end' after try statement")
        return TryStatement(try_body, catch_clauses, finally_body)
    
    def switch_statement(self) -> SwitchStatement:
        """Parse switch statement"""
        self.consume(TokenType.LEFT_PAREN, "Expected '(' after 'switch'")
        expression = self.expression()
        self.consume(TokenType.RIGHT_PAREN, "Expected ')' after switch expression")
        
        # Skip newlines before cases
        while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
            pass
        
        cases = []
        while (self.check(TokenType.CASE) or self.check(TokenType.DEFAULT)) and not self.is_at_end():
            if self.match(TokenType.CASE):
                values = []
                values.append(self.expression())
                
                while self.match(TokenType.COMMA):
                    values.append(self.expression())
                
                self.consume(TokenType.COLON, "Expected ':' after case value(s)")
                
                # Skip newlines before case body
                while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
                    pass
                
                case_body = []
                while not self.check(TokenType.CASE) and not self.check(TokenType.DEFAULT) and not self.check(TokenType.END) and not self.is_at_end():
                    if self.check(TokenType.NEWLINE) or self.check(TokenType.TAB):
                        self.advance()
                        continue
                    
                    stmt = self.declaration()
                    if stmt:
                        case_body.append(stmt)
                
                cases.append(CaseClause(values, case_body))
            
            elif self.match(TokenType.DEFAULT):
                self.consume(TokenType.COLON, "Expected ':' after 'default'")
                
                # Skip newlines before default body
                while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
                    pass
                
                default_body = []
                while not self.check(TokenType.CASE) and not self.check(TokenType.DEFAULT) and not self.check(TokenType.END) and not self.is_at_end():
                    if self.check(TokenType.NEWLINE) or self.check(TokenType.TAB):
                        self.advance()
                        continue
                    
                    stmt = self.declaration()
                    if stmt:
                        default_body.append(stmt)
                
                cases.append(CaseClause([], default_body, is_default=True))
        
        self.consume(TokenType.END, "Expected 'end' after switch statement")
        return SwitchStatement(expression, cases)
    
    def expression_statement(self) -> ExpressionStatement:
        """Parse expression statement"""
        expr = self.expression()
        self.consume(TokenType.SEMICOLON, "Expected ';' after expression")
        return ExpressionStatement(expr)
    
    def expression(self) -> Expression:
        """Parse expression"""
        return self.assignment()
    
    def assignment(self) -> Expression:
        """Parse assignment expression"""
        expr = self.logical_or()
        
        if self.match(TokenType.ASSIGN):
            value = self.assignment()
            
            if isinstance(expr, IdentifierExpression):
                return AssignmentExpression(expr.name, value)
            elif isinstance(expr, GetExpression):
                return SetExpression(expr.object, expr.name, value)
            elif isinstance(expr, IndexExpression):
                return IndexSetExpression(expr.object, expr.index, value)
            
            prev_token = self.previous()
            if prev_token.span:
                raise ParseError.invalid_assignment_target(prev_token.span)
            else:
                span = Span(0, 0, 1)  # Dummy span
                raise ParseError.invalid_assignment_target(span)
        
        return expr
    
    def logical_or(self) -> Expression:
        """Parse logical OR expression"""
        expr = self.logical_and()
        
        while self.match(TokenType.OR):
            operator = self.previous().lexeme
            right = self.logical_and()
            expr = LogicalExpression(expr, operator, right)
        
        return expr
    
    def logical_and(self) -> Expression:
        """Parse logical AND expression"""
        expr = self.equality()
        
        while self.match(TokenType.AND):
            operator = self.previous().lexeme
            right = self.equality()
            expr = LogicalExpression(expr, operator, right)
        
        return expr
    
    def equality(self) -> Expression:
        """Parse equality expression"""
        expr = self.comparison()
        
        while self.match(TokenType.NOT_EQUAL, TokenType.EQUAL):
            operator = self.previous().lexeme
            right = self.comparison()
            expr = BinaryExpression(expr, operator, right)
        
        return expr
    
    def comparison(self) -> Expression:
        """Parse comparison expression"""
        expr = self.term()
        
        while self.match(TokenType.GREATER, TokenType.GREATER_EQUAL, TokenType.LESS, TokenType.LESS_EQUAL):
            operator = self.previous().lexeme
            right = self.term()
            expr = BinaryExpression(expr, operator, right)
        
        return expr
    
    def term(self) -> Expression:
        """Parse addition and subtraction"""
        expr = self.factor()
        
        while self.match(TokenType.MINUS, TokenType.PLUS):
            operator = self.previous().lexeme
            right = self.factor()
            # Create span covering the entire binary expression
            start_span = getattr(expr, 'span', None) or getattr(self.previous(), 'span', None)
            end_span = getattr(right, 'span', None) or getattr(self.previous(), 'span', None)
            if start_span and end_span:
                combined_span = Span(start_span.file_id, start_span.start, end_span.end)
            else:
                combined_span = start_span or end_span
            expr = BinaryExpression(expr, operator, right, combined_span)
        
        return expr
    
    def factor(self) -> Expression:
        """Parse multiplication, division, and modulo"""
        expr = self.power()
        
        while self.match(TokenType.DIVIDE, TokenType.MULTIPLY, TokenType.MODULO):
            operator = self.previous().lexeme
            right = self.power()
            # Create span covering the entire binary expression
            start_span = getattr(expr, 'span', None) or getattr(self.previous(), 'span', None)
            end_span = getattr(right, 'span', None) or getattr(self.previous(), 'span', None)
            if start_span and end_span:
                combined_span = Span(start_span.file_id, start_span.start, end_span.end)
            else:
                combined_span = start_span or end_span
            expr = BinaryExpression(expr, operator, right, combined_span)
        
        return expr
    
    def power(self) -> Expression:
        """Parse exponentiation (right-associative)"""
        expr = self.unary()
        
        if self.match(TokenType.POWER):
            operator = self.previous().lexeme
            right = self.power()  # Right-associative
            expr = BinaryExpression(expr, operator, right)
        
        return expr
    
    def unary(self) -> Expression:
        """Parse unary expressions"""
        if self.match(TokenType.NOT, TokenType.MINUS):
            operator = self.previous().lexeme
            right = self.unary()
            return UnaryExpression(operator, right)
        
        return self.postfix()
    
    def postfix(self) -> Expression:
        """Parse postfix expressions (++, --)"""
        expr = self.call()
        
        if self.match(TokenType.PLUS_PLUS, TokenType.MINUS_MINUS):
            operator = self.previous().lexeme
            return PostfixExpression(expr, operator)
        
        return expr
    
    def call(self) -> Expression:
        """Parse function calls and property access"""
        expr = self.primary()
        
        while True:
            if self.match(TokenType.LEFT_PAREN):
                expr = self.finish_call(expr)
            elif self.match(TokenType.DOT):
                name = self.consume(TokenType.IDENTIFIER, "Expected property name after '.'").literal
                expr = GetExpression(expr, name)
            elif self.match(TokenType.LEFT_BRACKET):
                index = self.expression()
                self.consume(TokenType.RIGHT_BRACKET, "Expected ']' after array index")
                expr = IndexExpression(expr, index)
            else:
                break
        
        return expr
    
    def finish_call(self, callee: Expression) -> CallExpression:
        """Parse function call arguments"""
        arguments = []
        if not self.check(TokenType.RIGHT_PAREN):
            arguments.append(self.expression())
            while self.match(TokenType.COMMA):
                arguments.append(self.expression())
        
        paren_token = self.consume(TokenType.RIGHT_PAREN, "Expected ')' after arguments")
        # Create span from callee start to closing paren
        start_span = getattr(callee, 'span', None)
        end_span = getattr(paren_token, 'span', None)
        if start_span and end_span:
            call_span = Span(start_span.file_id, start_span.start, end_span.end)
        else:
            call_span = start_span or end_span
        return CallExpression(callee, arguments, call_span)
    
    def primary(self) -> Expression:
        """Parse primary expressions"""
        if self.match(TokenType.TRUE):
            token = self.previous()
            return LiteralExpression(True, token.span)
        
        if self.match(TokenType.FALSE):
            token = self.previous()
            return LiteralExpression(False, token.span)
        
        if self.match(TokenType.NULL):
            token = self.previous()
            return LiteralExpression(None, token.span)
        
        if self.match(TokenType.NUMBER):
            token = self.previous()
            return LiteralExpression(token.literal, token.span)
        
        if self.match(TokenType.STRING):
            token = self.previous()
            return LiteralExpression(token.literal, token.span)
        
        if self.match(TokenType.TEMPLATE_LITERAL):
            token = self.previous()
            return TemplateLiteralExpression(token.literal, token.span)
        
        if self.match(TokenType.THIS):
            return ThisExpression()
        
        if self.match(TokenType.IDENTIFIER):
            token = self.previous()
            return IdentifierExpression(token.literal, token.span)
        
        if self.match(TokenType.LEFT_PAREN):
            expr = self.expression()
            self.consume(TokenType.RIGHT_PAREN, "Expected ')' after expression")
            return expr
        
        if self.match(TokenType.LEFT_BRACKET):
            return self.array_literal()
        
        if self.match(TokenType.LEFT_BRACE):
            return self.dictionary_literal()
        
        current_token = self.peek()
        if current_token.span:
            raise ParseError.expected_expression(current_token.span)
        else:
            span = Span(0, 0, 1)  # Dummy span
            raise ParseError.expected_expression(span)
    
    def array_literal(self) -> ArrayExpression:
        """Parse array literal [1, 2, 3]"""
        elements = []
        if not self.check(TokenType.RIGHT_BRACKET):
            elements.append(self.expression())
            while self.match(TokenType.COMMA):
                elements.append(self.expression())
        
        self.consume(TokenType.RIGHT_BRACKET, "Expected ']' after array elements")
        return ArrayExpression(elements)
    
    def dictionary_literal(self) -> DictionaryExpression:
        """Parse dictionary literal {key: value, key2: value2}
        Supports both JavaScript-like syntax {key: value} and quoted keys {"key": value}
        """
        pairs = []
        
        # Skip initial newlines inside the dictionary
        while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
            pass
            
        if not self.check(TokenType.RIGHT_BRACE):
            key = self.dictionary_key()
            self.consume(TokenType.COLON, "Expected ':' after dictionary key")
            value = self.expression()
            pairs.append((key, value))
            
            # Skip newlines after first pair
            while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
                pass
            
            while self.match(TokenType.COMMA):
                # Skip optional newlines after comma in multiline dictionaries
                while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
                    pass
                
                # Check if we're at the end after trailing comma
                if self.check(TokenType.RIGHT_BRACE):
                    break
                    
                key = self.dictionary_key()
                self.consume(TokenType.COLON, "Expected ':' after dictionary key")
                value = self.expression()
                pairs.append((key, value))
                
                # Skip newlines after each pair
                while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
                    pass
        
        # Skip newlines before closing brace
        while self.match(TokenType.NEWLINE) or self.match(TokenType.TAB):
            pass
            
        self.consume(TokenType.RIGHT_BRACE, "Expected '}' after dictionary elements")
        return DictionaryExpression(pairs)
    
    def dictionary_key(self) -> Expression:
        """Parse dictionary key - either an identifier (JavaScript-style) or an expression"""
        if self.check(TokenType.IDENTIFIER):
            # For bare identifiers, treat them as string literals
            # This enables JavaScript-like syntax: {key: value} instead of {"key": value}
            identifier_name = self.advance().literal
            return LiteralExpression(identifier_name)
        else:
            # For all other cases (strings, expressions, etc.), parse as normal expression
            return self.expression()
    
    # Utility methods
    def match(self, *types: TokenType) -> bool:
        """Check if current token matches any of the given types"""
        for token_type in types:
            if self.check(token_type):
                self.advance()
                return True
        return False
    
    def check(self, token_type: TokenType) -> bool:
        """Check if current token is of given type"""
        if self.is_at_end():
            return False
        return self.peek().type == token_type
    
    def check_any(self, token_types: List[TokenType]) -> bool:
        """Check if current token matches any in the list"""
        return any(self.check(t) for t in token_types)
    
    def advance(self) -> Token:
        """Consume current token and return it"""
        if not self.is_at_end():
            self.current += 1
        return self.previous()
    
    def is_at_end(self) -> bool:
        """Check if we're at the end of tokens"""
        return self.peek().type == TokenType.EOF
    
    def peek(self) -> Token:
        """Return current token without advancing"""
        return self.tokens[self.current]
    
    def previous(self) -> Token:
        """Return previous token"""
        return self.tokens[self.current - 1]
    
    def consume(self, token_type: TokenType, message: str) -> Token:
        """Consume token of expected type or raise error"""
        if self.check(token_type):
            return self.advance()
        
        current_token = self.peek()
        if current_token.span:
            raise ParseError.expected_token(current_token.span, token_type.name.lower(), current_token.lexeme)
        else:
            # Fallback for tokens without spans
            span = Span(0, 0, 1)  # Dummy span
            raise ParseError.expected_token(span, token_type.name.lower(), current_token.lexeme)
    
    def synchronize(self):
        """Recover from parse error by finding next statement"""
        self.advance()
        
        while not self.is_at_end():
            if self.previous().type == TokenType.SEMICOLON:
                return
            
            if self.peek().type in [TokenType.CLASS, TokenType.FUNC, TokenType.VAR,
                                   TokenType.FOR, TokenType.IF, TokenType.WHILE,
                                   TokenType.RETURN]:
                return
            
            self.advance()