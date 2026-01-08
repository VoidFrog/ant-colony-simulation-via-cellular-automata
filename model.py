import random

import mesa
import numpy as np
import math
from agent import AntAgent, Obstacle
from agent import FoodPatch
from agent import Nest
from mesa.space import PropertyLayer
import templates

from scenario import Scenario


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
    if model.nfp == 0:
        return 1
    else:
        return model.food_delivered / (model.nfp * model.fpp)


def get_ants_alive(model):
    ants_agents = model.agents.select(lambda agent: isinstance(agent, AntAgent))
    return len(ants_agents)


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
    flags - flags that determine whether or not additional model modifiers are used
    thresholds - threshold for both age and hunger
    scenario - scenarios for generating obstacles or condtions
    possible values: basenha (no obstacles, no hunger, no age, no food), base (no obstacles, with food), basea (no obstacles with age, but no food), baseah (no obstacles with food, hunger and age), rock (one rock generated), tunnel (nest inside a tunnel)
    """


class ColonyModel(mesa.Model):
    def __init__(self, N, width, height, g, J_11, J_12, J_21, J_22, prob_spontaneous, pher_dec, pher_diff, pher_drop,
                 nfp, fpp, food_inf, seed=None):
        def get_value(param):
            """Helper function to get value from a Solara element."""
            if hasattr(param, "kwargs") and "value" in param.kwargs:
                return param.kwargs["value"]
            if hasattr(param, "value"):
                return param.value
            return param

        self.num_agents = int(get_value(N))
        self.uid = 0
        self.scenario = Scenario.HUNGER
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
        self.food_inf = int(get_value(food_inf))
        self.nest_pos = (width // 2, height // 2)
        self.max_dist = (width // 2 + height // 2)
        self.hunger_flag = True
        self.hunger_threshold = 80
        final_seed = get_value(seed)

        if final_seed is not None:
            try:
                final_seed = int(final_seed)
            except (ValueError, TypeError):
                final_seed = None

        # -------------------------
        super().__init__(seed=final_seed)
        self.grid = mesa.space.MultiGrid(width, height, torus=False)
        self.food = np.zeros((width, height), dtype=int)
        self.obstacles = np.zeros((width, height), dtype=int)
        self.pher_food_layer = PropertyLayer("pher_food", width, height, 0.0, dtype=np.float64)
        self.obstacles_layer = PropertyLayer("obstacles", width, height, 0.0, dtype=np.int32)
        self.grid.add_property_layer(self.pher_food_layer)
        self.grid.add_property_layer(self.obstacles_layer)
        self.pher_home_dict = {}
        self.running = True

        # Scenarios ------------------------------------------
        if self.scenario == Scenario.BASE:
            self.hunger_flag = False
            self.nfp = 0
        elif self.scenario == Scenario.FOOD:
            self.hunger_flag = False
        elif self.scenario == Scenario.HUNGER:
            self.hunger_flag = True
        else:
            self.hunger_flag = True
            self._make_obstacles(self.scenario, width, height)
        # ----------------------------------------------------

        if not self.hunger_flag:
            self.hunger_threshold = np.inf

        self._scatter_food(self.nfp, 3)
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
                    patch.max_amount = amount
                    self.grid.place_agent(patch, (x, y))
                    self.uid += 1

        # Setup DataCollector
        self.food_delivered = 0
        self.datacollector = mesa.DataCollector(
            model_reporters={"ActiveAntPercentage": get_active_ant_percentage,
                             "FoodDelivered": get_food_delivered_percentage,
                             "AntsAlive": get_ants_alive},
            agent_reporters={"ActivityLevel": "activity_level", "State": "state"})

    def _make_obstacles(self, tname, width, height):
        if tname == "rock":
            self.obstacles = templates.dwayne
            self.nest_pos = (width - 9 * width // 10, height - height // 10)
        if tname == "tunnel":
            self.obstacles = templates.tunnel
            self.nest_pos = (27, 27)
        for i in range(width):
            for j in range(height):
                if self.obstacles[i][j] != 0:
                    self.colony.obstacle_layer.modify_cell((i, j))

    def _scatter_food(self, n_patches, r):
        W, H = self.grid.width, self.grid.height
        for _ in range(n_patches):
            # Randomize patch center
            cx, cy = self.random.randrange(W), self.random.randrange(H)
            while self.obstacles[cx, cy] != 0:
                cx, cy = self.random.randrange(W), self.random.randrange(H)
            for x in range(W):
                for y in range(H):
                    if (x - cx == 0 and y - cy == 0) and not self.obstacles[cx][cy] != 0 and self.food[x, y] == 0:
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

    """
    Functions that manage the behavior of the layer that is common for ants
    and represents pheromones that marks trail to food
    """

    def decay(self, arr):
        arr *= 0.9
        return arr

    def diffuse_decay_layer(self, D=10.0, gamma=0.001, dt=0.001):
        c = self.pher_food_layer.data.copy()
        nx, ny = c.shape

        for i in range(nx):
            for j in range(ny):
                center = c[i, j]

                up = c[i - 1, j] if i > 0 else c[i, j]
                down = c[i + 1, j] if i < nx - 1 else c[i, j]
                left = c[i, j - 1] if j > 0 else c[i, j]
                right = c[i, j + 1] if j < ny - 1 else c[i, j]

                laplacian = up + down + left + right - 4 * center
                new_value = center + dt * (D * laplacian - gamma * center)
                self.pher_food_layer.set_cell((i, j), new_value)

    def birth_agents(self):
        width, height = self.grid.width, self.grid.height
        bprob = 0.0
        if get_active_ant_percentage(self) / 100 < 0.05:
            bprob = 0.5
        else:
            bprob = 0.3
        if self.random.random() <= bprob:
            a = AntAgent(self.uid, self)
            self.pher_home_dict[a] = np.zeros((width, height), dtype=float)
            self.grid.place_agent(a, self.nest_pos)

    def step(self):
        """
        Advance the model by one step.
        """
        self.datacollector.collect(self)

        self.diffuse_decay_layer(
            D=self.pher_diff,
            gamma=self.pher_dec,
            dt=0.001
        )

        for k, v in self.pher_home_dict.items():
            self.pher_home_dict[k] = self.decay(v)

        self.agents.do("step")
        self.agents.do("advance")
        if self.hunger_flag:
            self.birth_agents()

        # remove dead ants
        for agent in list(self.agents):
            if isinstance(agent, AntAgent) and agent.is_dead:
                self.pher_home_dict.pop(agent)
                self.grid.remove_agent(agent)
                agent.remove()
