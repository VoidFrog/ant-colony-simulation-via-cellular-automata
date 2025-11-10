import mesa
import math

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

    @property
    def state(self):
        """
        A derived property. The paper defines an ant as 'active'
        if its activity level (A_t) is greater than zero.
        This is useful for the visualization.
        """
        return 'active' if self.activity_level > 0 else 'inactive'

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
        # A_{t+1} = Tanh( [interaction term] + S_t )                           #eghm, pointer below, this WAS the equation, but now it's not, look at the next_activity_level
        # Tanh is used to keep the value between -1 and 1.

        # HAPPY CREATIVE GLUE AND DELUSION POWERS USAGE HERE
        next_activity_level = math.tanh(interaction_term + self.model.g * S_t) #this little addon in the equation was made by myself as the model
                                                                               #didnt behave correctly. We should search for the reason, but for 
                                                                               #the time being, current change looks okay. SHOULD BE TESTED ON ALL OF THE CONFIGS.
        #or maybe im blind and cannot read, oh well, you should double sanity check this deranged piece of code :3 


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

    def move(self):
        """
        Finds a random empty neighboring cell and moves to it.
        """
        possible_steps = self.model.grid.get_neighborhood(
            self.pos,
            moore=True,
            include_center=False
        )
        # Filters for empty cells
        free_spaces = [p for p in possible_steps if self.model.grid.is_cell_empty(p)]
        
        if free_spaces:
            new_position = self.random.choice(free_spaces)
            self.model.grid.move_agent(self, new_position)
class FoodPatch(mesa.Agent):
    """Komórka z jedzeniem — osobny agent do wizualizacji i (opcjonalnie) odrastania."""
    def __init__(self, uid, model, pos, amount=0):
        super().__init__(uid, model)
        self.pos = pos
        self.amount = amount
        # self._regen_timer = 0

    def step(self):
        # Przykładowe proste odrastanie: co 40 ticków dodaj 1, max 3
        # self._regen_timer += 1
        # if self._regen_timer >= 40 and self.amount < 3:
        #     self.amount += 1
        #     x, y = self.pos
        #     self.model.food[x, y] = min(self.model.food[x, y] + 1, 3)
        #     self._regen_timer = 0
        pass


class Nest(mesa.Agent):
    """Gniazdo mrówek (pojedyncza komórka)."""
    def __init__(self, uid, model, pos):
        super().__init__(uid, model)
        self.pos = pos