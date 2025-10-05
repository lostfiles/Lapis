#!/usr/bin/env python3
"""
Lapis Programming Language Interpreter
Usage: python3 lapis.py <filename.lapis>
"""

import sys
import os
from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from errors import LapisError
from diagnostics import get_formatter, ColorMode, set_color_mode, set_max_errors
from source_map import reset_source_map

def run_file(filename):
    """Run a Lapis program from a file"""
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)
    
    # Reset source map and get formatter
    reset_source_map()
    formatter = get_formatter()
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Tokenize
        lexer = Lexer(source, filename)
        tokens = lexer.tokenize()
        
        # Parse
        parser = Parser(tokens)
        ast = parser.parse()
        
        # Interpret
        interpreter = Interpreter()
        interpreter.interpret(ast, filename)
        
    except LapisError as e:
        # Use new diagnostic formatter
        formatter.emit_diagnostic(e.diagnostic)
        formatter.print_summary()
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}")
        sys.exit(1)

def run_interactive():
    """Run Lapis in interactive mode"""
    print("Lapis Interactive Mode")
    print("Type 'exit' to quit")
    
    interpreter = Interpreter()
    
    while True:
        try:
            line = input("lapis> ")
            if line.strip().lower() == 'exit':
                break
            
            if line.strip() == '':
                continue
            
            # Add semicolon if not present for single expressions
            if not line.strip().endswith(';'):
                line += ';'
            
            # Tokenize
            lexer = Lexer(line, "<interactive>")
            tokens = lexer.tokenize()
            
            # Parse
            parser = Parser(tokens)
            ast = parser.parse()
            
            # Interpret
            interpreter.interpret(ast, "<interactive>")
            
        except EOFError:
            break
        except KeyboardInterrupt:
            print("\nUse 'exit' to quit.")
        except LapisError as e:
            formatter = get_formatter()
            formatter.emit_diagnostic(e.diagnostic)
        except Exception as e:
            print(f"Unexpected Error: {e}")
    
    print("Goodbye!")

def main():
    """Main entry point"""
    if len(sys.argv) == 1:
        run_interactive()
    elif len(sys.argv) == 2:
        run_file(sys.argv[1])
    else:
        print("Usage: python3 lapis.py [filename.lapis]")
        print("       python3 lapis.py (for interactive mode)")
        sys.exit(1)

if __name__ == "__main__":
    main()