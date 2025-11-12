from typing import Tuple

import mesa
import math

from mesa import Agent


class AntAgent(mesa.Agent):
    """
    An agent implementing the Mobile Cellular Automata (MCA) model
    from Cole & Cheshire (1996).
    
    Activity is a continuous value (A_t), not a simple binary state.
    """
    def __init__(self, unique_id, model):
        super().__init__(model) 
        self.unique_id = unique_id 

        # Initialize with a random activity level between -1 and 1
        self.activity_level = self.random.uniform(-1.0, 1.0)
        self.next_activity_level = self.activity_level
        # Start as not carrying food
        self.carrying = False

    @property
    def state(self):
        """
        A derived property. The paper defines an ant as 'active'
        if its activity level (A_t) is greater than zero.
        This is useful for the visualization.
        """
        return 'active' if self.activity_level > 0 else 'inactive'

    def objective(self, pos_next: Tuple[int, int]) -> float:
        """
        A function to used to determine pathing based on available pheromones and if the agent has acquired food
        """
        x, y = pos_next
        util = 0.0
        if not self.carrying:
            util += 3.0 * self.model.food[x, y]
            util += 1.0 * self.model.pher_food[x, y]
            util -= 0.01 * self.dist_to_nest(pos_next)
        else:
            util += 2.0 * self.model.pher_home[x, y]
            util += 0.2 * (self.model.max_dist - self.dist_to_nest(pos_next))
        return util

    def dist_to_nest(self, pos):
        (nx, ny) = self.model.nest_pos
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
        neighbors = self.model.grid.get_neighbors(
            self.pos,
            moore=True,
            include_center=False
        )
        neighbors = [neighbor for neighbor in neighbors if isinstance(neighbor, AntAgent)]
        for neighbor in neighbors:
            # Determine which J coefficient to use based on states
            if self.state == 'active' and neighbor.state == 'active':
                J = self.model.J_11 # Active -> Active 
            elif self.state == 'active' and neighbor.state == 'inactive':
                J = self.model.J_12 # Inactive -> Active 
            elif self.state == 'inactive' and neighbor.state == 'active':
                J = self.model.J_21 # Active -> Inactive 
            else: # self.state == 'inactive' and neighbor.state == 'inactive'
                J = self.model.J_22 # Inactive -> Inactive
            
            interaction_sum += J * neighbor.activity_level
            
        return interaction_sum

    def step(self):
        """
        This method executes the core mathematical model from the
        Cole & Cheshire (1996) paper at each time step.
        
        This calculates the *next* state.
        """
        
        # 1. Calculate S_t (Internal Dynamics / Self-Interaction)
        # S_t = g * A_t 
        # This term makes activity naturally decay if the ant is alone.
        S_t = self.model.g * self.activity_level
        
        # 2. Calculate the Interaction Term
        # g * Σ(J_ij * A_kt) 
        interaction_term = self.model.g * self.get_interaction_sum()

        # 3. Calculate new A_{t+1}
        # A_{t+1} = Tanh( [interaction term] + S_t )
        # #eghm, pointer below, this WAS the equation, but now it's not, look at the next_activity_level
        # Tanh is used to keep the value between -1 and 1.

        # HAPPY CREATIVE GLUE AND DELUSION POWERS USAGE HERE
        next_activity_level = math.tanh(interaction_term + self.model.g * S_t)
        # this little addon in the equation was made by myself as the model
        # didn't behave correctly. We should search for the reason, but for
        # the time being, current change looks okay. SHOULD BE TESTED ON ALL OF THE CONFIGS.
        # or maybe im blind and cannot read, oh well, you should double sanity check this deranged piece of code :3


        # 4. Handle Spontaneous Activation
        # If the ant is inactive, it has a chance to become active.
        # "a single unit is activated with a constant probability if it is inactive"
        # "A randomly activated ant has an activity level of 0.01" 
        if self.state == 'inactive':
            if self.random.random() < self.model.prob_spontaneous_activation:
                next_activity_level = 0.01

        # Set the new activity level for the *next* step
        # We use this value in the 'advance' method.
        self.next_activity_level = next_activity_level

        # 5. Move if active
        # "If an ant is active, it will move randomly to one of the 
        # neighboring lattice points that is not currently occupied" 
        if self.state == 'active':
            self.move()

    def advance(self):
        """
        Apply the new activity level after all agents have 'stepped'.
        This is the second phase of the SimultaneousActivation.
        """
        self.activity_level = self.next_activity_level

    def legal_moves(self):
        return self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)

    def move(self):
        """
        Determines the next step based on the objective function.
        """
        possible_steps = self.legal_moves()
        score = [(self.objective(m), m) for m in possible_steps]
        best_move = max(s for s, _ in score)

        if self.random.random() < self.model.noise or best_move < 0:
            next_pos = self.random.choice(possible_steps)
        else:
            cnd = [m for s, m in score if s == best_move]
            next_pos = self.random.choice(cnd)

        self.model.grid.move_agent(self, next_pos)
        x, y = next_pos[0], next_pos[1]

        if not self.carrying and self.model.food[x, y] > 0:
            self.model.food[x, y] -= 1
            self.carrying = True
            for agent in self.model.grid.get_cell_list_contents([next_pos]):
                if isinstance(agent, FoodPatch):
                    agent.amount = max(agent.amount - 1, 0)

        if self.carrying and ((x,y) == self.model.nest_pos):
            self.model.food_delivered += 1
            self.carrying = False

        if self.carrying:
            self.model.pher_home[x, y] += self.model.pher_drop
        else:
            self.model.pher_food[x, y] += self.model.pher_drop * 0.25


class FoodPatch(mesa.Agent):
    """A food patch agent for the purpose of food visualisation with an optional way of regrowth"""
    def __init__(self, uid, model):
        super().__init__(model)
        self.unique_id = uid
        self.amount = 0
        # self._regen_timer = 0

    @property
    def state(self):
        return 'full' if self.amount > 0 else 'empty'

    def step(self):
        # Optional regrowth
        # self._regen_timer += 1
        # if self._regen_timer >= 40 and self.amount < 3:
        #     self.amount += 1
        #     x, y = self.pos
        #     self.model.food[x, y] = min(self.model.food[x, y] + 1, 3)
        #     self._regen_timer = 0
        pass


class Nest(mesa.Agent):
    """The nest agent for the purpose of visualisation"""
    def __init__(self, uid, model):
        super().__init__(model)
        self.unique_id = uid
