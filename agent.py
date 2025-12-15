from typing import Tuple, cast, TYPE_CHECKING

import mesa
import math

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
        self.hunger = 0
        self.age = 0
        # Start as not carrying food
        self.carrying = False
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

    def dist_to_nest(self, pos):
        """
        Calculates the distance between the current position and the nest
        """
        (nx, ny) = self.colony.nest_pos
        (x, y) = pos
        dx = abs(x - nx)
        dy = abs(y - ny)
        return dx + dy

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
        if self.pos is None:
            return
        
        if self.age >= 60:
            self.remove()
            self.colony.pher_home_dict.pop(self)

        self.age += 1

        S_t = self.colony.g * self.activity_level
        interaction_term = self.colony.g * self.get_interaction_sum()
        next_activity_level = math.tanh(interaction_term + self.colony.g * S_t)

        if self.state == 'inactive':
            if self.random.random() < self.colony.prob_spontaneous_activation:
                next_activity_level = 0.01
        if self.state == 'inactive':
            self.hunger -= 0.5
        self.next_activity_level = next_activity_level
        if self.state == 'active':
            self.move()

    def advance(self):
        """
        Apply the new activity level after all agents have 'stepped'.
        This is the second phase of the SimultaneousActivation.
        """
        self.activity_level = self.next_activity_level

    def objective(self, pos_next: Tuple[int, int]) -> float:
        """
        A function to used to determine pathing based on available pheromones and if the agent has acquired food
        """
        x, y = pos_next
        util = 0.0
        if not self.carrying:
            util += 3.0 * self.colony.food[x, y]
            util += 1.0 * self.colony.pher_food_layer.data[x, y]
        else:
            util += 2.0 * self.colony.pher_home_dict[self][x, y]
            util += 0.2 * (self.colony.max_dist - self.dist_to_nest(pos_next))
        return util

    def move(self):
        """
        Determines the next step based on the objective function.
        """
        if self.pos is None:
            return

        if not self.carrying:
            self.hunger+=1

        current_position = cast(Tuple[int, int], self.pos)
        previous_position = cast(Tuple[int, int], self.previous_pos)

        possible_steps = list(self.colony.grid.get_neighborhood(current_position, moore=True, include_center=False))
        if self.previous_pos is not None:
            possible_steps.remove(previous_position)

        possible_steps = [step for step in possible_steps if self.colony.obstacles[step[0], step[1]] == 0]

        score = [(self.objective(m), m) for m in possible_steps]
        best_move = max(s for s, _ in score)

        if self.random.random() < self.colony.noise or best_move < 0.1:
            next_pos = self.random.choice(possible_steps)
        else:
            cnd = [m for s, m in score if s == best_move]
            next_pos = self.random.choice(cnd)

        self.previous_pos = self.pos
        self.colony.grid.move_agent(self, next_pos)
        x, y = next_pos[0], next_pos[1]

        # picking up nearby food
        if not self.carrying and self.colony.food[x, y] > 0:
            self.colony.food[x, y] -= 1
            self.carrying = True
            self.hunger=0
            for agent in self.colony.grid.get_cell_list_contents([next_pos]):
                if isinstance(agent, FoodPatch):
                    agent.amount = max(agent.amount - 1, 0)

        # delivering food to nest
        if self.carrying and ((x, y) == self.colony.nest_pos):
            self.colony.food_delivered += 1
            self.carrying = False

        # dropping pheromones based on carrying status
        if self.carrying:
            self.colony.pher_food_layer.modify_cell((x, y), lambda c: c + self.colony.pher_drop)
        else:
            self.colony.pher_home_dict[self][x, y] += self.colony.pher_drop
        if self.hunger>10:
            self.remove()
            if self in self.colony.pher_home_dict:
                self.colony.pher_home_dict.pop(self)


class FoodPatch(mesa.Agent):
    """
    A food patch agent for the purpose of food visualisation with an optional way of regrowth
    """
    def __init__(self, uid, model):
        super().__init__(model)
        self.unique_id = uid
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
        # Optional regrowth
        self._regen_timer += 1

        if self.pos is None:
            return

        if 0 < self.amount < self.colony.fpp:
            if self.depleted:
                if self._regen_timer > 60:
                    self.depleted = False
                    self._regen_timer = 0
            elif self._regen_timer >= 5:
                self.amount += 1
                x, y = cast(Tuple[int, int], self.pos)
                self.colony.food[x, y] += 1
                self._regen_timer = 0
        elif self.amount == 0:
            self.depleted = True


class Nest(mesa.Agent):
    """The nest agent for the purpose of visualisation"""

    def __init__(self, uid, model):
        super().__init__(model)
        self.unique_id = uid
