from FastAPIProject.Models.domain.entity import Entity

class Paragraph:
    def __init__(self,index: int, start: int, end: int, entities: list[int]): #, summary: str = ""):
        self.index = index
        self.start = start
        self.end = end
        self.entities = entities
        self.summary = ""
        self.place = []
        self.time = []
        # self.events = []
#        self.descriptions = []

    def set_summary(self, summ: str):
        """set summary for the paragraph"""
        self.summary = summ

