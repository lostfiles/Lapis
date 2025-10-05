"""
Abstract Syntax Tree node definitions for the Lapis Programming Language
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Dict
from enum import Enum
from source_map import Span

class AccessModifier(Enum):
    PUBLIC = "public"
    PRIVATE = "private"

# Base classes
class ASTNode(ABC):
    """Base class for all AST nodes"""
    def __init__(self, span: Optional[Span] = None):
        self.span = span

class Expression(ASTNode):
    """Base class for all expressions"""
    def __init__(self, span: Optional[Span] = None):
        super().__init__(span)

class Statement(ASTNode):
    """Base class for all statements"""
    def __init__(self, span: Optional[Span] = None):
        super().__init__(span)

# Expressions
class LiteralExpression(Expression):
    def __init__(self, value: Any, span: Optional[Span] = None):
        super().__init__(span)
        self.value = value

class IdentifierExpression(Expression):
    def __init__(self, name: str, span: Optional[Span] = None):
        super().__init__(span)
        self.name = name

class BinaryExpression(Expression):
    def __init__(self, left: Expression, operator: str, right: Expression, span: Optional[Span] = None):
        super().__init__(span)
        self.left = left
        self.operator = operator
        self.right = right

class UnaryExpression(Expression):
    def __init__(self, operator: str, operand: Expression):
        self.operator = operator
        self.operand = operand

class CallExpression(Expression):
    def __init__(self, callee: Expression, arguments: List[Expression], span: Optional[Span] = None):
        super().__init__(span)
        self.callee = callee
        self.arguments = arguments

class GetExpression(Expression):
    """For accessing object properties (obj.prop)"""
    def __init__(self, object: Expression, name: str):
        self.object = object
        self.name = name

class SetExpression(Expression):
    """For setting object properties (obj.prop = value)"""
    def __init__(self, object: Expression, name: str, value: Expression):
        self.object = object
        self.name = name
        self.value = value

class IndexExpression(Expression):
    """For array/dictionary access (arr[index])"""
    def __init__(self, object: Expression, index: Expression):
        self.object = object
        self.index = index

class IndexSetExpression(Expression):
    """For setting array/dictionary values (arr[index] = value)"""
    def __init__(self, object: Expression, index: Expression, value: Expression):
        self.object = object
        self.index = index
        self.value = value

class ArrayExpression(Expression):
    """Array literal [1, 2, 3]"""
    def __init__(self, elements: List[Expression]):
        self.elements = elements

class DictionaryExpression(Expression):
    """Dictionary literal {key: value, key2: value2}"""
    def __init__(self, pairs: List[tuple]):  # List of (key_expr, value_expr) tuples
        self.pairs = pairs

class AssignmentExpression(Expression):
    def __init__(self, name: str, value: Expression):
        self.name = name
        self.value = value

class LogicalExpression(Expression):
    def __init__(self, left: Expression, operator: str, right: Expression):
        self.left = left
        self.operator = operator
        self.right = right

class ThisExpression(Expression):
    """'this' keyword for accessing current object"""
    pass

class PostfixExpression(Expression):
    """For i++ and i--"""
    def __init__(self, operand: Expression, operator: str):
        self.operand = operand
        self.operator = operator

class TemplateLiteralExpression(Expression):
    """Template literal with {variable} interpolation"""
    def __init__(self, parts: list, span: Optional[Span] = None):
        super().__init__(span)
        self.parts = parts  # List of (text, variable_name) tuples

# Statements
class ExpressionStatement(Statement):
    def __init__(self, expression: Expression):
        self.expression = expression

class VarStatement(Statement):
    def __init__(self, name: str, initializer: Optional[Expression], 
                 access_modifier: AccessModifier = AccessModifier.PRIVATE):
        self.name = name
        self.initializer = initializer
        self.access_modifier = access_modifier

class BlockStatement(Statement):
    def __init__(self, statements: List[Statement]):
        self.statements = statements

class IfStatement(Statement):
    def __init__(self, condition: Expression, then_branch: Statement, 
                 else_branch: Optional[Statement] = None, elif_branches: List = None):
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch
        self.elif_branches = elif_branches or []

class ElifBranch:
    def __init__(self, condition: Expression, body: Statement):
        self.condition = condition
        self.body = body

class WhileStatement(Statement):
    def __init__(self, condition: Expression, body: Statement):
        self.condition = condition
        self.body = body

class ForStatement(Statement):
    def __init__(self, variable: str, iterable: Expression, body: Statement):
        self.variable = variable
        self.iterable = iterable
        self.body = body

class ReturnStatement(Statement):
    def __init__(self, value: Optional[Expression]):
        self.value = value

class FunctionStatement(Statement):
    def __init__(self, name: str, params: List[str], body: List[Statement], 
                 access_modifier: AccessModifier = AccessModifier.PRIVATE,
                 variadic_param: Optional[str] = None):
        self.name = name
        self.params = params
        self.body = body
        self.access_modifier = access_modifier
        self.variadic_param = variadic_param

class ClassStatement(Statement):
    def __init__(self, name: str, methods: List[FunctionStatement], 
                 constructor: Optional[FunctionStatement] = None,
                 access_modifier: AccessModifier = AccessModifier.PRIVATE):
        self.name = name
        self.methods = methods
        self.constructor = constructor
        self.access_modifier = access_modifier

class PackageStatement(Statement):
    """Import statement: package "./file.lapis" use identifier; or package "./file.lapis"; for all"""
    def __init__(self, path: str, imports: Optional[List[str]]):
        self.path = path
        self.imports = imports  # None means import all public symbols

class BreakStatement(Statement):
    """Break statement for loops"""
    def __init__(self, span: Optional[Span] = None):
        super().__init__(span)

class ContinueStatement(Statement):
    """Continue statement for loops"""
    def __init__(self, span: Optional[Span] = None):
        super().__init__(span)

class CatchClause:
    """Catch clause for try-catch statements"""
    def __init__(self, variable: Optional[str], body: List[Statement]):
        self.variable = variable  # Variable to bind the exception to
        self.body = body

class TryStatement(Statement):
    """Try-catch-finally statement"""
    def __init__(self, try_body: List[Statement], catch_clauses: List[CatchClause] = None, 
                 finally_body: Optional[List[Statement]] = None, span: Optional[Span] = None):
        super().__init__(span)
        self.try_body = try_body
        self.catch_clauses = catch_clauses or []
        self.finally_body = finally_body

class CaseClause:
    """Case clause for switch statements"""
    def __init__(self, values: List[Expression], body: List[Statement], is_default: bool = False):
        self.values = values  # List of values to match (empty for default)
        self.body = body
        self.is_default = is_default

class SwitchStatement(Statement):
    """Switch statement with cases"""
    def __init__(self, expression: Expression, cases: List[CaseClause], span: Optional[Span] = None):
        super().__init__(span)
        self.expression = expression
        self.cases = cases

class Program(ASTNode):
    """Root node containing all statements"""
    def __init__(self, statements: List[Statement]):
        self.statements = statements