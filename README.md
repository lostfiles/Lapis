# Lapis Language Features

A complete, up-to-date catalog of the Lapis programming language features as implemented in this repository.

This document covers syntax, types, control flow, functions, classes, collections, modules, built-ins, operators, errors, and the CLI.

## Syntax Basics
- Statements end with a semicolon `;`
- Blocks are delimited with keywords and `end` (e.g., `func ... end`, `if ... end`)
- Parentheses are required around conditions (e.g., `if (x > 0)`)
- Comments:
  - Single-line: `// comment text`
  - Multi-line: `/* comment text */` (supports nesting)
- Whitespace (newlines and tabs) is generally ignored between statements

Example
```lapis
// A simple program
private var x = 42;

/* 
   Multi-line comment
   explaining the logic
*/
if (x > 10)
    Console.print("big"); /* inline comment */
else
    Console.print("small");
end
```

## Types and Literals
- number: integer and floating-point numbers (e.g., `42`, `3.14`)
- string: double-quoted `"text"` or single-quoted `'text'` strings with escapes (e.g., `"hi\nthere"`, `'Don\'t'`)
- boolean: `true`, `false`
- null: represents "no value" (use `null` keyword)
- array: `[1, 2, 3]`
- dictionary: `{ "key": "value" }` or JavaScript-style `{key: value}` for bare identifier keys

### Type Conversions
All types support method-based conversions:

```lapis
// String conversions
var s = "123";
var i = s.toInt();      // 123
var f = s.toFloat();    // 123.0
var b = "true".toBool(); // true

// Number conversions  
var n = 42;
var str = n.toString();  // "42"
var fl = n.toFloat();   // 42.0
var bool = n.toBool();  // true (non-zero = true)

// Boolean conversions
var b = true;
var str = b.toString(); // "true"
var num = b.toInt();    // 1
var fl = b.toFloat();   // 1.0
```

### String Formatting
Lapis supports two ways to format strings with variables:

**Template Literals (recommended):**
```lapis
var name = "Alice";
var age = 25;

// Simple variable interpolation
var message = `Hello {name}, you are {age} years old!`;

// Full expression support
var calc = `Sum: {10 + 20}, Greater: {age > 18}`;
var method = `Length: {name.length()}, Uppercase: {name.toString()}`;
var complex = `Result: {(age + 5) * 2}`;
```

**Format Method:**
```lapis
// With key-value pairs
var template = "Hello {name}, you are {age} years old!";
var result = template.format("name", "Alice", "age", 25);

// With dictionary
var data = {name: "Alice", age: 25};
var result2 = template.format(data);
```

Template literals support full expressions within `{...}` and automatically resolve variables from the current scope, while the format method gives more control for dynamic data.

### String Quotes
Strings can use either single or double quotes:

```lapis
var double = "Hello world";
var single = 'Hello world';
var mixed1 = 'He said "Hello"';     // No escaping needed
var mixed2 = "Don't worry";         // No escaping needed
var escaped1 = "He said \"Hello\"";  // Escape same quote type
var escaped2 = 'Don\'t worry';       // Escape same quote type
```

## Variables and Scope
- Declaration: `var name = expression;`
- Access modifiers: `private` (default) and `public`
  - Public symbols are importable by other files; private symbols are file-local

Examples
```lapis
private var a = 10;
public var greeting = "Hello";
```

## Expressions and Operators
- Arithmetic: `+`, `-`, `*`, `/`, `%`, `**` (power is right-associative)
- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Logical: `&&`, `||`, `!`
- Unary: `-x`, `!x`
- Postfix: `i++`, `i--` (numbers only, returns the original value)
- Property access: `obj.prop`
- Indexing: `arr[0]`, `dict["key"]`

String concatenation
- `+` supports string concatenation; if either operand is a string, both sides are converted to strings.

Operator precedence (high → low)
1. calls, property access, indexing
2. postfix (`++`, `--`)
3. unary (`-`, `!`)
4. power `**` (right-associative)
5. `*`, `/`, `%`
6. `+`, `-`
7. comparisons (`<`, `<=`, `>`, `>=`)
8. equality (`==`, `!=`)
9. logical `&&`
10. logical `||`

