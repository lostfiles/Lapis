"""
Main interpreter for the Lapis Programming Language
"""

import os
import sys
from typing import Any, List, Dict
from ast_nodes import *
from environment import Environment, LapisFunction, LapisClass, LapisInstance, BoundMethod
from errors import LapisError, RuntimeError, AccessError, ImportError, TypeError
from lexer import Lexer
from parser import Parser

class ReturnException(Exception):
    """Exception used for return statement control flow"""
    def __init__(self, value):
        self.value = value

class BreakException(Exception):
    """Exception used for break statement control flow"""
    pass

class ContinueException(Exception):
    """Exception used for continue statement control flow"""
    pass

class LapisRuntimeException(Exception):
    """Exception used for try-catch error handling"""
    def __init__(self, message: str, original_exception=None):
        self.message = message
        self.original_exception = original_exception
        super().__init__(message)

class Interpreter:
    """Main interpreter that executes the AST"""
    
    def __init__(self):
        self.globals = Environment()
        self.environment = self.globals
        self.locals = {}
        
        # Built-in functions
        self.define_built_ins()
        
        # Keep track of imported files to avoid circular imports
        self.imported_files = set()
    
    def define_built_ins(self):
        """Define built-in functions"""
        import math
        
        # Math utilities
        class MathModule:
            def __init__(self):
                pass
        
        class MathSqrtFunction:
            def arity(self):
                return 1
            
            def call(self, interpreter, arguments):
                x = arguments[0]
                if not isinstance(x, (int, float)):
                    raise RuntimeError("Math.sqrt() requires a number")
                if x < 0:
                    raise RuntimeError("Math.sqrt() argument must be non-negative")
                return math.sqrt(x)
        
        class MathAbsFunction:
            def arity(self):
                return 1
            
            def call(self, interpreter, arguments):
                x = arguments[0]
                if not isinstance(x, (int, float)):
                    raise RuntimeError("Math.abs() requires a number")
                return abs(x)
        
        class MathFloorFunction:
            def arity(self):
                return 1
            
            def call(self, interpreter, arguments):
                x = arguments[0]
                if not isinstance(x, (int, float)):
                    raise RuntimeError("Math.floor() requires a number")
                return math.floor(x)
        
        class MathCeilFunction:
            def arity(self):
                return 1
            
            def call(self, interpreter, arguments):
                x = arguments[0]
                if not isinstance(x, (int, float)):
                    raise RuntimeError("Math.ceil() requires a number")
                return math.ceil(x)
        
        # Create Math object with methods
        math_obj = MathModule()
        
        # Add function methods to Math object - we'll use a special LapisMathInstance
        class LapisMathInstance:
            def __init__(self):
                self.functions = {
                    "sqrt": MathSqrtFunction(),
                    "abs": MathAbsFunction(),
                    "floor": MathFloorFunction(),
                    "ceil": MathCeilFunction()
                }
            
            def get(self, name):
                if name in self.functions:
                    return self.functions[name]
                raise RuntimeError(f"Math has no method '{name}'")
        
        # Console Module Functions
        class ConsoleInputFunction:
            def arity(self):
                return -1  # Variable arguments (0 or 1)
            
            def call(self, interpreter, arguments):
                prompt = ""
                if len(arguments) > 0:
                    prompt = str(arguments[0])
                try:
                    return input(prompt)
                except EOFError:
                    return None
                except KeyboardInterrupt:
                    raise RuntimeError("Input interrupted")
        
        class ConsoleInputNumberFunction:
            def arity(self):
                return -1  # Variable arguments (0 or 1)
            
            def call(self, interpreter, arguments):
                prompt = ""
                if len(arguments) > 0:
                    prompt = str(arguments[0])
                try:
                    user_input = input(prompt)
                    # Try to convert to number
                    if '.' in user_input:
                        return float(user_input)
                    else:
                        return int(user_input)
                except ValueError:
                    raise RuntimeError(f"Invalid number input: '{user_input}'")
                except EOFError:
                    return None
                except KeyboardInterrupt:
                    raise RuntimeError("Input interrupted")
        
        class ConsoleErrorFunction:
            def arity(self):
                return 1  # Exactly one argument - the error message
            
            def call(self, interpreter, arguments):
                message = str(arguments[0]) if len(arguments) > 0 else "User error"
                # Create a LapisRuntimeException that can be caught by try-catch
                raise LapisRuntimeException(message)
        
        class NativePyCallFunction:
            """Internal: __lapis_native_py_call(py_module, py_module_func_name, args=[])"""
            def arity(self):
                return -1  # variable: 2 or 3 args
            
            def call(self, interpreter, arguments):
                # Validate arguments count
                if len(arguments) < 2:
                    from source_map import Span
                    dummy_span = Span(1, 0, 1)
                    raise RuntimeError.from_simple(
                        "LAP9001", "__lapis_native_py_call requires at least 2 arguments (module, function)", dummy_span
                    )
                
                py_module = arguments[0]
                func_name = arguments[1]
                py_args = []
                if len(arguments) >= 3:
                    # If third param is a list and only 3 args were provided, treat it as args list
                    if len(arguments) == 3 and isinstance(arguments[2], list):
                        py_args = arguments[2]
                    else:
                        py_args = arguments[2:]
                
                # Validate types
                if not isinstance(py_module, str):
                    from source_map import Span
                    dummy_span = Span(1, 0, 1)
                    raise RuntimeError.from_simple(
                        "LAP9001", "__lapis_native_py_call: py_module must be a string", dummy_span
                    )
                if not isinstance(func_name, str):
                    from source_map import Span
                    dummy_span = Span(1, 0, 1)
                    raise RuntimeError.from_simple(
                        "LAP9001", "__lapis_native_py_call: py_module_func_name must be a string", dummy_span
                    )
                if py_args is None:
                    py_args = []
                if not isinstance(py_args, list):
                    from source_map import Span
                    dummy_span = Span(1, 0, 1)
                    raise RuntimeError.from_simple(
                        "LAP9001", "__lapis_native_py_call: args must be an array (list)", dummy_span
                    )
                
                try:
                    import importlib
                    mod = importlib.import_module(py_module)
                except Exception as e:
                    from source_map import Span
                    dummy_span = Span(1, 0, 1)
                    raise RuntimeError.from_simple(
                        "LAP9001", f"__lapis_native_py_call: cannot import module '{py_module}': {str(e)}", dummy_span
                    )
                
                try:
                    func = getattr(mod, func_name)
                except AttributeError:
                    from source_map import Span
                    dummy_span = Span(1, 0, 1)
                    raise RuntimeError.from_simple(
                        "LAP9001", f"__lapis_native_py_call: module '{py_module}' has no attribute '{func_name}'", dummy_span
                    )
                
                if not callable(func):
                    from source_map import Span
                    dummy_span = Span(1, 0, 1)
                    raise RuntimeError.from_simple(
                        "LAP9001", f"__lapis_native_py_call: '{py_module}.{func_name}' is not callable", dummy_span
                    )
                
                # Call the Python function with provided args
                try:
                    return func(*py_args)
                except Exception as e:
                    # Surface the Python exception as a Lapis runtime error
                    from source_map import Span
                    dummy_span = Span(1, 0, 1)
                    raise RuntimeError.from_simple(
                        "LAP9001", f"__lapis_native_py_call: error calling '{py_module}.{func_name}': {str(e)}", dummy_span
                    )
        
        class ConsolePrintFunction:
            def arity(self):
                return -1  # Variable arguments
            
            def call(self, interpreter, arguments):
                if len(arguments) == 0:
                    print()
                else:
                    outputs = [self.stringify(arg) for arg in arguments]
                    print(' '.join(outputs))
                return None
            
            def stringify(self, obj):
                if obj is None:
                    return "null"
                if isinstance(obj, bool):
                    return "true" if obj else "false"
                if isinstance(obj, str):
                    return obj
                if isinstance(obj, (int, float)):
                    return str(obj)
                if isinstance(obj, list):
                    elements = [self.stringify(elem) for elem in obj]
                    return f"[{', '.join(elements)}]"
                if isinstance(obj, dict):
                    pairs = [f"{self.stringify(k)}: {self.stringify(v)}" for k, v in obj.items()]
                    return f"{{{', '.join(pairs)}}}"
                return str(obj)
        
        # Console module instance
        class LapisConsoleInstance:
            def __init__(self):
                self.functions = {
                    "input": ConsoleInputFunction(),
                    "number": ConsoleInputNumberFunction(),
                    "print": ConsolePrintFunction(),
                    "error": ConsoleErrorFunction()
                }
            
            def get(self, name):
                if name in self.functions:
                    return self.functions[name]
                raise RuntimeError(f"Console has no method '{name}'")
        
        # File Module Functions
        class FileReadFunction:
            def arity(self):
                return 1
            
            def call(self, interpreter, arguments):
                filename = arguments[0]
                if not isinstance(filename, str):
                    raise RuntimeError("File.read() requires a string filename")
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        return f.read()
                except FileNotFoundError:
                    raise RuntimeError(f"File not found: '{filename}'")
                except PermissionError:
                    raise RuntimeError(f"Permission denied: '{filename}'")
                except Exception as e:
                    raise RuntimeError(f"Error reading file '{filename}': {str(e)}")
        
        class FileWriteFunction:
            def arity(self):
                return 2
            
            def call(self, interpreter, arguments):
                filename = arguments[0]
                content = arguments[1]
                if not isinstance(filename, str):
                    raise RuntimeError("File.write() requires a string filename")
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(str(content))
                    return True
                except PermissionError:
                    raise RuntimeError(f"Permission denied: '{filename}'")
                except Exception as e:
                    raise RuntimeError(f"Error writing file '{filename}': {str(e)}")
        
        class FileAppendFunction:
            def arity(self):
                return 2
            
            def call(self, interpreter, arguments):
                filename = arguments[0]
                content = arguments[1]
                if not isinstance(filename, str):
                    raise RuntimeError("File.append() requires a string filename")
                try:
                    with open(filename, 'a', encoding='utf-8') as f:
                        f.write(str(content))
                    return True
                except PermissionError:
                    raise RuntimeError(f"Permission denied: '{filename}'")
                except Exception as e:
                    raise RuntimeError(f"Error appending to file '{filename}': {str(e)}")
        
        class FileExistsFunction:
            def arity(self):
                return 1
            
            def call(self, interpreter, arguments):
                filename = arguments[0]
                if not isinstance(filename, str):
                    raise RuntimeError("File.exists() requires a string filename")
                import os
                return os.path.exists(filename)
        
        class FileDeleteFunction:
            def arity(self):
                return 1
            
            def call(self, interpreter, arguments):
                filename = arguments[0]
                if not isinstance(filename, str):
                    raise RuntimeError("File.delete() requires a string filename")
                try:
                    import os
                    os.remove(filename)
                    return True
                except FileNotFoundError:
                    raise RuntimeError(f"File not found: '{filename}'")
                except PermissionError:
                    raise RuntimeError(f"Permission denied: '{filename}'")
                except Exception as e:
                    raise RuntimeError(f"Error deleting file '{filename}': {str(e)}")
        
        class FileListFunction:
            def arity(self):
                return -1  # Variable arguments (0 or 1)
            
            def call(self, interpreter, arguments):
                directory = "."
                if len(arguments) > 0:
                    directory = arguments[0]
                    if not isinstance(directory, str):
                        raise RuntimeError("File.list() requires a string directory path")
                try:
                    import os
                    return os.listdir(directory)
                except FileNotFoundError:
                    raise RuntimeError(f"Directory not found: '{directory}'")
                except PermissionError:
                    raise RuntimeError(f"Permission denied: '{directory}'")
                except Exception as e:
                    raise RuntimeError(f"Error listing directory '{directory}': {str(e)}")
        
        # File module instance
        class LapisFileInstance:
            def __init__(self):
                self.functions = {
                    "read": FileReadFunction(),
                    "write": FileWriteFunction(),
                    "append": FileAppendFunction(),
                    "exists": FileExistsFunction(),
                    "delete": FileDeleteFunction(),
                    "list": FileListFunction()
                }
            
            def get(self, name):
                if name in self.functions:
                    return self.functions[name]
                raise RuntimeError(f"File has no method '{name}'")
        
        # Define built-in functions and objects
        self.globals.define("Console", LapisConsoleInstance(), AccessModifier.PUBLIC)
        self.globals.define("Math", LapisMathInstance(), AccessModifier.PUBLIC)
        self.globals.define("File", LapisFileInstance(), AccessModifier.PUBLIC)
        
        # Internal native Python call for bootstrapping
        self.globals.define("__lapis_native_py_call", NativePyCallFunction(), AccessModifier.PRIVATE)
    
    def interpret(self, program: Program, filename: str = "<script>"):
        """Interpret a program"""
        try:
            for statement in program.statements:
                self.execute(statement)
        except (BreakException, ContinueException):
            # Break/continue outside of loops should be an error
            from source_map import Span
            dummy_span = Span(1, 0, 1)
            raise RuntimeError.from_simple(
                "LAP9002", "break or continue outside of loop", dummy_span
            )
        except LapisError:
            # Re-raise Lapis errors as-is (these include try-catch handled errors)
            raise
        except Exception as e:
            # Create a proper LapisError for internal Python errors
            from source_map import Span
            dummy_span = Span(1, 0, 1)
            raise RuntimeError.from_simple(
                "LAP9001", f"Runtime error: {str(e)}", dummy_span
            )
    
    def execute(self, stmt: Statement):
        """Execute a statement"""
        return self.visit_statement(stmt)
    
    def visit_statement(self, stmt: Statement):
        """Visit and execute statement based on type"""
        
        if isinstance(stmt, ExpressionStatement):
            return self.evaluate(stmt.expression)
        elif isinstance(stmt, VarStatement):
            return self.execute_var_statement(stmt)
        elif isinstance(stmt, BlockStatement):
            return self.execute_block_statement(stmt)
        elif isinstance(stmt, FunctionStatement):
            return self.execute_function_statement(stmt)
        elif isinstance(stmt, ClassStatement):
            return self.execute_class_statement(stmt)
        elif isinstance(stmt, IfStatement):
            return self.execute_if_statement(stmt)
        elif isinstance(stmt, WhileStatement):
            return self.execute_while_statement(stmt)
        elif isinstance(stmt, ForStatement):
            return self.execute_for_statement(stmt)
        elif isinstance(stmt, ReturnStatement):
            return self.execute_return_statement(stmt)
        elif isinstance(stmt, PackageStatement):
            return self.execute_package_statement(stmt)
        elif isinstance(stmt, BreakStatement):
            return self.execute_break_statement(stmt)
        elif isinstance(stmt, ContinueStatement):
            return self.execute_continue_statement(stmt)
        elif isinstance(stmt, TryStatement):
            return self.execute_try_statement(stmt)
        elif isinstance(stmt, SwitchStatement):
            return self.execute_switch_statement(stmt)
        else:
            raise RuntimeError(f"Unknown statement type: {type(stmt)}")
    
    def execute_var_statement(self, stmt: VarStatement):
        """Execute variable declaration"""
        value = None
        if stmt.initializer is not None:
            value = self.evaluate(stmt.initializer)
        
        self.environment.define(stmt.name, value, stmt.access_modifier)
    
    def execute_block_statement(self, stmt: BlockStatement):
        """Execute block statement"""
        self.execute_block(stmt.statements, Environment(self.environment))
    
    def execute_block(self, statements: List[Statement], environment: Environment):
        """Execute a list of statements in a given environment"""
        previous = self.environment
        try:
            self.environment = environment
            
            for statement in statements:
                self.execute(statement)
        finally:
            self.environment = previous
    
    def execute_function_statement(self, stmt: FunctionStatement):
        """Execute function declaration"""
        function = LapisFunction(stmt, self.environment)
        self.environment.define(stmt.name, function, stmt.access_modifier)
    
    def execute_class_statement(self, stmt: ClassStatement):
        """Execute class declaration"""
        methods = {}
        
        for method in stmt.methods:
            function = LapisFunction(method, self.environment)
            methods[method.name] = function
        
        # Handle constructor
        if stmt.constructor is not None:
            constructor = LapisFunction(stmt.constructor, self.environment, is_initializer=True)
            methods["init"] = constructor
        
        klass = LapisClass(stmt.name, methods, stmt.access_modifier)
        self.environment.define(stmt.name, klass, stmt.access_modifier)
    
    def execute_if_statement(self, stmt: IfStatement):
        """Execute if statement"""
        condition_value = self.evaluate(stmt.condition)
        
        if self.is_truthy(condition_value):
            self.execute(stmt.then_branch)
            return
        
        # Check elif branches
        for elif_branch in stmt.elif_branches:
            elif_condition = self.evaluate(elif_branch.condition)
            if self.is_truthy(elif_condition):
                self.execute(elif_branch.body)
                return
        
        # Execute else branch if present
        if stmt.else_branch is not None:
            self.execute(stmt.else_branch)
    
    def execute_while_statement(self, stmt: WhileStatement):
        """Execute while loop"""
        while self.is_truthy(self.evaluate(stmt.condition)):
            try:
                self.execute(stmt.body)
            except BreakException:
                break
            except ContinueException:
                continue
    
    def execute_for_statement(self, stmt: ForStatement):
        """Execute for loop"""
        iterable = self.evaluate(stmt.iterable)
        
        if isinstance(iterable, list):
            for item in iterable:
                # Create new environment for loop variable
                loop_env = Environment(self.environment)
                loop_env.define(stmt.variable, item)
                
                previous = self.environment
                try:
                    self.environment = loop_env
                    self.execute(stmt.body)
                except BreakException:
                    break
                except ContinueException:
                    continue
                finally:
                    self.environment = previous
        else:
            raise RuntimeError(f"Object is not iterable: {type(iterable)}")
    
    def execute_return_statement(self, stmt: ReturnStatement):
        """Execute return statement"""
        value = None
        if stmt.value is not None:
            value = self.evaluate(stmt.value)
        
        raise ReturnException(value)
    
    def execute_break_statement(self, stmt: BreakStatement):
        """Execute break statement"""
        raise BreakException()
    
    def execute_continue_statement(self, stmt: ContinueStatement):
        """Execute continue statement"""
        raise ContinueException()
    
    def execute_try_statement(self, stmt: TryStatement):
        """Execute try-catch-finally statement"""
        caught_exception = None
        exception_handled = False
        
        try:
            # Execute try body
            for statement in stmt.try_body:
                self.execute(statement)
        except (BreakException, ContinueException, ReturnException):
            # Control flow exceptions should propagate up
            raise
        except Exception as e:
            caught_exception = e
            
            # Try to find a matching catch clause
            for catch_clause in stmt.catch_clauses:
                if catch_clause.variable:
                    # Create new environment with exception variable
                    catch_env = Environment(self.environment)
                    
                    # Convert exception to Lapis runtime exception
                    if isinstance(e, LapisError):
                        exception_obj = LapisRuntimeException(str(e), e)
                    else:
                        exception_obj = LapisRuntimeException(str(e), e)
                    
                    catch_env.define(catch_clause.variable, exception_obj)
                    
                    # Execute catch body in new environment
                    previous = self.environment
                    try:
                        self.environment = catch_env
                        for statement in catch_clause.body:
                            self.execute(statement)
                        exception_handled = True
                        break
                    finally:
                        self.environment = previous
                else:
                    # Catch clause without variable - catch any exception
                    for statement in catch_clause.body:
                        self.execute(statement)
                    exception_handled = True
                    break
        
        # Always execute finally block
        if stmt.finally_body:
            for statement in stmt.finally_body:
                self.execute(statement)
        
        # Re-raise unhandled exceptions
        if caught_exception and not exception_handled:
            raise caught_exception
    
    def execute_switch_statement(self, stmt: SwitchStatement):
        """Execute switch statement"""
        switch_value = self.evaluate(stmt.expression)
        
        matched_case = None
        default_case = None
        
        # Find matching case or default
        for case in stmt.cases:
            if case.is_default:
                default_case = case
            else:
                for case_value_expr in case.values:
                    case_value = self.evaluate(case_value_expr)
                    if self._values_equal(switch_value, case_value):
                        matched_case = case
                        break
                if matched_case:
                    break
        
        # Execute the matched case (or default if no match)
        case_to_execute = matched_case or default_case
        if case_to_execute:
            try:
                for statement in case_to_execute.body:
                    self.execute(statement)
            except BreakException:
                # Break out of switch statement
                pass
    
    def execute_package_statement(self, stmt: PackageStatement):
        """Execute package import statement"""
        # Resolve the file path
        file_path = self.resolve_import_path(stmt.path)
        
        if file_path in self.imported_files:
            # Already imported, just get the public symbols
            return self.get_imported_symbols(file_path, stmt.imports)
        
        # Add to imported files to prevent circular imports
        self.imported_files.add(file_path)
        
        try:
            # Read and parse the imported file
            with open(file_path, 'r') as file:
                source = file.read()
            
            lexer = Lexer(source)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse()
            
            # Create new interpreter for the imported file
            imported_interpreter = Interpreter()
            imported_interpreter.interpret(ast, file_path)
            
            # Get public symbols and import them into current environment
            if stmt.imports is None:
                # Import all public symbols
                public_symbols = imported_interpreter.globals.get_all_public()
                for symbol_name, symbol_value in public_symbols.items():
                    self.environment.define(symbol_name, symbol_value, AccessModifier.PRIVATE)
            else:
                # Import specific symbols
                for import_name in stmt.imports:
                    try:
                        value = imported_interpreter.globals.get(import_name, from_external_file=True)
                        self.environment.define(import_name, value, AccessModifier.PRIVATE)
                    except AccessError:
                        from source_map import Span
                        dummy_span = Span(1, 0, 1)
                        raise ImportError.from_simple(
                            "LAP4003", f"Cannot import private symbol '{import_name}' from '{stmt.path}'", dummy_span
                        )
                    except RuntimeError:
                        from source_map import Span
                        dummy_span = Span(1, 0, 1)
                        raise ImportError.from_simple(
                            "LAP4003", f"Symbol '{import_name}' not found in '{stmt.path}'", dummy_span
                        )
        
        except FileNotFoundError:
            from source_map import Span
            dummy_span = Span(1, 0, 1)
            raise ImportError.from_simple(
                "LAP4003", f"Could not find file: {stmt.path}", dummy_span
            )
        except Exception as e:
            from source_map import Span
            dummy_span = Span(1, 0, 1)
            # Extract the clean error message if it's already a formatted LapisError
            error_msg = str(e)
            if "Error [LAP" in error_msg:
                # Extract just the inner message after the error code
                parts = error_msg.split(": ", 2)
                if len(parts) >= 2:
                    error_msg = parts[1]
            raise ImportError.from_simple(
                "LAP4003", f"Error importing {stmt.path}: {error_msg}", dummy_span
            )
    
    def resolve_import_path(self, path: str) -> str:
        """Resolve import path to absolute file path"""
        if path.startswith("./"):
            # Relative path from current directory
            return os.path.abspath(path)
        elif path.startswith("/"):
            # Absolute path
            return path
        else:
            # Relative path from current directory
            return os.path.abspath(path)
    
    def get_imported_symbols(self, file_path: str, imports: List[str]) -> Dict[str, Any]:
        """Get imported symbols from already-imported file"""
        # This would require keeping track of imported environments
        # For now, just return empty dict (improvement needed)
        return {}
    
    def evaluate(self, expr: Expression) -> Any:
        """Evaluate an expression"""
        return self.visit_expression(expr)
    
    def visit_expression(self, expr: Expression) -> Any:
        """Visit and evaluate expression based on type"""
        if isinstance(expr, LiteralExpression):
            return expr.value
        elif isinstance(expr, IdentifierExpression):
            try:
                return self.environment.get(expr.name)
            except Exception as env_error:
                # Handle undefined variable with proper error
                if expr.span:
                    raise RuntimeError.undefined_variable(expr.span, expr.name)
                else:
                    from source_map import Span
                    raise RuntimeError.undefined_variable(Span(0, 0, 1), expr.name)
        elif isinstance(expr, BinaryExpression):
            return self.evaluate_binary_expression(expr)
        elif isinstance(expr, UnaryExpression):
            return self.evaluate_unary_expression(expr)
        elif isinstance(expr, CallExpression):
            return self.evaluate_call_expression(expr)
        elif isinstance(expr, GetExpression):
            return self.evaluate_get_expression(expr)
        elif isinstance(expr, SetExpression):
            return self.evaluate_set_expression(expr)
        elif isinstance(expr, IndexExpression):
            return self.evaluate_index_expression(expr)
        elif isinstance(expr, IndexSetExpression):
            return self.evaluate_index_set_expression(expr)
        elif isinstance(expr, ArrayExpression):
            return self.evaluate_array_expression(expr)
        elif isinstance(expr, DictionaryExpression):
            return self.evaluate_dictionary_expression(expr)
        elif isinstance(expr, AssignmentExpression):
            return self.evaluate_assignment_expression(expr)
        elif isinstance(expr, LogicalExpression):
            return self.evaluate_logical_expression(expr)
        elif isinstance(expr, ThisExpression):
            return self.environment.get("this")
        elif isinstance(expr, PostfixExpression):
            return self.evaluate_postfix_expression(expr)
        elif isinstance(expr, TemplateLiteralExpression):
            return self.evaluate_template_literal_expression(expr)
        else:
            raise RuntimeError(f"Unknown expression type: {type(expr)}")
    
    def evaluate_binary_expression(self, expr: BinaryExpression) -> Any:
        """Evaluate binary expression with type-aware error reporting"""
        left = self.evaluate(expr.left)
        right = self.evaluate(expr.right)
        
        if expr.operator == "+":
            if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                return left + right
            # String concatenation - convert non-strings to strings using Lapis formatting
            elif isinstance(left, str) or isinstance(right, str):
                return self._to_lapis_string(left) + self._to_lapis_string(right)
            else:
                # Generate detailed type error with spans for unsupported types
                left_type = self._get_type_name(left)
                right_type = self._get_type_name(right)
                
                # Get spans with safe attribute access
                expr_span, left_span, right_span = self._get_safe_spans(expr)
                
                if expr_span and left_span and right_span:
                    raise TypeError.cannot_add_types(
                        expr_span, left_span, right_span,
                        left_type, right_type
                    )
                else:
                    # Fallback for missing spans
                    from source_map import Span
                    dummy_span = Span(0, 0, 1)
                    raise TypeError.cannot_add_types(
                        dummy_span, dummy_span, dummy_span,
                        left_type, right_type
                    )
        
        elif expr.operator == "-":
            if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
                left_type = self._get_type_name(left)
                right_type = self._get_type_name(right)
                # Get spans with safe attribute access
                expr_span, left_span, right_span = self._get_safe_spans(expr)
                
                if expr_span and left_span and right_span:
                    raise TypeError.invalid_binary_operation(
                        expr_span, left_span, right_span,
                        expr.operator, left_type, right_type
                    )
            return left - right
        
        elif expr.operator == "*":
            if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
                left_type = self._get_type_name(left)
                right_type = self._get_type_name(right)
                if expr.span and expr.left.span and expr.right.span:
                    raise TypeError.invalid_binary_operation(
                        expr.span, expr.left.span, expr.right.span,
                        expr.operator, left_type, right_type
                    )
            return left * right
        
        elif expr.operator == "/":
            if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
                left_type = self._get_type_name(left)
                right_type = self._get_type_name(right)
                if expr.span and expr.left.span and expr.right.span:
                    raise TypeError.invalid_binary_operation(
                        expr.span, expr.left.span, expr.right.span,
                        expr.operator, left_type, right_type
                    )
            if right == 0:
                if expr.span:
                    raise RuntimeError.division_by_zero(expr.span)
                else:
                    from source_map import Span
                    raise RuntimeError.division_by_zero(Span(1, 0, 1))
            return left / right
        
        elif expr.operator == "**":
            if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
                left_type = self._get_type_name(left)
                right_type = self._get_type_name(right)
                if expr.span and expr.left.span and expr.right.span:
                    raise TypeError.invalid_binary_operation(
                        expr.span, expr.left.span, expr.right.span,
                        expr.operator, left_type, right_type
                    )
            return left ** right
        
        elif expr.operator == "%":
            if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
                left_type = self._get_type_name(left)
                right_type = self._get_type_name(right)
                if expr.span and expr.left.span and expr.right.span:
                    raise TypeError.invalid_binary_operation(
                        expr.span, expr.left.span, expr.right.span,
                        expr.operator, left_type, right_type
                    )
            return left % right
        
        elif expr.operator == ">":
            if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
                left_type = self._get_type_name(left)
                right_type = self._get_type_name(right)
                if expr.span and expr.left.span and expr.right.span:
                    raise TypeError.invalid_binary_operation(
                        expr.span, expr.left.span, expr.right.span,
                        expr.operator, left_type, right_type
                    )
            return left > right
        
        elif expr.operator == ">=":
            if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
                left_type = self._get_type_name(left)
                right_type = self._get_type_name(right)
                if expr.span and expr.left.span and expr.right.span:
                    raise TypeError.invalid_binary_operation(
                        expr.span, expr.left.span, expr.right.span,
                        expr.operator, left_type, right_type
                    )
            return left >= right
        
        elif expr.operator == "<":
            if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
                left_type = self._get_type_name(left)
                right_type = self._get_type_name(right)
                if expr.span and expr.left.span and expr.right.span:
                    raise TypeError.invalid_binary_operation(
                        expr.span, expr.left.span, expr.right.span,
                        expr.operator, left_type, right_type
                    )
            return left < right
        
        elif expr.operator == "<=":
            if not (isinstance(left, (int, float)) and isinstance(right, (int, float))):
                left_type = self._get_type_name(left)
                right_type = self._get_type_name(right)
                if expr.span and expr.left.span and expr.right.span:
                    raise TypeError.invalid_binary_operation(
                        expr.span, expr.left.span, expr.right.span,
                        expr.operator, left_type, right_type
                    )
            return left <= right
        
        elif expr.operator == "!=":
            return not self.is_equal(left, right)
        
        elif expr.operator == "==":
            return self.is_equal(left, right)
        
        from source_map import Span
        dummy_span = expr.span or Span(0, 0, 1)
        raise RuntimeError.from_simple(
            "LAP4999", f"Unknown binary operator: {expr.operator}", dummy_span
        )
    
    def evaluate_unary_expression(self, expr: UnaryExpression) -> Any:
        """Evaluate unary expression"""
        operand = self.evaluate(expr.operand)
        
        if expr.operator == "-":
            self.check_number_operand(expr.operator, operand)
            return -operand
        elif expr.operator == "!":
            return not self.is_truthy(operand)
        
        raise RuntimeError(f"Unknown unary operator: {expr.operator}")
    
    def evaluate_call_expression(self, expr: CallExpression) -> Any:
        """Evaluate function call"""
        callee = self.evaluate(expr.callee)
        
        arguments = []
        for argument in expr.arguments:
            arguments.append(self.evaluate(argument))
        
        if not hasattr(callee, 'call'):
            raise RuntimeError("Can only call functions and classes")
        
        if hasattr(callee, 'arity') and callee.arity() != -1 and len(arguments) != callee.arity():
            raise RuntimeError(f"Expected {callee.arity()} arguments but got {len(arguments)}")
        
        return callee.call(self, arguments)
    
    def evaluate_get_expression(self, expr: GetExpression) -> Any:
        """Evaluate property access"""
        obj = self.evaluate(expr.object)
        
        if isinstance(obj, LapisInstance):
            return obj.get(expr.name)
        elif hasattr(obj, 'get') and callable(getattr(obj, 'get')):
            return obj.get(expr.name)
        elif isinstance(obj, dict):
            # Support dot notation for dictionaries: dict.key instead of dict["key"]
            if expr.name in obj:
                return obj[expr.name]
            else:
                return None  # Return None for missing keys (similar to JavaScript behavior)
        elif isinstance(obj, str):
            return self.get_string_method(obj, expr.name)
        elif isinstance(obj, list):
            return self.get_array_method(obj, expr.name)
        elif isinstance(obj, bool):
            return self.get_boolean_method(obj, expr.name)
        elif isinstance(obj, (int, float)):
            return self.get_number_method(obj, expr.name)
        
        raise RuntimeError(f"'{type(obj).__name__}' object has no property '{expr.name}'")
    
    def evaluate_set_expression(self, expr: SetExpression) -> Any:
        """Evaluate property assignment"""
        obj = self.evaluate(expr.object)
        
        if isinstance(obj, LapisInstance):
            value = self.evaluate(expr.value)
            obj.set(expr.name, value)
            return value
        elif isinstance(obj, dict):
            # Support dot notation assignment for dictionaries: dict.key = value
            value = self.evaluate(expr.value)
            obj[expr.name] = value
            return value
        
        raise RuntimeError("Only instances and dictionaries have assignable fields")
    
    def evaluate_index_expression(self, expr: IndexExpression) -> Any:
        """Evaluate array/dictionary access"""
        obj = self.evaluate(expr.object)
        index = self.evaluate(expr.index)
        
        if isinstance(obj, list):
            if not isinstance(index, int):
                raise RuntimeError("Array index must be an integer")
            if index < 0 or index >= len(obj):
                raise RuntimeError("Array index out of bounds")
            return obj[index]
        elif isinstance(obj, dict):
            return obj.get(index)
        else:
            raise RuntimeError("Can only index arrays and dictionaries")
    
    def evaluate_index_set_expression(self, expr: IndexSetExpression) -> Any:
        """Evaluate array/dictionary assignment"""
        obj = self.evaluate(expr.object)
        index = self.evaluate(expr.index)
        value = self.evaluate(expr.value)
        
        if isinstance(obj, list):
            if not isinstance(index, int):
                raise RuntimeError("Array index must be an integer")
            if index < 0 or index >= len(obj):
                raise RuntimeError("Array index out of bounds")
            obj[index] = value
        elif isinstance(obj, dict):
            obj[index] = value
        else:
            raise RuntimeError("Can only index arrays and dictionaries")
        
        return value
    
    def evaluate_array_expression(self, expr: ArrayExpression) -> list:
        """Evaluate array literal"""
        elements = []
        for element_expr in expr.elements:
            elements.append(self.evaluate(element_expr))
        return elements
    
    def evaluate_dictionary_expression(self, expr: DictionaryExpression) -> dict:
        """Evaluate dictionary literal"""
        result = {}
        for key_expr, value_expr in expr.pairs:
            key = self.evaluate(key_expr)
            value = self.evaluate(value_expr)
            result[key] = value
        return result
    
    def evaluate_assignment_expression(self, expr: AssignmentExpression) -> Any:
        """Evaluate assignment"""
        value = self.evaluate(expr.value)
        self.environment.assign(expr.name, value)
        return value
    
    def evaluate_logical_expression(self, expr: LogicalExpression) -> Any:
        """Evaluate logical expression"""
        left = self.evaluate(expr.left)
        
        if expr.operator == "||":
            if self.is_truthy(left):
                return left
            return self.evaluate(expr.right)
        elif expr.operator == "&&":
            if not self.is_truthy(left):
                return left
            return self.evaluate(expr.right)
        
        raise RuntimeError(f"Unknown logical operator: {expr.operator}")
    
    def evaluate_postfix_expression(self, expr: PostfixExpression) -> Any:
        """Evaluate postfix expression (++, --)"""
        if not isinstance(expr.operand, IdentifierExpression):
            raise RuntimeError("Postfix operators can only be applied to variables")
        
        current_value = self.environment.get(expr.operand.name)
        
        if not isinstance(current_value, (int, float)):
            raise RuntimeError("Postfix operators can only be applied to numbers")
        
        if expr.operator == "++":
            self.environment.assign(expr.operand.name, current_value + 1)
        elif expr.operator == "--":
            self.environment.assign(expr.operand.name, current_value - 1)
        else:
            raise RuntimeError(f"Unknown postfix operator: {expr.operator}")
        
        return current_value  # Return the original value (postfix)
    
    def evaluate_template_literal_expression(self, expr: TemplateLiteralExpression) -> str:
        """Evaluate template literal by interpolating variables from current scope"""
        result = ""
        
        for text_part, var_name in expr.parts:
            if text_part is not None:
                # Static text part
                result += text_part
            elif var_name is not None:
                # Expression interpolation part
                try:
                    # Try to parse and evaluate the content as an expression
                    value = self._evaluate_template_expression(var_name)
                    result += self._to_lapis_string(value)
                except Exception as e:
                    # Expression evaluation failed
                    if expr.span:
                        raise RuntimeError.from_simple(
                            "LAP4001", f"Error evaluating expression '{var_name}' in template literal: {str(e)}", expr.span
                        )
                    else:
                        from source_map import Span
                        dummy_span = Span(1, 0, 1)
                        raise RuntimeError.from_simple(
                            "LAP4001", f"Error evaluating expression '{var_name}' in template literal: {str(e)}", dummy_span
                        )
        
        return result
    
    def _evaluate_template_expression(self, expression_text: str):
        """Parse and evaluate a Lapis expression from template literal"""
        # Import here to avoid circular imports
        from lexer import Lexer
        from parser import Parser
        
        try:
            # Tokenize the expression
            lexer = Lexer(expression_text, "<template>")
            tokens = lexer.tokenize()
            
            # Parse as expression
            parser = Parser(tokens)
            
            # Parse just the expression (not a full program)
            expr = parser.expression()
            
            # Evaluate the expression in current environment
            return self.evaluate(expr)
        
        except Exception as e:
            # If parsing/evaluation fails, try as simple variable name for backward compatibility
            try:
                return self.environment.get(expression_text.strip())
            except:
                # Re-raise the original parsing error
                raise e
    
    def is_truthy(self, obj: Any) -> bool:
        """Determine truthiness of object"""
        if obj is None:
            return False
        if isinstance(obj, bool):
            return obj
        if isinstance(obj, (int, float)):
            return obj != 0
        if isinstance(obj, str):
            return len(obj) > 0
        if isinstance(obj, (list, dict)):
            return len(obj) > 0
        return True
    
    def is_equal(self, a: Any, b: Any) -> bool:
        """Check equality"""
        return a == b
    
    def check_number_operand(self, operator: str, operand: Any):
        """Check that operand is a number"""
        if not isinstance(operand, (int, float)):
            raise RuntimeError(f"Operand must be a number for '{operator}'")
    
    def check_number_operands(self, operator: str, left: Any, right: Any):
        """Check that both operands are numbers"""
        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            raise RuntimeError(f"Operands must be numbers for '{operator}'")
    
    def get_string_method(self, string_obj: str, method_name: str):
        """Get method for string objects"""
        
        class StringLengthMethod:
            def __init__(self, string_value):
                self.string_value = string_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                return len(self.string_value)
        
        class StringSplitMethod:
            def __init__(self, string_value):
                self.string_value = string_value
            
            def arity(self):
                return 1
            
            def call(self, interpreter, arguments):
                delimiter = arguments[0]
                if not isinstance(delimiter, str):
                    raise RuntimeError("split() delimiter must be a string")
                return self.string_value.split(delimiter)
        
        class StringReplaceMethod:
            def __init__(self, string_value):
                self.string_value = string_value
            
            def arity(self):
                return 2
            
            def call(self, interpreter, arguments):
                old = arguments[0]
                new = arguments[1]
                if not isinstance(old, str) or not isinstance(new, str):
                    raise RuntimeError("replace() arguments must be strings")
                return self.string_value.replace(old, new)
        
        class StringContainsMethod:
            def __init__(self, string_value):
                self.string_value = string_value
            
            def arity(self):
                return 1
            
            def call(self, interpreter, arguments):
                substring = arguments[0]
                if not isinstance(substring, str):
                    raise RuntimeError("contains() argument must be a string")
                return substring in self.string_value
        
        class StringToIntMethod:
            def __init__(self, string_value):
                self.string_value = string_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                try:
                    return int(self.string_value)
                except ValueError:
                    raise RuntimeError(f"Cannot convert '{self.string_value}' to integer")
        
        class StringToFloatMethod:
            def __init__(self, string_value):
                self.string_value = string_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                try:
                    return float(self.string_value)
                except ValueError:
                    raise RuntimeError(f"Cannot convert '{self.string_value}' to float")
        
        class StringToBoolMethod:
            def __init__(self, string_value):
                self.string_value = string_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                lower_val = self.string_value.lower()
                if lower_val in ['true', '1', 'yes', 'on']:
                    return True
                elif lower_val in ['false', '0', 'no', 'off', '']:
                    return False
                else:
                    raise RuntimeError(f"Cannot convert '{self.string_value}' to boolean")
        
        if method_name == "length":
            return StringLengthMethod(string_obj)
        elif method_name == "split":
            return StringSplitMethod(string_obj)
        elif method_name == "replace":
            return StringReplaceMethod(string_obj)
        elif method_name == "contains":
            return StringContainsMethod(string_obj)
        elif method_name == "toInt":
            return StringToIntMethod(string_obj)
        elif method_name == "toFloat":
            return StringToFloatMethod(string_obj)
        elif method_name == "toBool":
            return StringToBoolMethod(string_obj)
        elif method_name == "toString":
            # String toString just returns itself
            class StringToStringMethod:
                def __init__(self, string_value):
                    self.string_value = string_value
                
                def arity(self):
                    return 0
                
                def call(self, interpreter, arguments):
                    return self.string_value
            return StringToStringMethod(string_obj)
        elif method_name == "format":
            # String formatting with {variable} syntax
            class StringFormatMethod:
                def __init__(self, string_value):
                    self.string_value = string_value
                
                def arity(self):
                    return -1  # Variable arguments
                
                def call(self, interpreter, arguments):
                    # Arguments can be passed as key-value pairs or a dictionary
                    if len(arguments) == 1 and isinstance(arguments[0], dict):
                        # Single dictionary argument
                        variables = arguments[0]
                    elif len(arguments) % 2 == 0:
                        # Key-value pairs: "name", "John", "age", 25
                        variables = {}
                        for i in range(0, len(arguments), 2):
                            key = arguments[i]
                            value = arguments[i + 1]
                            if not isinstance(key, str):
                                from source_map import Span
                                dummy_span = Span(1, 0, 1)
                                raise RuntimeError.from_simple(
                                    "LAP4006", "Format variable names must be strings", dummy_span
                                )
                            variables[key] = value
                    else:
                        from source_map import Span
                        dummy_span = Span(1, 0, 1)
                        raise RuntimeError.from_simple(
                            "LAP4006", "Format arguments must be key-value pairs or a single dictionary", dummy_span
                        )
                    
                    return self._format_string(interpreter, self.string_value, variables)
                
                def _format_string(self, interpreter, template, variables):
                    """Replace {variable} placeholders with values"""
                    import re
                    
                    def replace_placeholder(match):
                        var_name = match.group(1)
                        if var_name in variables:
                            value = variables[var_name]
                            return interpreter._to_lapis_string(value)
                        else:
                            from source_map import Span
                            dummy_span = Span(1, 0, 1)
                            raise RuntimeError.from_simple(
                                "LAP4006", f"Format variable '{var_name}' not provided", dummy_span
                            )
                    
                    # Replace {variable_name} with values
                    return re.sub(r'\{([^}]+)\}', replace_placeholder, template)
            
            return StringFormatMethod(string_obj)
        else:
            raise RuntimeError(f"String has no method '{method_name}'")
    
    def get_number_method(self, number_obj, method_name: str):
        """Get method for number objects (int/float)"""
        
        class NumberToStringMethod:
            def __init__(self, number_value):
                self.number_value = number_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                return str(self.number_value)
        
        class NumberToIntMethod:
            def __init__(self, number_value):
                self.number_value = number_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                return int(self.number_value)
        
        class NumberToFloatMethod:
            def __init__(self, number_value):
                self.number_value = number_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                return float(self.number_value)
        
        class NumberToBoolMethod:
            def __init__(self, number_value):
                self.number_value = number_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                return self.number_value != 0
        
        if method_name == "toString":
            return NumberToStringMethod(number_obj)
        elif method_name == "toInt":
            return NumberToIntMethod(number_obj)
        elif method_name == "toFloat":
            return NumberToFloatMethod(number_obj)
        elif method_name == "toBool":
            return NumberToBoolMethod(number_obj)
        else:
            raise RuntimeError(f"Number has no method '{method_name}'")
    
    def get_boolean_method(self, bool_obj, method_name: str):
        """Get method for boolean objects"""
        
        class BooleanToStringMethod:
            def __init__(self, bool_value):
                self.bool_value = bool_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                return "true" if self.bool_value else "false"
        
        class BooleanToIntMethod:
            def __init__(self, bool_value):
                self.bool_value = bool_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                return 1 if self.bool_value else 0
        
        class BooleanToFloatMethod:
            def __init__(self, bool_value):
                self.bool_value = bool_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                return 1.0 if self.bool_value else 0.0
        
        if method_name == "toString":
            return BooleanToStringMethod(bool_obj)
        elif method_name == "toInt":
            return BooleanToIntMethod(bool_obj)
        elif method_name == "toFloat":
            return BooleanToFloatMethod(bool_obj)
        else:
            raise RuntimeError(f"Boolean has no method '{method_name}'")
    
    def _get_type_name(self, value: Any) -> str:
        """Get human-readable type name for error messages"""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "number"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "dictionary"
        else:
            return type(value).__name__.lower()
    
    def _get_safe_spans(self, expr):
        """Safely get spans from expression, returning None if not available"""
        expr_span = getattr(expr, 'span', None)
        left_span = getattr(expr.left, 'span', None) if hasattr(expr, 'left') and hasattr(expr.left, 'span') else None
        right_span = getattr(expr.right, 'span', None) if hasattr(expr, 'right') and hasattr(expr.right, 'span') else None
        return expr_span, left_span, right_span
    
    def _to_lapis_string(self, obj):
        """Convert object to Lapis-style string representation"""
        if obj is None:
            return "null"
        if isinstance(obj, bool):
            return "true" if obj else "false"
        if isinstance(obj, str):
            return obj
        if isinstance(obj, (int, float)):
            return str(obj)
        if isinstance(obj, list):
            elements = [self._to_lapis_string(elem) for elem in obj]
            return f"[{', '.join(elements)}]"
        if isinstance(obj, dict):
            pairs = [f"{self._to_lapis_string(k)}: {self._to_lapis_string(v)}" for k, v in obj.items()]
            return f"{{{', '.join(pairs)}}}"
        return str(obj)
    
    def get_array_method(self, array_obj: list, method_name: str):
        """Get method for array objects"""
        
        class ArrayMapMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return 1
            
            def call(self, interpreter, arguments):
                func = arguments[0]
                if not hasattr(func, 'call'):
                    raise RuntimeError("map() argument must be a function")
                
                result = []
                for item in self.array_value:
                    mapped_item = func.call(interpreter, [item])
                    result.append(mapped_item)
                return result
        
        class ArrayFilterMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return 1
            
            def call(self, interpreter, arguments):
                func = arguments[0]
                if not hasattr(func, 'call'):
                    raise RuntimeError("filter() argument must be a function")
                
                result = []
                for item in self.array_value:
                    if interpreter.is_truthy(func.call(interpreter, [item])):
                        result.append(item)
                return result
        
        class ArrayReduceMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return 2
            
            def call(self, interpreter, arguments):
                func = arguments[0]
                initial = arguments[1]
                
                if not hasattr(func, 'call'):
                    raise RuntimeError("reduce() first argument must be a function")
                
                accumulator = initial
                for item in self.array_value:
                    accumulator = func.call(interpreter, [accumulator, item])
                return accumulator
        
        class ArrayLengthMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                return len(self.array_value)
        
        class ArrayPushMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return -1  # Variable arguments
            
            def call(self, interpreter, arguments):
                for arg in arguments:
                    self.array_value.append(arg)
                return len(self.array_value)  # Return new length
        
        class ArrayPopMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                if len(self.array_value) == 0:
                    return None
                return self.array_value.pop()
        
        class ArrayShiftMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                if len(self.array_value) == 0:
                    return None
                return self.array_value.pop(0)
        
        class ArrayUnshiftMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return -1  # Variable arguments
            
            def call(self, interpreter, arguments):
                for i, arg in enumerate(arguments):
                    self.array_value.insert(i, arg)
                return len(self.array_value)  # Return new length
        
        class ArraySpliceMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return -1  # Variable arguments (start, deleteCount, ...items)
            
            def call(self, interpreter, arguments):
                if len(arguments) == 0:
                    raise RuntimeError("splice() requires at least 1 argument (start index)")
                
                start = arguments[0]
                if not isinstance(start, int):
                    raise RuntimeError("splice() start index must be an integer")
                
                # Handle negative indices
                if start < 0:
                    start = max(0, len(self.array_value) + start)
                else:
                    start = min(start, len(self.array_value))
                
                # Delete count (default to rest of array)
                delete_count = len(self.array_value) - start
                if len(arguments) > 1:
                    delete_count = arguments[1]
                    if not isinstance(delete_count, int):
                        raise RuntimeError("splice() delete count must be an integer")
                    delete_count = max(0, min(delete_count, len(self.array_value) - start))
                
                # Items to insert
                items_to_insert = arguments[2:] if len(arguments) > 2 else []
                
                # Remove elements and collect deleted
                deleted = []
                for _ in range(delete_count):
                    if start < len(self.array_value):
                        deleted.append(self.array_value.pop(start))
                
                # Insert new elements
                for i, item in enumerate(items_to_insert):
                    self.array_value.insert(start + i, item)
                
                return deleted  # Return array of deleted elements
        
        class ArraySliceMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return -1  # Variable arguments (start, end)
            
            def call(self, interpreter, arguments):
                start = 0
                end = len(self.array_value)
                
                if len(arguments) > 0:
                    start = arguments[0]
                    if not isinstance(start, int):
                        raise RuntimeError("slice() start index must be an integer")
                    if start < 0:
                        start = max(0, len(self.array_value) + start)
                
                if len(arguments) > 1:
                    end = arguments[1]
                    if not isinstance(end, int):
                        raise RuntimeError("slice() end index must be an integer")
                    if end < 0:
                        end = max(0, len(self.array_value) + end)
                    end = min(end, len(self.array_value))
                
                return self.array_value[start:end]
        
        class ArrayIndexOfMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return -1  # Variable arguments (searchElement, fromIndex)
            
            def call(self, interpreter, arguments):
                if len(arguments) == 0:
                    raise RuntimeError("indexOf() requires at least 1 argument")
                
                search_element = arguments[0]
                from_index = 0
                
                if len(arguments) > 1:
                    from_index = arguments[1]
                    if not isinstance(from_index, int):
                        raise RuntimeError("indexOf() fromIndex must be an integer")
                    if from_index < 0:
                        from_index = max(0, len(self.array_value) + from_index)
                
                for i in range(from_index, len(self.array_value)):
                    if interpreter.is_equal(self.array_value[i], search_element):
                        return i
                
                return -1  # Not found
        
        class ArrayIncludesMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return -1  # Variable arguments (searchElement, fromIndex)
            
            def call(self, interpreter, arguments):
                if len(arguments) == 0:
                    raise RuntimeError("includes() requires at least 1 argument")
                
                search_element = arguments[0]
                from_index = 0
                
                if len(arguments) > 1:
                    from_index = arguments[1]
                    if not isinstance(from_index, int):
                        raise RuntimeError("includes() fromIndex must be an integer")
                    if from_index < 0:
                        from_index = max(0, len(self.array_value) + from_index)
                
                for i in range(from_index, len(self.array_value)):
                    if interpreter.is_equal(self.array_value[i], search_element):
                        return True
                
                return False
        
        class ArrayReverseMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return 0
            
            def call(self, interpreter, arguments):
                self.array_value.reverse()
                return self.array_value  # Return the array itself
        
        class ArraySortMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return -1  # Optional compare function
            
            def call(self, interpreter, arguments):
                if len(arguments) == 0:
                    # Default sort (lexicographic)
                    self.array_value.sort(key=str)
                else:
                    # Custom compare function
                    compare_func = arguments[0]
                    if not hasattr(compare_func, 'call'):
                        raise RuntimeError("sort() argument must be a function")
                    
                    def compare(a, b):
                        result = compare_func.call(interpreter, [a, b])
                        if not isinstance(result, (int, float)):
                            raise RuntimeError("sort() compare function must return a number")
                        return result
                    
                    from functools import cmp_to_key
                    self.array_value.sort(key=cmp_to_key(compare))
                
                return self.array_value  # Return the array itself
        
        class ArrayJoinMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return -1  # Optional separator
            
            def call(self, interpreter, arguments):
                separator = ","
                if len(arguments) > 0:
                    separator = str(arguments[0])
                
                string_elements = [str(item) if item is not None else "" for item in self.array_value]
                return separator.join(string_elements)
        
        class ArrayConcatMethod:
            def __init__(self, array_value):
                self.array_value = array_value
            
            def arity(self):
                return -1  # Variable arguments
            
            def call(self, interpreter, arguments):
                result = self.array_value.copy()  # Don't modify original
                
                for arg in arguments:
                    if isinstance(arg, list):
                        result.extend(arg)
                    else:
                        result.append(arg)
                
                return result
        
        # Method dispatch
        method_map = {
            "map": ArrayMapMethod(array_obj),
            "filter": ArrayFilterMethod(array_obj),
            "reduce": ArrayReduceMethod(array_obj),
            "length": ArrayLengthMethod(array_obj),
            "push": ArrayPushMethod(array_obj),
            "pop": ArrayPopMethod(array_obj),
            "shift": ArrayShiftMethod(array_obj),
            "unshift": ArrayUnshiftMethod(array_obj),
            "splice": ArraySpliceMethod(array_obj),
            "slice": ArraySliceMethod(array_obj),
            "indexOf": ArrayIndexOfMethod(array_obj),
            "includes": ArrayIncludesMethod(array_obj),
            "reverse": ArrayReverseMethod(array_obj),
            "sort": ArraySortMethod(array_obj),
            "join": ArrayJoinMethod(array_obj),
            "concat": ArrayConcatMethod(array_obj)
        }
        
        if method_name in method_map:
            return method_map[method_name]
        else:
            raise RuntimeError.from_simple(
                "LAP4005", f"Array has no method '{method_name}'", None
            )
    
    def _values_equal(self, left: Any, right: Any) -> bool:
        """Check if two values are equal for switch statement comparison"""
        # Handle None values
        if left is None and right is None:
            return True
        if left is None or right is None:
            return False
        
        # Handle boolean values
        if isinstance(left, bool) and isinstance(right, bool):
            return left == right
        
        # Handle numeric values (int, float)
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left == right
        
        # Handle string values
        if isinstance(left, str) and isinstance(right, str):
            return left == right
        
        # Handle list/array values (shallow comparison)
        if isinstance(left, list) and isinstance(right, list):
            if len(left) != len(right):
                return False
            return all(self._values_equal(a, b) for a, b in zip(left, right))
        
        # Handle dictionary values (shallow comparison)
        if isinstance(left, dict) and isinstance(right, dict):
            if set(left.keys()) != set(right.keys()):
                return False
            return all(self._values_equal(left[k], right[k]) for k in left.keys())
        
        # For other types, use Python's default equality
        return left == right
