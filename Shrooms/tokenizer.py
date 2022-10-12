class Tokenizer:
    def __init__(self):
        self.token  = ""
        self.tokens = []
        
    def create_token(self,id_, value):
        self.tokens.append({'id':id_,'value':value})
        
    def clear(self):
        self.token = ""
    
    def clear_tokens(self):
        self.tokens = []