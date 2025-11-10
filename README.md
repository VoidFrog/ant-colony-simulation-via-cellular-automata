# Symulacja kolonii mrówek w oparciu o model aktywności ruchowej Leptothorax Allardycei w celu porównania wytworzonych fenotypów społecznych z danymi obserwacyjnymi

**English Title:** Ant Colony Simulation Based on the Activity Model of *Leptothorax Allardycei* to Compare Generated Social Phenotypes with Observational Data.

## Project Description  MESA

This project is an agent-based simulation built in Python using the **MESA** framework (specifically MESA 3.x with the **Solara** visualization backend). The goal is to model and understand the emergence of collective activity cycles ("social phenotypes") in ant colonies.

The simulation is based on the **Mobile Cellular Automata (MCA)** model described in the 1996 paper by Blaine J. Cole and David Cheshire, which specifically studied the activity patterns of *Leptothorax allardycei* ants.

## Model Description

The model itself represents the inside of an ant colony in which the currently each cell of the space of the colony can be occupied by 1 ant, it’s neighbors are the 8 spaces surrounding the cell, also known as Moore neighborhood. The model’s goal is to emulate the creation of social phenotypes, of which two are differentiated: active and inactive, which are determined by each ant’s activity level.

The activity level is determined based on two factors. The first, referred to as self-interaction which Is determined by a gain term determined by model by model basis and the current activity level of the ant. The second is the interaction term, determined by the sum of the multiplication of the interaction matrix and activity levels of all neighboring ants.

The interaction matrix is a 2x2 square matrix, which determines how ants of either state affect other ants depending on their state.

The activity level in the next unit of time is equal to a hyperbolic tangent of the sum of the interaction term multiplied by the gain term and the self-interaction term. The hyperbolic tangent is used so as to constrain the activity level in between -1 and 1.

One of the core limitations of the model as implemented in the research paper is the fact that it assumes one ant per grid coordinate. This in turn may cause dissonance between the simulation and reality as observed in the experimental research conducted by Cole and Cheshire for the 1996 paper as some ants may group in close enough spaces that they couldn’t be differentiated as being on separate grid coordinates.

One more possible problem displays itself in the data gathered by Cole and Cheshire (1996). The experiment and model simulation used a low sample size of at most 15 ants which could again cause a significant difference then when observed in a larger but natural setting such as a colony.  

## Core Mathematical Model 

This simulation implements the continuous activity model from the **Cole & Cheshire (1996)** paper. Each ant agent has a continuous **activity level ($A_t$)** from -1 (inactive) to +1 (active). An ant is *defined* as "active" only when its $A_t > 0$.

The activity level for the next time step ($A_{t+1}$) is calculated using the following core equation:

$$A_{t+1} = \tanh( [g*\sum(J_{ij} \cdot A_{kt})] + S_t )$$

Currently we use a modified version as it looks much better:
$$A_{t+1} = \tanh( [g*\sum(J_{ij} \cdot A_{kt})] + S_t*g )$$

Where:
* **$\Sigma(J_{ij} \cdot A_{kt})$** is the **Interaction Term**. This is the sum of activity from all neighbors, modified by the `J` interaction matrix. 

* **$S_t$** is the **Self-Interaction (Decay) Term**, $S_t = g \cdot A_t$. This term is weak (scaled by `g=0.1`) and causes an isolated ant's activity to naturally decay.

* **$\tanh$** is the hyperbolic tangent function, used to keep the final activity level bounded in range $(-1, 1)$.

## Technology Stack 

* Python 3
* MESA 3.x (with Solara)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/VoidFrog/ant-colony-simulation-via-cellular-automata.git
    cd ant-colony-simulation-via-cellular-automata
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv your_venv_name
    
    .\\your_venv_name\\Scripts\\activate  # On Windows
    source your_venv_name/bin/activate  # On macOS/Linux
    ```

3.  **Install the required libraries:**
    ```bash
    pip install -r requirements.txt
    ```

## How to Run the Simulation 🚀

From the project's root directory (with your `venv` activated), run:

```bash
solara run app.py
```