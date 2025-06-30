from FastAPIProject.config.config_loader import config
from FastAPIProject.Models.domain.entity import Entity

def is_male(entity: Entity):
    name_count = [0, 0]
    for n in entity.nicknames:
        words = n.split()
        for w in words:
            if w.lower() in config["services"]["gender-phrases"]["male"]:
                name_count[0] += 1
            elif w.lower() in config["services"]["gender-phrases"]["female"]:
                name_count[1] += 1
    return name_count[0] > name_count[1]