from lex import Lex
import os
import sys

lexer  = Lex()

def main():
    tokens = lexer.generate_tokens(sys.argv[1])
    print(tokens)
    """
    try:
        tokens = lexer.generate_tokens(sys.argv[1])
        print(tokens)
    except:
        os.system("python3 C:\\Users\\dying\\Desktop\\Shrooms\\prompt.py")
    """
 
if __name__ == "__main__":
    main()