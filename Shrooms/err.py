import sys

class Errors:
    def __init__(self):
        pass
    
    def throw_error(self,type_,value):
        print(f"{type_}: {value}")
        sys.exit()