## Control Flow

### Conditionals
- If/Elif/Else
```lapis
if (score >= 90)
    print("A");
elif (score >= 80)
    print("B");
else
    print("C");
end
```

### Loops
- While
```lapis
while (i < 5)
    print(i);
    i++;
end
```
- For (arrays only)
```lapis
for item in [1, 2, 3]
    print(item);
end
```

### Loop Control
- Break: Exit a loop early
```lapis
while (true)
    print("Enter 'quit' to exit:");
    var input = Console.input();
    if (input == "quit")
        break;
    end
    print("You entered: " + input);
end
```
- Continue: Skip to the next iteration
```lapis
for i in [1, 2, 3, 4, 5]
    if (i % 2 == 0)
        continue;  // skip even numbers
    end
    print("Odd: " + i);
end
```
- Break/continue can only be used inside loops; using them elsewhere raises an error

### Switch Statements
```lapis
switch (day)
case 1:
    print("Monday");
case 2:
    print("Tuesday");
case 3, 4, 5:  // Multiple values per case
    print("Midweek");
default:
    print("Weekend");
end
```
- Cases can match multiple values (comma-separated)
- No fallthrough: each case is independent
- Optional `default` case for unmatched values
- `break` can be used within cases (but not required)
- Works with numbers, strings, and other value types

### Exception Handling
- Try/Catch/Finally
```lapis
try
    private var result = 10 / 0;  // This will error
    print("This won't print");
catch (e)
    print("Caught error: " + e);
finally
    print("This always executes");
end
```
- `try` block: code that might throw errors
- `catch (variable)`: handles any runtime error, binding it to the variable
- `finally` block: always executes, even if no error occurs
- All blocks are optional except `try`
- Supports nested try-catch blocks
- Catches all Lapis runtime errors (division by zero, undefined variables, etc.)
- Manual error throwing: Use `Console.error(message)` to throw custom errors

```lapis
func validate_input(value)
    if (value < 0)
        Console.error("Value must be positive: " + value);
    end
    return value;
end

try
    validate_input(-10);
catch (e)
    Console.print("Validation error: " + e);
end
```

### Function Returns
```lapis
func add(a, b)
    return a + b;
end
```

## Functions

### Regular Functions
- Declaration
```lapis
private func square(x)
    return x * x;
end
```
- Public functions are importable
- First-class usage: you can pass functions to array helpers like `map`, `filter`, `reduce`

### Variadic Functions
- Functions can accept any number of arguments using `args**` syntax
- The variadic parameter collects all extra arguments into an array
```lapis
public func print_all(items**)
    for item in items
        Console.print("Item: " + item);
    end
end

// Usage
print_all("a", "b", "c");        // items = ["a", "b", "c"]
print_all(1, 2, 3, 4, 5);       // items = [1, 2, 3, 4, 5]
```

- Can combine fixed parameters with variadic
```lapis
public func greet_all(greeting, names**)
    for name in names
        Console.print(greeting + ", " + name);
    end
end

greet_all("Hello", "Alice", "Bob");  // greeting="Hello", names=["Alice", "Bob"]
```

- Excellent for wrapping Python functions cleanly
```lapis
public func join(parts**)
    return __lapis_native_py_call("os.path", "join", parts);
end

var path = join("folder1", "folder2", "file.txt");
```

## Classes and Objects
- Declaration and methods
```lapis
public class Person()
    func init()
        this.name = "Unknown";
    end

    func set_name(name)
        this.name = name;
    end

    func greet()
        print("Hello, I'm " + this.name);
    end
end

var p = Person();
p.set_name("Alice");
p.greet();
```
- Constructor method is named `init`
- `this` refers to the current instance
- Property access/assignment: `obj.prop`, `obj.prop = value`

## Collections

### Arrays
- Literals: `[1, 2, 3]`
- Indexing: `arr[0]` (0-based). Errors on non-integer indices and out-of-bounds access.
- Assignment: `arr[1] = 99;`
- Iteration: `for item in arr ... end`

