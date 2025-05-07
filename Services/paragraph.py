# from . import character
# from . import event

class Paragraph:
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end
        self.characters = []
        self.events = []
#        self.descriptions = []
