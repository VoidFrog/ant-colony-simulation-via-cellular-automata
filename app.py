import mesa
from mesa.visualization import (
    SolaraViz, 
    Slider, 
    make_plot_component, 
    make_space_component
)
from solara import InputInt

from model import ColonyModel
from agent import AntAgent

def agent_portrayal(agent):
    """
    Draw agents based on their 'state' property (active/inactive).
    Uses Matplotlib-compatible keywords.
    """
    if not isinstance(agent, AntAgent):
        return

    portrayal = {"marker": "o"} # "o" is a circle

    if agent.state == 'active':
        portrayal["color"] = "#FF0000" # Red
        portrayal["s"] = 60 # 's' is size (area), not radius
    else:
        portrayal["color"] = "#333333" # Dark Gray
        portrayal["s"] = 30

    return portrayal

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
    "J_22": Slider("J_22 (Inactive on Inactive)", 0.0, 0.0, 2.0, 0.1)
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
chart = make_plot_component(
    ["ActiveAntPercentage"]
)

# Create the visualization grid component
grid = make_space_component(
    agent_portrayal
)

# Create the server instance
page = SolaraViz(
    model=initial_model,
    model_params=model_params,
    components=[grid, chart],
    name="Cole & Cheshire (1996) MCA Model"
)

# solara looks for this one, and if it's not present it looks for the page variable
# throws an error if more than 1 page is present, so this little trick should do the work
# even though we dont have more than 1 page, it's better to leave it as is 
app = page