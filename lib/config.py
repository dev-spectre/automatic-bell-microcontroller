import json

class JSON:
    def __init__(self, file = "../config.json"):
        self.file = file
        with open(self.file, "r") as f:
            data = json.load(f)
            self.json = data
    
    def save(self):
        try:
            with open(self.file, "w") as f:
                json.dump(self.json, f)
            return True
        except:
            return False
    
    def load(self):
        return self.json

    def set(self, key, value):
        self.json[key] = value
        if self.save():
            return value
    
    def get(self, key):
        return self.json.get(key)

    def remove(self, key):
        try:
            value = self.json.pop(key)
            if self.save():
                return value
        except KeyError:
            pass


config = JSON()