Array helper methods (all available)
- Query/size: `length()`
- Mutation:
  - `push(...items)` → append items, return new length
  - `pop()` → remove and return last element (or `nil` if empty)
  - `shift()` → remove and return first element (or `nil` if empty)
  - `unshift(...items)` → insert at beginning, return new length
  - `splice(start, deleteCount, ...items)` → remove/insert; returns array of removed elements
  - `reverse()` → reverse in place, returns the array
  - `sort([compareFn])` → sort in place; default string compare; custom `compare(a, b)` returns number
- Non-mutating:
  - `slice(start, end)` → copy subarray
  - `concat(...arraysOrValues)` → return new array
  - `join([separator])` → string join (defaults to ",")
- Search:
  - `indexOf(element, [fromIndex])` → index or `-1`
  - `includes(element, [fromIndex])` → boolean
- Higher-order:
  - `map(fn)`
  - `filter(fn)`
  - `reduce(fn, initial)`

Examples
```lapis
var a = [1, 2, 3];
a.push(4, 5);
var removed = a.splice(1, 2, 9, 9);  // a=[1, 9, 9, 4, 5], removed=[2, 3]
print(a.join("-"));                  // "1-9-9-4-5"
```

### Dictionaries
- Literals: `{ "name": "Alice", "age": 30 }`
- JavaScript-style keys: `{name: "Alice", age: 30}` (bare identifiers become string keys)
- Indexing: `dict["name"]`
- Dot access sugar: `dict.name` (returns `nil` for missing keys)
- Dot assignment: `dict.name = "Bob"`

## Modules and Imports
- Import syntax
```lapis
// In another file: math_utils.lapis
public func square(x)
    return x * x;
end

// In current file
package "./math_utils.lapis" use square;
print(square(5));  // 25
```
- Only `public` symbols are importable; importing a private symbol raises an error
- Paths can be relative (`./file.lapis`) or absolute

## Built-in Modules and Functions

### Console (as object)
- `Console.print(...args)` → print with stringification
- `Console.input([prompt])` → read a line (or `nil` on EOF)
- `Console.number([prompt])` → read a number (int/float) or error on invalid
- `Console.error(message)` → throw a custom error with the given message (catchable with try-catch)

### Math
- `Math.sqrt(x)` (non-negative)
- `Math.abs(x)`
- `Math.floor(x)`
- `Math.ceil(x)`

### File
- `File.read(path)` → string
- `File.write(path, content)` → true
- `File.append(path, content)` → true
- `File.exists(path)` → boolean
- `File.delete(path)` → true or error
- `File.list([dir])` → array of filenames

### Native Python Interop (Internal)
- `__lapis_native_py_call(py_module, py_module_func_name, ...args)` → any
  - **Internal function for bootstrapping new features**
  - `py_module` (string): Python module name (e.g., "os", "math", "os.path")
  - `py_module_func_name` (string): function name within the module
  - `...args` (variadic): any number of arguments to pass to the Python function
  - Alternative: `__lapis_native_py_call(py_module, py_module_func_name, [args])` with array
  - Returns the value returned by the Python function
  - Catches Python exceptions and converts them to Lapis runtime errors

```lapis
// Example: Creating OS utilities in pure Lapis
public func get_cwd()
    return __lapis_native_py_call("os", "getcwd");
end

// Clean variadic wrapper for Python functions
public func join(parts**)
    return __lapis_native_py_call("os.path", "join", parts);
end

public func max_of(values**)
    return __lapis_native_py_call("builtins", "max", values);
end

// Usage
var current_dir = get_cwd();
var full_path = join(current_dir, "documents", "file.txt");
var maximum = max_of(5, 2, 8, 1, 9);
Console.print("Path: " + full_path);
Console.print("Max: " + maximum);

// Direct calls also work
var direct_join = __lapis_native_py_call("os.path", "join", "dir1", "dir2", "file");
```

### String Methods
- `str.length()` → number
- `str.split(delimiter)` → array
- `str.replace(old, new)` → string
- `str.contains(substring)` → boolean

## Runtime Semantics
- Truthiness
  - `nil` → false
  - boolean → itself
  - number → `0` is false, others true
  - string/array/dictionary → empty is false, non-empty true
  - everything else → true
- Equality uses underlying Python equality; arrays/dicts compare structurally

