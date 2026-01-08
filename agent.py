from typing import Tuple, cast, TYPE_CHECKING

import mesa
import math

import numpy as np
from mesa import Agent

if TYPE_CHECKING:
    from model import ColonyModel


class AntAgent(mesa.Agent):
    """
    An agent implementing the Mobile Cellular Automata (MCA) model
    from Cole & Cheshire (1996).

    Activity is a continuous value (A_t), not a simple binary state.
    """
    def __init__(self, unique_id, model: "ColonyModel"):
        super().__init__(model)
        self.unique_id = unique_id

        # Initialize with a random activity level between -1 and 1
        self.activity_level = self.random.uniform(-1.0, 1.0)
        self.next_activity_level = self.activity_level
        # life cycle based on hunger
        self.hunger = 0
        self.is_dead = False
        # Start as not carrying food
        self.carrying = False
        self.current_food_source = None
        # Previous position
        self.previous_pos = None

    @property
    def colony(self) -> "ColonyModel":
        """
        Helper property to access the MESA model already casted into "ColonyModel"
        """
        return cast("ColonyModel", self.model)

    @property
    def state(self):
        """
        A derived property. The paper defines an ant as 'active'
        if its activity level (A_t) is greater than zero.
        This is useful for the visualization.
        """
        return 'active' if self.activity_level > 0 else 'inactive'

    @property
    def state_2(self):
        """
        A derived property. The paper defines an ant as 'active'
        if its activity level (A_t) is greater than zero.
        This is useful for the visualization.
        """
        return 'carrying' if self.carrying > 0 else 'foraging'

    def dist_to_nest(self, pos):
        """
        Calculates the distance between the current position and the nest
        """
        (nx, ny) = self.colony.nest_pos
        (x, y) = pos
        return np.linalg.norm([x - nx, y - ny], 2)

    def get_interaction_sum(self):
        """
        Calculates the sum of interactions with neighbors:
        Σ(J_ij * A_kt)
        """
        interaction_sum = 0
        current_position = cast(Tuple[int, int], self.pos)

        neighbors = self.colony.grid.get_neighbors(
            current_position,
            moore=True,
            include_center=False
        )
        neighbors = [neighbor for neighbor in neighbors if isinstance(neighbor, AntAgent)]
        for neighbor in neighbors:
            # Determine which J coefficient to use based on states
            if self.state == 'active' and neighbor.state == 'active':
                J = self.colony.J_11  # Active -> Active
            elif self.state == 'active' and neighbor.state == 'inactive':
                J = self.colony.J_12  # Inactive -> Active
            elif self.state == 'inactive' and neighbor.state == 'active':
                J = self.colony.J_21  # Active -> Inactive
            else:  # self.state == 'inactive' and neighbor.state == 'inactive'
                J = self.colony.J_22  # Inactive -> Inactive

            interaction_sum += J * neighbor.activity_level

        return interaction_sum

    def step(self):
        if self.hunger >= self.colony.hunger_threshold:
            self.is_dead = True
            return

        S_t = self.colony.g * self.activity_level
        interaction_term = self.colony.g * self.get_interaction_sum()
        next_activity_level = math.tanh(interaction_term + self.colony.g * S_t)

        if self.state == 'inactive':
            if self.random.random() < self.colony.prob_spontaneous_activation:
                next_activity_level = 0.01
        if self.state == 'inactive':
            self.hunger += 1
        self.next_activity_level = next_activity_level

        if self.state == 'active':
            self.move()

    def advance(self):
        self.activity_level = self.next_activity_level

    def objective(self, pos_next: Tuple[int, int], current_density) -> float:
        x, y = pos_next
        weight = 0.0
        diff = self.colony.pher_food_layer.data[x, y] - current_density

        if not self.carrying:
            if self.colony.food[x, y] > 0:
                weight = 20.0
            elif diff > 0:
                weight = 1.0 + diff
            elif diff == 0:
                weight = 1.0
            else:
                weight = 1e-6
        else:
            weight += 1.0 * self.colony.pher_home_dict[self][x, y]
            weight += 2.0 * (self.dist_to_nest(self.pos) - self.dist_to_nest(pos_next))
        return weight

    def avg_pheromone_density(self, position):
        tiles = list(self.colony.grid.get_neighborhood(position, moore=True, include_center=True))
        avg = 0.0
        for (x, y) in tiles:
            avg += self.colony.pher_food_layer.data[x, y]
        return avg / 9.0

    def deposit_pheromone(self, A=1.0, sigma=1.0):
        (x, y) = self.pos
        (fx, fy) = self.current_food_source

        dist2 = (x - fx) ** 2 + (y - fy) ** 2
        amount = A * np.exp(-dist2 / sigma ** 2)
        self.colony.pher_food_layer.modify_cell((x, y), lambda c: c + amount)

    def move(self):
        cp = cast(Tuple[int, int], self.pos)
        next_pos = None

        # Getting neighbor tiles
        possible_steps = list(self.colony.grid.get_neighborhood(cp, moore=True, include_center=False))
        # Discarding tiles with obstacles
        possible_steps = list([step for step in possible_steps if self.colony.obstacles_layer.data[step[0]][step[1]] == 0])
        # calculating score for each tile
        score = [self.objective(m, self.colony.pher_food_layer.data[cp[0], cp[1]]) for m in possible_steps]

        if not self.carrying:
            self.hunger += 1
            if self.avg_pheromone_density(cp) > 1e-6:
                total_score = np.sum(score)
                probability = [p / total_score for p in score]
                indices = [i for i in range(len(score))]
                index = np.random.choice(indices, None, True, probability)
                next_pos = possible_steps[index]
            else:
                next_pos = self.random.choice(possible_steps)
        else:
            best_move = np.max(score)
            for i in range(8):
                if score[i] == best_move:
                    next_pos = possible_steps[i]
                    break

        # move ant after calculating next position
        self.previous_pos = self.pos
        self.colony.grid.move_agent(self, next_pos)
        x, y = next_pos[0], next_pos[1]

        # picking up nearby food
        if not self.carrying and self.colony.food[x, y] > 0:
            self.current_food_source = (x, y)
            self.carrying = True
            self.hunger = 0
            if self.colony.food_inf == 0:
                self.colony.food[x, y] -= 1
                for agent in self.colony.grid.get_cell_list_contents([next_pos]):
                    if isinstance(agent, FoodPatch):
                        agent.amount = max(agent.amount - 1, 0)

        # delivering food to nest
        if self.carrying and ((x, y) == self.colony.nest_pos):
            self.colony.food_delivered += 1
            self.current_food_source = None
            self.carrying = False

        # dropping pheromones based on carrying status
        if self.carrying:
            self.deposit_pheromone(A=self.colony.pher_drop)
        else:
            self.colony.pher_home_dict[self][x, y] += self.colony.pher_drop


class FoodPatch(mesa.Agent):
    """
    A food patch agent for the purpose of food visualisation with a way of regrowth
    """
    def __init__(self, uid, model):
        super().__init__(model)
        self.unique_id = uid
        self.max_amount = 0
        self.amount = 0
        self._regen_timer = 0
        self.depleted = False

    @property
    def colony(self) -> "ColonyModel":
        return cast("ColonyModel", self.model)

    @property
    def state(self):
        return 'full' if self.amount > 0 else 'empty'

    def step(self):
        if self.pos is None:
            return

        if self.depleted:
            self._regen_timer += 1
            if self._regen_timer == 120:
                self.amount = self.max_amount
                self.colony.food[self.pos[0], self.pos[1]] = self.max_amount
                self._regen_timer = 0
                self.depleted = False
        else:
            if self.state == 'empty':
                self.depleted = True


class Nest(mesa.Agent):
    """The nest agent for the purpose of visualisation"""
    def __init__(self, uid, model):
        super().__init__(model)
        self.unique_id = uid


# class Obstacle(mesa.Agent):
#     """The obstacle agent for the purpose of visualisation"""
#     def __init__(self, uid, model):
#         super().__init__(model)
#         self.unique_id = uid
