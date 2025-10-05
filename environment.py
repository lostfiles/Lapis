"""
Environment and scoping system for the Lapis Programming Language
"""

from typing import Any, Dict, Optional
from ast_nodes import AccessModifier
from errors import RuntimeError, AccessError

class Variable:
    """Represents a variable with access control"""
    def __init__(self, value: Any, access_modifier: AccessModifier = AccessModifier.PRIVATE):
        self.value = value
        self.access_modifier = access_modifier
    
    def can_access(self, from_external_file: bool = False) -> bool:
        """Check if variable can be accessed based on context"""
        if self.access_modifier == AccessModifier.PUBLIC:
            return True
        return not from_external_file

class Environment:
    """Environment for variable storage and scoping"""
    
    def __init__(self, enclosing: Optional['Environment'] = None):
        self.enclosing = enclosing
        self.values: Dict[str, Variable] = {}
    
    def define(self, name: str, value: Any, access_modifier: AccessModifier = AccessModifier.PRIVATE):
        """Define a new variable in this environment"""
        self.values[name] = Variable(value, access_modifier)
    
    def get(self, name: str, from_external_file: bool = False) -> Any:
        """Get variable value, checking access control"""
        if name in self.values:
            var = self.values[name]
            if var.can_access(from_external_file):
                return var.value
            else:
                from source_map import Span
                dummy_span = Span(1, 0, 1)
                raise AccessError.from_simple(
                    "LAP4002", f"Cannot access private variable '{name}' from external file", dummy_span
                )
        
        if self.enclosing is not None:
            return self.enclosing.get(name, from_external_file)
        
        from source_map import Span
        dummy_span = Span(1, 0, 1)
        raise RuntimeError.from_simple(
            "LAP4001", f"Undefined variable '{name}'", dummy_span
        )
    
    def assign(self, name: str, value: Any, from_external_file: bool = False):
        """Assign to existing variable, checking access control"""
        if name in self.values:
            var = self.values[name]
            if var.can_access(from_external_file):
                var.value = value
                return
            else:
                from source_map import Span
                dummy_span = Span(1, 0, 1)
                raise AccessError.from_simple(
                    "LAP4002", f"Cannot assign to private variable '{name}' from external file", dummy_span
                )
        
        if self.enclosing is not None:
            self.enclosing.assign(name, value, from_external_file)
            return
        
        from source_map import Span
        dummy_span = Span(1, 0, 1)
        raise RuntimeError.from_simple(
            "LAP4001", f"Undefined variable '{name}'", dummy_span
        )
    
    def get_all_public(self) -> Dict[str, Any]:
        """Get all public variables (for imports)"""
        result = {}
        for name, var in self.values.items():
            if var.access_modifier == AccessModifier.PUBLIC:
                result[name] = var.value
        return result

class CallableFunction:
    """Base class for callable functions and methods"""
    
    def __init__(self, declaration, closure: Environment, access_modifier: AccessModifier = AccessModifier.PRIVATE):
        self.declaration = declaration
        self.closure = closure
        self.access_modifier = access_modifier
    
    def call(self, interpreter, arguments: list) -> Any:
        raise NotImplementedError
    
    def arity(self) -> int:
        """Return number of parameters this function expects"""
        return -1 if getattr(self.declaration, 'variadic_param', None) else len(self.declaration.params)
    
    def can_access(self, from_external_file: bool = False) -> bool:
        """Check if function can be accessed based on context"""
        if self.access_modifier == AccessModifier.PUBLIC:
            return True
        return not from_external_file

