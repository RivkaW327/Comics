
class Entity:
    def __init__(self, name: str, nicknames: list[str], label: str, coref_position :list[int], description = ""):
        self.name = name
        self.nicknames = nicknames
        self.label = label
        self.coref_position = coref_position
        self.description = description # check about the format

