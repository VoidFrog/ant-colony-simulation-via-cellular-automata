# Symulacja kolonii mrówek w oparciu o model aktywności ruchowej Leptothorax Allardycei w celu porównania wytworzonych fenotypów społecznych z danymi obserwacyjnymi

**English Title:** Ant Colony Simulation Based on the Activity Model of *Leptothorax Allardycei* to Compare Generated Social Phenotypes with Observational Data.

## Project Description  MESA

This project is an agent-based simulation built in Python using the **MESA** framework (specifically MESA 3.x with the **Solara** visualization backend). The goal is to model and understand the emergence of collective activity cycles ("social phenotypes") in ant colonies.

The simulation is based on the **Mobile Cellular Automata (MCA)** model described in the 1996 paper by Blaine J. Cole and David Cheshire, which specifically studied the activity patterns of *Leptothorax allardycei* ants.

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