class LapisFunction(CallableFunction):
    """User-defined function"""
    
    def __init__(self, declaration, closure: Environment, is_initializer: bool = False):
        super().__init__(declaration, closure, declaration.access_modifier)
        self.is_initializer = is_initializer
    
    def call(self, interpreter, arguments: list) -> Any:
        from interpreter import ReturnException  # Import here to avoid circular imports
        
        # Create new environment for function execution
        environment = Environment(self.closure)
        
        # Bind parameters
        fixed_count = len(self.declaration.params)
        for i, param in enumerate(self.declaration.params):
            environment.define(param, arguments[i] if i < len(arguments) else None)
        # Bind variadic if present
        variadic = getattr(self.declaration, 'variadic_param', None)
        if variadic:
            rest = arguments[fixed_count:] if len(arguments) > fixed_count else []
            environment.define(variadic, rest)
        
        try:
            interpreter.execute_block(self.declaration.body, environment)
        except ReturnException as return_value:
            if self.is_initializer:
                return self.closure.get("this")
            return return_value.value
        
        # If it's an initializer, always return 'this'
        if self.is_initializer:
            return self.closure.get("this")
        
        return None

class LapisClass:
    """User-defined class"""
    
    def __init__(self, name: str, methods: Dict[str, LapisFunction], 
                 access_modifier: AccessModifier = AccessModifier.PRIVATE):
        self.name = name
        self.methods = methods
        self.access_modifier = access_modifier
    
    def call(self, interpreter, arguments: list) -> 'LapisInstance':
        """Create new instance of the class"""
        instance = LapisInstance(self)
        
        # Call initializer if it exists
        initializer = self.find_method("init")
        if initializer is not None:
            initializer.bind(instance).call(interpreter, arguments)
        
        return instance
    
    def find_method(self, name: str) -> Optional[LapisFunction]:
        """Find method by name"""
        return self.methods.get(name)
    
    def arity(self) -> int:
        """Return number of parameters for constructor"""
        initializer = self.find_method("init")
        if initializer is None:
            return 0
        return initializer.arity()
    
    def can_access(self, from_external_file: bool = False) -> bool:
        """Check if class can be accessed based on context"""
        if self.access_modifier == AccessModifier.PUBLIC:
            return True
        return not from_external_file

class LapisInstance:
    """Instance of a Lapis class"""
    
    def __init__(self, klass: LapisClass):
        self.klass = klass
        self.fields: Dict[str, Any] = {}
    
    def get(self, name: str) -> Any:
        """Get property or method"""
        if name in self.fields:
            return self.fields[name]
        
        method = self.klass.find_method(name)
        if method is not None:
            return method.bind(self)
        
        from source_map import Span
        dummy_span = Span(1, 0, 1)
        raise RuntimeError.from_simple(
            "LAP3005", f"Undefined property '{name}'", dummy_span
        )
    
    def set(self, name: str, value: Any):
        """Set property"""
        self.fields[name] = value

class BoundMethod(CallableFunction):
    """Method bound to an instance"""
    
    def __init__(self, instance: LapisInstance, method: LapisFunction):
        super().__init__(method.declaration, method.closure, method.access_modifier)
        self.instance = instance
        self.method = method
    
    def call(self, interpreter, arguments: list) -> Any:
        # Create environment with 'this' bound to the instance
        environment = Environment(self.method.closure)
        environment.define("this", self.instance)
        
        # Bind parameters
        for i, param in enumerate(self.method.declaration.params):
            environment.define(param, arguments[i] if i < len(arguments) else None)
        
        try:
            interpreter.execute_block(self.method.declaration.body, environment)
        except:
            from interpreter import ReturnException
            pass
        
        try:
            interpreter.execute_block(self.method.declaration.body, environment)
        except Exception as e:
            if hasattr(e, 'value'):  # ReturnException
                if self.method.is_initializer:
                    return self.instance
                return e.value
            raise e
        
        if self.method.is_initializer:
            return self.instance
        return None
    
    def arity(self) -> int:
        return self.method.arity()

# Extend LapisFunction with bind method
def bind_method(self, instance: LapisInstance) -> BoundMethod:
    return BoundMethod(instance, self)

LapisFunction.bind = bind_method