from FastAPIProject.Models.domain.entity import Entity

class Paragraph:
    def __init__(self,index: int, start: int, end: int, entities: list[Entity], summary: str = ""):
        self.index = index
        self.start = start
        self.end = end
        self.entities = entities
        self.summary = summary
        self.place = []
        self.time = []
        # self.events = []
#        self.descriptions = []
