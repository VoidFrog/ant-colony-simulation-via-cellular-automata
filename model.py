import mesa
import numpy as np

from agent import AntAgent
from agent import FoodPatch
from agent import Nest


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
    N - number of agents
    width - width of the grid
    height - height of the grid
    g - gain factor
    J_11, J_12, J_21, J_22 - Values of the interaction matrix
    prob_spontaneous - Spontaneous Activation Prob.
    pher_dec - pheromone decay rate
    pher_diff - pheromone diffusion rate
    pher_drop - amount of phermone dropped by ants
    nfp - amount of food patches
    fpp - amount of food per patch
    noise - probability of random movement when not carrying food
    sr - sensing radius for agents
    """

    def __init__(self, N, width, height, g, J_11, J_12, J_21, J_22, prob_spontaneous,pher_dec, pher_diff, pher_drop, nfp, fpp, noise, sr,  seed=None):
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
        self.pher_dec = float(get_value(pher_dec))
        self.pher_diff = float(get_value(pher_diff))
        self.pher_drop = float(get_value(pher_drop))
        self.nfp = int(get_value(nfp))
        self.fpp = float(get_value(fpp))
        self.noise = float(get_value(noise))
        self.sr = float(get_value(sr))
        self.nest_pos = (width // 2, height // 2)
        self.max_dist = (width + height)
        if final_seed is not None:
            try:
                final_seed = int(final_seed)
            except (ValueError, TypeError):
                final_seed = None

        # -------------------------
        super().__init__(seed=final_seed)
        self.grid = mesa.space.MultiGrid(width, height, torus=False)
        self.food = np.zeros((width, height), dtype=int)
        self.pher_food = np.zeros((width, height), dtype=float)
        self.pher_home = np.zeros((width, height), dtype=float)
        self.running = True

        # === Model Parameters from the Paper ===
        # These are now guaranteed to be numbers
        # (self.g, self.J_11, etc. were set above)
        # ========================================

        self._scatter_food(nfp, 3)
        # Create agents
        for i in range(self.num_agents):
            a = AntAgent(i, self)
            self.grid.place_agent(a, self.nest_pos)
        #Uid forces a unique identifier
        uid = 10_000
        nest = Nest(uid, self, self.nest_pos)
        self.grid.place_agent(nest, self.nest_pos)
        uid += 1
        for x in range(width):
            for y in range(height):
                amount = self.food[x, y]
                if amount > 0:
                    patch = FoodPatch(uid, self, (x, y), amount=amount)
                    self.grid.place_agent(patch, (x, y))
                    uid += 1

            
        # Setup DataCollector
        self.food_delivered = 0
        self.datacollector = mesa.DataCollector(
            model_reporters={"ActiveAntPercentage": get_active_ant_percentage, "FoodDelivered": self.food_delivered},
            agent_reporters={"ActivityLevel": "activity_level", "State": "state"})

    def _scatter_food(self, n_patches, r):
        W, H = self.grid.width, self.grid.height
        for _ in range(n_patches):
            # Randomize patch center
            cx, cy = self.random.randrange(W), self.random.randrange(H)
            radius = self.random.randrange(1, 4)
            for x in range(W):
                for y in range(H):
                    if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
                        self.food[x, y] += self.fpp

        # eliminate food from nearby the nest
        nx, ny = self.nest_pos
        self.food[nx, ny] = 0
        for x in range(nx - r, nx + r):
            for y in range(ny - r, ny + r):
                if x < 0 or y < 0 or x >= W or y >= H:
                    continue
                else:
                    self.food[x, y] = 0

    def decay(self, arr):
        arr *= (1.0-self.pher_dec)

    def diffuse(self,arr):
        W, H = self.grid.width, self.grid.height
        n = arr.copy()
        for i in range(W):
            for j in range(H):
                vals = [arr[i, j]] + \
                    ([arr[i - 1, j]] if i > 0 else []) + \
                    ([arr[i + 1, j]] if i < W - 1 else []) + \
                    ([arr[i, j - 1]] if j > 0 else []) + \
                    ([arr[i, j + 1]] if j < H - 1 else [])
                avg = sum(vals) / len(vals)
                n = (1-self.pher_diff)*arr[i, j] + self.pher_diff*avg
        arr[:, :] = n

    def step(self):
        """
        Advance the model by one step.
        """
        self.datacollector.collect(self)
        
        # 1. All agents calculate their next state based on the current state.
        self.agents.do("step")
        # 2. All agents apply their new state.
        self.agents.do("advance")
        self.decay(self.pher_food)
        self.decay(self.pher_home)
        self.diffuse(self.pher_food)
        self.diffuse(self.pher_home)