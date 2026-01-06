from enum import Enum 

# self.scenario = "basenha"  # possible values: basenha (no obstacles, no hunger, no age, no food), base (no obstacles, with food), 
# basea (no obstacles with age, but no food), baseah (no obstacles with food, hunger and age), rock (one rock generated), tunnel (nest inside a tunnel)
class Scenario(Enum):
    BASE = 1
    BASEA = 2
    BASEAH = 3
    ROCK = 4
    TUNNEL = 5
    BASENHA = 6 