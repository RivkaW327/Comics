from . import character

class Event:
    def __init__(self):
        self.description = self.Description()
        self.dialogs = {} #dictionary of character: dialog
        self.monologs = {} #dictionary of character: monolog

    class Description:
        def __init__(self):
            self.importance = 0
            self.place = ""
            self.time = ""
            self.characters = []
            self.text = ""