from typing import Any, Dict

from mesa.visualization import (
    SolaraViz, 
    Slider,
    SpaceRenderer,
    make_plot_component,
    make_space_component
)

from mesa.visualization.solara_viz import create_space_component

from solara import InputInt
from model import ColonyModel
from agent import AntAgent, FoodPatch, Nest, Obstacle


def agent_portrayal(agent):
    """
    Draw agents based on their 'state' property (active/inactive).
    Uses Matplotlib-compatible keywords.
    """
    portrayal: Dict[str, Any] = {"marker": "o"}
    
    if isinstance(agent, AntAgent):
        if agent.is_dead:
            return {}
        else:
            if agent.state == 'active':
                if agent.state_2 == 'carrying':
                    portrayal["color"] = "#12D400"  # Green
                    portrayal["size"] = 60
                else:
                    portrayal["color"] = "#FF0000"  # Red
                    portrayal["size"] = 60
            else:
                portrayal["color"] = "#333333"  # Dark Gray
                portrayal["size"] = 30
    elif isinstance(agent, FoodPatch):
        portrayal["marker"] = "s"
        if agent.state == 'full':
            portrayal["color"] = "#337329"
            portrayal["size"] = 100
        else:
            portrayal["color"] = "#FFFFFF"
            portrayal["size"] = 100
    elif isinstance(agent, Nest):
        portrayal = {"marker": "s", "color": "#541608", "size": 100}
    elif isinstance(agent, Obstacle):
        portrayal = {"marker": "s", "color": "#4A4A4A", "size":100}
    else:
        return
    return portrayal


def pheromone_agent_portrayal(agent):
    return {}


layer_portrayal = {
    "pher_food": {
        "colormap": "plasma",
        "alpha": 1.0,
        "colorbar": True,
        "vmin": 0,
        "vmax": 15,
    }
}

# Define grid size
GRID_WIDTH = 30
GRID_HEIGHT = 30

# Define Model Parameters for Sliders
model_params = {
    "seed": InputInt(
        label="Random Seed",
        value=42,
    ),
    # -----------------
    "N": Slider("Number of Ants", 25, 10, 100, 1),
    "width": GRID_WIDTH,
    "height": GRID_HEIGHT,
    "g": Slider("Gain (g)", 0.05, 0.0, 1.0, 0.05),
    "prob_spontaneous": Slider("Spontaneous Activation Prob.", 0.01, 0.0, 0.1, 0.005),
    "J_11": Slider("J_11 (Active on Active)", 1.0, 0.0, 2.0, 0.1),
    "J_12": Slider("J_12 (Inactive on Active)", 0.0, 0.0, 2.0, 0.1),
    "J_21": Slider("J_21 (Active on Inactive)", 0.0, 0.0, 2.0, 0.1),
    "J_22": Slider("J_22 (Inactive on Inactive)", 0.0, 0.0, 2.0, 0.1),
    "pher_dec": Slider("Pheromone Decay Rate", 0.05, 0.0, 1.0, 0.05),
    "pher_diff": Slider("Pheromone Diffusion Rate", 0.1, 0.0, 1.0, 0.05),
    "pher_drop": Slider("Amount of phermone dropped per", 3.0, 0.5, 5.0, 0.5),
    "nfp": Slider("Number of food patches", 2, 1, 10, 1),
    "fpp": Slider("Food per Patch", 50.0, 1.0, 100.0, 1.0),
}

# This loop for initial_params
initial_params = {}
for name, param in model_params.items():
    if hasattr(param, "value"):
        initial_params[name] = param.value
    elif hasattr(param, "kwargs") and "value" in param.kwargs:
        initial_params[name] = param.kwargs["value"]
    else:
        initial_params[name] = param

initial_params["seed"] = int(initial_params["seed"])

# Create the first model instance
initial_model = ColonyModel(**initial_params)


def renderer_post_process(ax):
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xticks([], minor=True)
    ax.set_yticks([], minor=True)

    ax.set_xlim(-0.5, GRID_WIDTH - 0.5)
    ax.set_ylim(-0.5, GRID_HEIGHT - 0.5)
    # ax.set_aspect("equal")


# Create the chart
chart1 = make_plot_component(["ActiveAntPercentage"])
chart2 = make_plot_component(["FoodDelivered"])
chart3 = make_plot_component(["AntsAlive"])

renderer_agents = SpaceRenderer(model=initial_model, backend="matplotlib")
renderer_agents.draw_agents(agent_portrayal)
renderer_agents.post_process = renderer_post_process


renderer_pheromone = SpaceRenderer(model=initial_model, backend="matplotlib")
renderer_pheromone.draw_propertylayer(layer_portrayal)

space_agents = create_space_component(renderer_agents)
space_pheromone = create_space_component(renderer_pheromone)

page = SolaraViz(
    model=initial_model,
    renderer=None,
    model_params=model_params,
    components=[space_agents, space_pheromone],
    name="Cole & Cheshire (1996) MCA Model"
)
app = page