## Error Handling and Diagnostics
- Comprehensive diagnostics with error codes and labeled spans
- Error classes include: lexer, parser, runtime, type, import, access
- Human-friendly code frames with caret underlines and help messages
- Colors auto-enable on TTY; set `NO_COLOR=1` to disable

Examples (human format)
```
Error [LAP3001]: cannot add number and string
  --> main.lapis:2:7
   |
1 | var x = 42;
2 | print(x + "hello");
  |       -^^^------
          cannot add number and string
          left operand has type number
              right operand has type string
   = help: convert the number to a string with string(x) or use string concatenation
```

## CLI / Running Code
- Run a file
```bash
python main.py file.lapis
```
- Interactive REPL
```bash
python lapis.py
```
  - Enter statements; `;` is auto-appended for single lines
  - Type `exit` to quit

## Access Control Rules
- `private` (default): only visible within the file
- `public`: importable from other files via `package ... use ...;`
- Applies to: variables, functions, classes

## Language Limitations and Notes
- For-loops iterate arrays (not dictionaries yet)
- Dictionaries return `nil` for missing keys on dot/index access
- Postfix `++`/`--` apply to variables and numbers only
- Division by zero raises a runtime error (catchable with try-catch)
- Switch statements don't have fallthrough (each case is independent)
- Exception handling catches all runtime errors; specific error types are not distinguished
- `__lapis_native_py_call` is internal-only for bootstrapping; not intended for general use

## Examples

### Basic Language Features
```lapis
// All together
public func sum(a, b)
    return a + b;
end

public class Counter()
    func init()
        this.value = 0;
    end

    func inc()
        this.value++;
    end
end

var c = Counter();
c.inc();
print("Counter: " + c.value);

var nums = [1, 2, 3, 4];
print(nums.filter(func(x) return x % 2 == 0; end).join(", "));
```

### Variadic Functions in Practice
```lapis
// Statistical analysis using variadic functions
public func analyze(label, values**)
    private var sum = 0;
    private var count = 0;
    private var min_val = values[0];
    private var max_val = values[0];
    
    Console.print("Analyzing " + label + " with " + values.length() + " values:");
    
    for value in values
        sum = sum + value;
        count = count + 1;
        if (value < min_val)
            min_val = value;
        end
        if (value > max_val)
            max_val = value;
        end
    end
    
    private var average = sum / count;
    Console.print("  Average: " + average);
    Console.print("  Min: " + min_val + ", Max: " + max_val);
    return average;
end

// Python integration with variadic wrappers
public func join_paths(parts**)
    return __lapis_native_py_call("os.path", "join", parts);
end

public func get_max(numbers**)
    return __lapis_native_py_call("builtins", "max", numbers);
end

// Usage
analyze("Test Scores", 85, 92, 78, 96, 88);
var config_path = join_paths("home", "user", "config", "app.json");
var highest = get_max(15, 23, 8, 42, 11);
```

### Advanced Control Flow Example
```lapis
// Demonstrates break, continue, try-catch, switch, and error throwing
public func process_numbers(numbers)
    for num in numbers
        // Skip negative numbers
        if (num < 0)
            Console.print("Skipping negative: " + num);
            continue;
        end
        
        // Stop at 100
        if (num >= 100)
            Console.print("Stopping at: " + num);
            break;
        end
        
        // Custom validation
        if (num == 13)
            Console.error("Unlucky number 13 is not allowed!");
        end
        
        try
            // Categorize numbers with switch
            switch (num % 3)
            case 0:
                Console.print(num + " is divisible by 3");
            case 1:
                Console.print(num + " has remainder 1 when divided by 3");
            default:
                Console.print(num + " has remainder 2 when divided by 3");
            end
            
            // Potentially risky operation
            private var result = 100 / (num % 10);
            Console.print("100 / (" + num + " % 10) = " + result);
        catch (e)
            Console.print("Error processing " + num + ": " + e);
        finally
            Console.print("Finished processing " + num);
        end
    end
end

// Usage - demonstrates various error sources
process_numbers([-5, 3, 10, 13, 20, 25, 100, 200]);
```

---
This document describes the current, implemented feature set of Lapis in this repository. If you add or modify features, consider updating this file to match.
