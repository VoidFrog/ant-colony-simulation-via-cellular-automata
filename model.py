import random

import mesa
import numpy as np
import math
from agent import AntAgent, Obstacle
from agent import FoodPatch
from agent import Nest
from mesa.space import PropertyLayer
import templates


def get_active_ant_percentage(model):
    """
    Helper function for the DataCollector:
    Calculates the percentage of ants that are 'active' (A_t > 0).
    """
    ants_agents = model.agents.select(lambda agent: isinstance(agent, AntAgent))
    active_ants = [a for a in ants_agents if a.state == 'active']
    if not ants_agents:
        return 0
    return (len(active_ants) / len(ants_agents)) * 100


def get_food_delivered_percentage(model):
    """
        Helper function for the DataCollector:
        Calculates the percentage of food delivered to the nest.
    """
    return model.food_delivered / (model.nfp * model.fpp)


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

    def __init__(self, N, width, height, g, J_11, J_12, J_21, J_22, prob_spontaneous, pher_dec, pher_diff, pher_drop,
                 nfp, fpp, noise, sr, seed=None):
        def get_value(param):
            """Helper function to get value from a Solara element."""
            if hasattr(param, "kwargs") and "value" in param.kwargs:
                return param.kwargs["value"]
            if hasattr(param, "value"):
                return param.value
            return param

        final_seed = get_value(seed)
        self.num_agents = int(get_value(N))
        self.uid = 0
        self.scenario = "rock"
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
        self.nest_pos = (width//2 ,height//2)
        self.max_dist = (width // 2 + height // 2)
        if final_seed is not None:
            try:
                final_seed = int(final_seed)
            except (ValueError, TypeError):
                final_seed = None

        # -------------------------
        super().__init__(seed=final_seed)
        self.grid = mesa.space.MultiGrid(width, height, torus=False)
        self.food = np.zeros((width, height), dtype=int)
        self.obstacles=np.zeros((width, height), dtype=int)
        self.pher_food_layer = PropertyLayer("pher_food", width, height, 0.0, dtype=np.float64)
        self.grid.add_property_layer(self.pher_food_layer)
        self.pher_home_dict = {}
        self.running = True

        # === Model Parameters from the Paper ===
        # These are now guaranteed to be numbers
        # (self.g, self.J_11, etc. were set above)
        # ========================================
        if self.scenario == "base":
            i = 1
        else:
            self._make_obstacles(self.scenario, width, height)

        self._scatter_food(nfp, 3)
        for i in range(width):
            for j in range(height):
                if self.obstacles[i][j] != 0 and self.food[i][j] != 0:
                    self.food[i][j] = 0

        # Create agents
        for i in range(self.num_agents):
            a = AntAgent(self.uid, self)
            self.pher_home_dict[a] = np.zeros((width, height), dtype=float)
            self.grid.place_agent(a, self.nest_pos)
            self.uid += 1
        # Uid forces a unique identifier
        nest = Nest(self.uid, self)
        self.grid.place_agent(nest, self.nest_pos)
        self.uid += 1

        for x in range(width):
            for y in range(height):
                amount = self.food[x, y]
                if amount > 0:
                    patch = FoodPatch(self.uid, self)
                    patch.amount = amount
                    self.grid.place_agent(patch, (x, y))
                    self.uid += 1

        # Setup DataCollector
        self.food_delivered = 0
        self.datacollector = mesa.DataCollector(
            model_reporters={"ActiveAntPercentage": get_active_ant_percentage,
                             "FoodDelivered": get_food_delivered_percentage},
            agent_reporters={"ActivityLevel": "activity_level", "State": "state"})

    def _make_obstacles(self, tname, width, height):
        if tname == "rock":
            self.obstacles = templates.dwayne
            self.nest_pos = (width - width//10, height - height//10)
        if tname == "tunnel":
            self.obstacles = templates.tunnel
            self.nest_pos = (41, 44)
        for i in range(width):
            for j in range(height):
                if self.obstacles[i][j] != 0:
                    obstacle = Obstacle(self.uid, self)
                    self.grid.place_agent(obstacle, (i, j))
                    self.uid += 1

    def _scatter_food(self, n_patches, r):
        W, H = self.grid.width, self.grid.height
        for _ in range(n_patches):
            # Randomize patch center
            cx, cy = self.random.randrange(W), self.random.randrange(H)
            radius = self.random.randrange(1, 4)
            for x in range(W):
                for y in range(H):
                    if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2 and not self.obstacles[cx][cy] != 0:
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
        arr *= (1.0 - self.pher_dec)
        return arr

    """
    Functions that manage the behavior of the layer that is common for ants
    and represents pheromones that marks trail to food
    """

    def decay_layer(self, layer):
        layer.modify_cells(lambda x: x * (1.0 - self.pher_dec))

    def diffuse_layer(self, layer):
        w, h = self.grid.width, self.grid.height
        prev = layer.data.copy()
        for i in range(w):
            for j in range(h):
                vals = [prev[i, j]] + \
                       ([prev[i - 1, j]] if i > 0 else []) + \
                       ([prev[i + 1, j]] if i < w - 1 else []) + \
                       ([prev[i, j - 1]] if j > 0 else []) + \
                       ([prev[i, j + 1]] if j < h - 1 else [])
                avg = sum(vals) / len(vals)
                result = (1 - self.pher_diff) * prev[i, j] + self.pher_diff * avg
                layer.set_cell((i, j), result)

    def limit_value(self, layer):
        layer.set_cells(10.0, lambda x: True if x > 10.0 else False)

    def birth_agents(self):
        width , height = self.grid.width, self.grid.height
        bprob=0.0
        if get_active_ant_percentage(self) / 100 < 0.05 or len(self.agents) < 2:
            bprob=0.5
        else:
            bprob=0.1
        if self.random.random() >= bprob:
            a = AntAgent(self.uid, self)
            self.pher_home_dict[a] = np.zeros((width, height), dtype=float)
            self.grid.place_agent(a, self.nest_pos)

    def step(self):
        """
        Advance the model by one step.
        """
        self.datacollector.collect(self)

        # 1. All agents calculate their next state based on the current state.
        self.agents.do("step")
        # 2. All agents apply their new state.
        self.agents.do("advance")
        self.birth_agents()
        # 3. All pheromone layers apply their new state.
        self.decay_layer(self.pher_food_layer)
        self.diffuse_layer(self.pher_food_layer)
        self.limit_value(self.pher_food_layer)
        for k, v in self.pher_home_dict.items():
            self.pher_home_dict[k] = self.decay(v)

        # remove dead ants
        for agent in list(self.agents):
            if isinstance(agent, AntAgent) and agent.is_dead:
                self.pher_home_dict.pop(agent)
                agent.remove()

