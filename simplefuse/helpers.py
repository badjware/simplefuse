from simplefuse.filesystem import Directory, File
from simplefuse.decorators import readonly

@readonly
class DictDirectory(Directory):
    def __init__(self, data={}):
        super().__init__()
        self.data = data

        for name, value in data.items():
            if isinstance(value, dict):
                dir = DictDirectory(value)
                self.add_child(name, dir)
            elif isinstance(value, str):
                file = File(bytes(value, 'utf8'))
                self.add_child(name, file)
    
    def get_dict(self):
        # TODO
        pass
