import mesa
from agent import AntAgent 

def get_active_ant_percentage(model):
    """
    Helper function for the DataCollector:
    Calculates the percentage of ants that are 'active' (A_t > 0).
    """
    active_ants = [a for a in model.agents if a.state == 'active']
    if not model.agents:
        return 0
    return (len(active_ants) / len(model.agents)) * 100

class ColonyModel(mesa.Model):
    """
    The main model, now holding the parameters from the paper.
    """
    def __init__(self, N, width, height, g, J_11, J_12, J_21, J_22, prob_spontaneous, seed=None):
        def get_value(param):
            """Helper function to get value from a Solara element."""
            if hasattr(param, "kwargs") and "value" in param.kwargs:
                return param.kwargs["value"]
            if hasattr(param, "value"):
                return param.value
            return param

        final_seed = get_value(seed)
        self.num_agents = int(get_value(N))
        self.g = float(get_value(g))
        self.J_11 = float(get_value(J_11))
        self.J_12 = float(get_value(J_12))
        self.J_21 = float(get_value(J_21))
        self.J_22 = float(get_value(J_22))
        self.prob_spontaneous_activation = float(get_value(prob_spontaneous))
        
        if final_seed is not None:
            try:
                final_seed = int(final_seed)
            except (ValueError, TypeError):
                final_seed = None

        # -------------------------
        super().__init__(seed=final_seed)
        self.grid = mesa.space.SingleGrid(width, height, torus=False)
        self.running = True

        # === Model Parameters from the Paper ===
        # These are now guaranteed to be numbers
        # (self.g, self.J_11, etc. were set above)
        # ========================================

        # Create agents
        for i in range(self.num_agents):
            a = AntAgent(i, self)
                 
            # Find an empty cell
            empty_cells = list(self.grid.empties)
            if empty_cells:
                pos = self.random.choice(empty_cells)
                self.grid.place_agent(a, pos)
            
        # Setup DataCollector
        self.datacollector = mesa.DataCollector(
            model_reporters={"ActiveAntPercentage": get_active_ant_percentage},
            agent_reporters={"ActivityLevel": "activity_level", "State": "state"}
        )

    def step(self):
        """
        Advance the model by one step.
        """
        self.datacollector.collect(self)
        
        # 1. All agents calculate their next state based on the current state.
        self.agents.do("step")
        # 2. All agents apply their new state.
        self.agents.do("advance")