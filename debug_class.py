#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lexer import Lexer
from parser import Parser

# Test class parsing
source = """
public class Person()
	func init()
		this.age = 10;
	end
end
"""

print("Testing lexer...")
lexer = Lexer(source)
tokens = lexer.tokenize()

print("Tokens:")
for token in tokens[:10]:  # Show first 10 tokens
    print(f"  {token}")

print("\\nTesting parser...")
parser = Parser(tokens)
try:
    ast = parser.parse()
    
    print("\\nAST statements:")
    for stmt in ast.statements:
        print(f"  {type(stmt).__name__}: {stmt}")
        if hasattr(stmt, 'name'):
            print(f"    name: {stmt.name}")
except Exception as e:
    print(f"Parser error: {e}")
    import traceback
    traceback.print_exc()
