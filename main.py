#!/usr/bin/env python3
"""
Lapis Programming Language Interpreter
Main entry point for running .lapis files
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser
from interpreter import Interpreter
from errors import LapisError
from diagnostics import get_formatter
from source_map import reset_source_map

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <filename.lapis>")
        sys.exit(1)
    
    filename = sys.argv[1]
    
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)
    
    if not filename.endswith('.lapis'):
        print("Error: File must have .lapis extension.")
        sys.exit(1)
    
    # Reset source map for each run
    reset_source_map()
    formatter = get_formatter()
    
    try:
        with open(filename, 'r') as file:
            source = file.read()
        
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
        print(f"Internal Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()