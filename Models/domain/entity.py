
class Entity:
    def __init__(self, name: str, label: str, nicknames: list[str], coref_position :list[tuple[int, int]], description = ""):
        self.name = name
        self.label = label
        self.nicknames = nicknames
        self.coref_position = coref_position
        self.description = description # check about the format

    def get_position(self):
        return self.coref_position