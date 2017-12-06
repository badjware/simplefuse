from filesystem import Directory

class DictDirectory(Directory):
    def __init__(self, data={}):
        super().__init__()
        self.data = data

        for k, v in data.items():
            if v is dict:
                dir = DictDirectory(v)
                self.add(k, v)
    
    def get_dict(self):
        pass
