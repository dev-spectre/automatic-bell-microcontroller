import json

class JSON:
    json_data = {}

    def __init__(self, file = "/config.json"):
        self.file = file

        if file in JSON.json_data:
            self.json = JSON.json_data[file]
            return

        with open(self.file, "r") as f:
            data = json.load(f)
            self.json = data
            JSON.json_data[file] = data

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