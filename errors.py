"""
Comprehensive error handling for the Lapis Programming Language
Includes diagnostics, error codes, and pretty formatting
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Any, Dict
from source_map import Span, get_source_map, SourceFile, Position

class Severity(Enum):
    """Error severity levels"""
    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"
    HELP = "help"

@dataclass
class LabeledSpan:
    """A span with an optional label"""
    span: Span
    label: Optional[str] = None
    is_primary: bool = False
    style: str = "secondary"  # "primary" or "secondary"
    
    def __post_init__(self):
        if self.is_primary:
            self.style = "primary"

@dataclass
class RelatedDiagnostic:
    """Related diagnostic information"""
    span: Span
    message: str

class ErrorCode:
    """Error code constants"""
    # Lexical errors (LAP1xxx)
    UNEXPECTED_CHARACTER = "LAP1001"
    UNTERMINATED_STRING = "LAP1002"
    INVALID_NUMBER = "LAP1003"
    
    # Parser errors (LAP2xxx)
    UNEXPECTED_TOKEN = "LAP2001"
    EXPECTED_TOKEN = "LAP2002"
    EXPECTED_EXPRESSION = "LAP2003"
    EXPECTED_STATEMENT = "LAP2004"
    INVALID_ASSIGNMENT_TARGET = "LAP2005"
    
    # Type errors (LAP3xxx)
    TYPE_MISMATCH_BINARY = "LAP3001"
    TYPE_MISMATCH_UNARY = "LAP3002"
    CANNOT_CALL = "LAP3003"
    WRONG_ARITY = "LAP3004"
    NO_PROPERTY = "LAP3005"
    NOT_INDEXABLE = "LAP3006"
    INDEX_OUT_OF_BOUNDS = "LAP3007"
    DIVISION_BY_ZERO = "LAP3008"
    
    # Runtime errors (LAP4xxx)
    UNDEFINED_VARIABLE = "LAP4001"
    ACCESS_VIOLATION = "LAP4002"
    IMPORT_ERROR = "LAP4003"
    FILE_ERROR = "LAP4004"
    
    # Internal errors (LAP9xxx)
    INTERNAL_ERROR = "LAP9001"

@dataclass
class Diagnostic:
    """Comprehensive diagnostic information"""
    code: str
    severity: Severity
    message: str
    labels: List[LabeledSpan]
    notes: List[str] = None
    help: Optional[str] = None
    related: List[RelatedDiagnostic] = None
    data: Dict[str, Any] = None
    
    def to_json(self):
        """Convert diagnostic to JSON-serializable format"""
        return {
            'code': self.code,
            'severity': self.severity.value,
            'message': self.message,
            'labels': [{
                'span': {'start': label.span.start, 'end': label.span.end, 'file_id': label.span.file_id},
                'label': label.label,
                'is_primary': label.is_primary,
                'style': label.style
            } for label in self.labels],
            'notes': self.notes or [],
            'help': self.help,
            'data': self.data or {}
        }
    
    def __post_init__(self):
        if self.notes is None:
            self.notes = []
        if self.related is None:
            self.related = []
        if self.data is None:
            self.data = {}
        
        # Ensure exactly one primary label
        primary_count = sum(1 for label in self.labels if label.is_primary)
        if primary_count == 0 and self.labels:
            self.labels[0].is_primary = True
            self.labels[0].style = "primary"
        elif primary_count > 1:
            # Keep only the first primary
            found_primary = False
            for label in self.labels:
                if label.is_primary and found_primary:
                    label.is_primary = False
                    label.style = "secondary"
                elif label.is_primary:
                    found_primary = True
    
    def primary_span(self) -> Optional[Span]:
        """Get the primary span for this diagnostic"""
        for label in self.labels:
            if label.is_primary:
                return label.span
        return None

class LapisError(Exception):
    """Base exception class for all Lapis errors with diagnostics support"""
    
    def __init__(self, diagnostic: Diagnostic):
        self.diagnostic = diagnostic
        super().__init__(self._format_simple_message())
    
    def _format_simple_message(self) -> str:
        """Format a simple message for the exception"""
        primary_span = self.diagnostic.primary_span()
        if primary_span:
            try:
                source_map = get_source_map()
                source_file, start_pos, _ = source_map.resolve_span(primary_span)
                file_name = source_file.path.split('/')[-1]  # Just filename
                return f"{self.diagnostic.severity.value.title()} [{self.diagnostic.code}]: {self.diagnostic.message} at {file_name}:{start_pos.line}:{start_pos.column}"
            except:
                return f"{self.diagnostic.severity.value.title()} [{self.diagnostic.code}]: {self.diagnostic.message}"
        return f"{self.diagnostic.severity.value.title()} [{self.diagnostic.code}]: {self.diagnostic.message}"
    
    @classmethod
    def from_simple(cls, code: str, message: str, span: Optional[Span] = None, 
                   severity: Severity = Severity.ERROR, help_text: Optional[str] = None):
        """Create error from simple parameters"""
        labels = []
        if span:
            labels.append(LabeledSpan(span, message, is_primary=True))
        
        diagnostic = Diagnostic(
            code=code,
            severity=severity,
            message=message,
            labels=labels,
            help=help_text
        )
        return cls(diagnostic)

class LexError(LapisError):
    """Lexical analysis errors"""
    
    @classmethod
    def unexpected_character(cls, span: Span, char: str):
        diagnostic = Diagnostic(
            code=ErrorCode.UNEXPECTED_CHARACTER,
            severity=Severity.ERROR,
            message=f"unexpected character '{char}'",
            labels=[LabeledSpan(span, f"unexpected character '{char}'", is_primary=True)],
            help="check for typos or unsupported characters"
        )
        return cls(diagnostic)
    
    @classmethod
    def unterminated_string(cls, span: Span):
        diagnostic = Diagnostic(
            code=ErrorCode.UNTERMINATED_STRING,
            severity=Severity.ERROR,
            message="unterminated string literal",
            labels=[LabeledSpan(span, "string starts here", is_primary=True)],
            help="add closing quote to terminate the string"
        )
        return cls(diagnostic)

class ParseError(LapisError):
    """Parser errors"""
    
    @classmethod
    def expected_token(cls, span: Span, expected: str, found: str):
        diagnostic = Diagnostic(
            code=ErrorCode.EXPECTED_TOKEN,
            severity=Severity.ERROR,
            message=f"expected '{expected}', found '{found}'",
            labels=[LabeledSpan(span, f"expected '{expected}' here", is_primary=True)],
            help=f"add '{expected}' before this token"
        )
        return cls(diagnostic)
    
    @classmethod
    def expected_expression(cls, span: Span):
        diagnostic = Diagnostic(
            code=ErrorCode.EXPECTED_EXPRESSION,
            severity=Severity.ERROR,
            message="expected expression",
            labels=[LabeledSpan(span, "expected expression here", is_primary=True)],
            help="add a valid expression (variable, literal, or function call)"
        )
        return cls(diagnostic)
    
    @classmethod
    def invalid_assignment_target(cls, span: Span):
        diagnostic = Diagnostic(
            code=ErrorCode.INVALID_ASSIGNMENT_TARGET,
            severity=Severity.ERROR,
            message="invalid assignment target",
            labels=[LabeledSpan(span, "cannot assign to this expression", is_primary=True)],
            help="only variables, properties, and array elements can be assigned to"
        )
        return cls(diagnostic)

class TypeError(LapisError):
    """Type-related errors"""
    
    @classmethod
    def cannot_add_types(cls, expr_span: Span, left_span: Span, right_span: Span, 
                        left_type: str, right_type: str):
        message = f"cannot add {left_type} and {right_type}"
        labels = [
            LabeledSpan(expr_span, message, is_primary=True),
            LabeledSpan(left_span, f"left operand has type {left_type}"),
            LabeledSpan(right_span, f"right operand has type {right_type}")
        ]
        
        # Provide helpful suggestions
        help_text = None
        if left_type == "number" and right_type == "string":
            help_text = "convert the number to a string with string(x) or use string concatenation"
        elif left_type == "string" and right_type == "number":
            help_text = "convert the string to a number with number(x) or use string concatenation"
        elif left_type in ["number", "string"] and right_type in ["number", "string"]:
            help_text = "ensure both operands are the same type (both numbers or both strings)"
        else:
            help_text = "the + operator is only defined for numbers and strings"
        
        diagnostic = Diagnostic(
            code=ErrorCode.TYPE_MISMATCH_BINARY,
            severity=Severity.ERROR,
            message=message,
            labels=labels,
            help=help_text
        )
        return cls(diagnostic)
    
    @classmethod
    def invalid_binary_operation(cls, expr_span: Span, left_span: Span, right_span: Span,
                               operator: str, left_type: str, right_type: str):
        message = f"cannot use operator '{operator}' with {left_type} and {right_type}"
        labels = [
            LabeledSpan(expr_span, message, is_primary=True),
            LabeledSpan(left_span, f"left operand has type {left_type}"),
            LabeledSpan(right_span, f"right operand has type {right_type}")
        ]
        
        help_text = f"operator '{operator}' requires numeric operands"
        if operator in ["==", "!="]:
            help_text = "equality operators work with any types"
        elif operator in ["<", ">", "<=", ">="]:
            help_text = "comparison operators require numeric operands"
        
        diagnostic = Diagnostic(
            code=ErrorCode.TYPE_MISMATCH_BINARY,
            severity=Severity.ERROR,
            message=message,
            labels=labels,
            help=help_text
        )
        return cls(diagnostic)

class RuntimeError(LapisError):
    """Runtime errors"""
    
    @classmethod
    def undefined_variable(cls, span: Span, name: str):
        diagnostic = Diagnostic(
            code=ErrorCode.UNDEFINED_VARIABLE,
            severity=Severity.ERROR,
            message=f"undefined variable '{name}'",
            labels=[LabeledSpan(span, f"'{name}' not found", is_primary=True)],
            help=f"declare the variable with 'var {name} = value;' before using it"
        )
        return cls(diagnostic)
    
    @classmethod
    def division_by_zero(cls, span: Span):
        diagnostic = Diagnostic(
            code=ErrorCode.DIVISION_BY_ZERO,
            severity=Severity.ERROR,
            message="division by zero",
            labels=[LabeledSpan(span, "division by zero", is_primary=True)],
            help="ensure the denominator is not zero before dividing"
        )
        return cls(diagnostic)

class ImportError(LapisError):
    """Import-related errors"""
    pass

class AccessError(LapisError):
    """Access control errors (public/private)"""
    pass
