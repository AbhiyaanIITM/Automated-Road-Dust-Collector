import json

class JSONReader:
    def __init__(self, filename):
        self.filename = filename
        self.data = {}
        self.readData(self.filename)
    
    def readData(self, filename):
        try:
            with open(filename, "r") as f:
                self.data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"JSON decode error in file {filename}: {e}")
            self.data = {}
        except Exception as e:
            print(f"Error reading JSON file {filename}: {e}")
            self.data = {}