from tokenizer import Tokenizer
from bools import *
from err import Errors
import string

t      = Tokenizer()
errors = Errors()

class Lex:
    def __init__(self):
        self.letters = string.ascii_lowercase+string.ascii_uppercase
        
        ## TEMP VARIABLEES ##
        self.bit          = ""
        
        self.temp_string  = ""
        self.in_str       = false
        
        self.temp_num     = ""
        self.temp_literal = ""
        
        
        self.toks    = [
            "if",   "else",  "print",
            "main", "func",  "preload", "var", 
            "bool", "char"
        ]
        
        self.literals = "#$%&\'()*+,-./:;<=>!?@[\\]^_`{|}"
        self.numbers  = "0123456789"
        
        self.ignore_characters = [
            ' ', '\n', '©'
        ]
    
    def generate_tokens(self, filename):
        content = open(filename,'r').read()+"©"
        
        for index, char in enumerate(content):
            t.token += char
            
            for letter in self.letters:
                if t.token == letter:
                    if self.temp_literal != "":
                        t.create_token('literal', self.temp_literal)
                        self.temp_literal = ''
                        
                    if self.in_str:
                        self.temp_string += letter
                    elif not self.in_str:
                        self.bit += letter
                        if self.temp_string != '':
                            t.create_token('string',self.temp_string)
                            self.temp_string = ''
                    t.clear()
                elif t.token == ' ' and self.in_str:
                    self.temp_string += ' '
                    t.clear()
                elif t.token == '\n' and self.in_str:
                    errors.throw_error('InvalidSyntax','Cannot initialize string without closing quotes.')
                    t.clear()
                elif t.token == '"':
                    if self.temp_literal != "":
                        t.create_token('literal', self.temp_literal)
                        self.temp_literal = ''
                    
                    if self.in_str:
                        self.in_str = false
                    elif not self.in_str:
                        if self.temp_string != "":
                            t.create_token('string',self.temp_string)
                            self.temp_string = ''
                            
                        if self.bit != '':
                            if self.bit in self.toks:
                                t.create_token(self.bit, self.bit)
                            else:
                                t.create_token('name', self.bit)
                            self.bit = ''
                        self.in_str = true
                    t.clear()
                elif t.token in self.literals:
                    for literal in self.literals:
                        if t.token == literal:
                            if self.bit != '':
                                if self.bit in self.toks:
                                    t.create_token(self.bit, self.bit)
                                else:
                                    t.create_token('name', self.bit)
                                self.bit = ''
                            
                            self.temp_literal += literal
                            
                            if self.temp_literal != '':
                                t.create_token('literal', self.temp_literal)
                                self.temp_literal = ''
                    t.clear()
            
            for ignore in self.ignore_characters:
                if t.token == ignore:
                    if self.bit != '':
                        if self.bit in self.toks:
                            t.create_token(self.bit, self.bit)
                        else:
                            t.create_token('name', self.bit)
                        self.bit = ''
                    elif self.temp_string != '':
                        if self.in_str:
                            errors.throw_error('InvalidSyntax', "Cannot initialize string without closing quotes.")
                        else:
                            t.create_token('string',self.temp_string)
                            self.temp_string = ''
                    elif self.temp_literal != '':
                        t.create_token('literal', self.temp_literal)
                        self.temp_literal = ''
                    t.clear()
        
        for token in t.tokens:
            print(token)
        
        """
        tt = t.tokens
        t.clear()
        
        return tt
        """