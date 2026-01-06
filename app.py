from typing import Any, Dict
import mesa
from mesa.visualization import (
    SolaraViz, 
    Slider,
    SpaceRenderer,
    make_plot_component,
    make_space_component
)
from mesa.visualization.components import PropertyLayerStyle

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


def propertylayer_portrayal(layer):
    if layer.name == "pher_food":
        return PropertyLayerStyle(color="blue", alpha=1.4, vmin=0, vmax=15, colorbar=True)

# Define grid size
GRID_WIDTH = 50
GRID_HEIGHT = 50

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
    "g": Slider("Gain (g)", 0.05, 0.0, 1.0, 0.05),#type: ignore
    "prob_spontaneous": Slider("Spontaneous Activation Prob.", 0.01, 0.0, 0.1, 0.005),#type: ignore
    "J_11": Slider("J_11 (Active on Active)", 1.0, 0.0, 2.0, 0.1),#type: ignore
    "J_12": Slider("J_12 (Inactive on Active)", 0.0, 0.0, 2.0, 0.1),#type: ignore
    "J_21": Slider("J_21 (Active on Inactive)", 0.0, 0.0, 2.0, 0.1),#type: ignore
    "J_22": Slider("J_22 (Inactive on Inactive)", 0.0, 0.0, 2.0, 0.1),#type: ignore
    "pher_dec": Slider("Pheromone Decay Rate", 0.1, 0.0, 1.0, 0.05),#type: ignore
    "pher_diff": Slider("Pheromone Diffusion Rate", 0.1, 0.0, 1.0, 0.05),#type: ignore
    "pher_drop": Slider("Amount of phermone dropped per", 1.0, 0.5, 3.0, 0.5),#type: ignore
    "nfp": Slider("Number of food patches", 2, 1, 10, 1),#type: ignore
    "fpp": Slider("Food per Patch", 10.0, 1.0, 20.0, 1.0),#type: ignore
    "noise": Slider("Probability of random movement when not carrying food", 0.0, 0.0,0.5,0.01),#type: ignore
    "sr": Slider("Sensing radius", 1.0, 1.0, 5.0, 1.0)#type: ignore
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

# Create the chart
chart1 = make_plot_component(
    ["ActiveAntPercentage"]
)
chart2 = make_plot_component(
    ["FoodDelivered"]
)
chart3 = make_plot_component(
    ["AntsAlive"]
)

# Create the visualization grid component
# grid = make_space_component(
#     agent_portrayal
# )

renderer = SpaceRenderer(model=initial_model, backend="matplotlib")
renderer.draw_agents(agent_portrayal)
renderer.draw_propertylayer(propertylayer_portrayal)

# Create the server instance
page = SolaraViz(
    model=initial_model,
    renderer=renderer,
    model_params=model_params,
    components=[chart1, chart2, chart3], #type: ignore
    name="Cole & Cheshire (1996) MCA Model"
)

# solara looks for this one, and if it's not present it looks for the page variable
# throws an error if more than 1 page is present, so this little trick should do the work
# even though we dont have more than 1 page, it's better to leave it as is 
app = page