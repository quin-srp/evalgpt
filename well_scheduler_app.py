
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import pulp
import plotly.express as px
import pandas as pd
from fastapi.responses import HTMLResponse

# Data models for request and response
class WellScheduleRequest(BaseModel):
    wells: List[str]
    timeframes: int
    capex: dict  # A dictionary of CAPEX costs for each well over the timeframes
    rig_limit: int  # Number of rigs available per timeframe

class WellScheduleResponse(BaseModel):
    well: str
    start_time: int
    finish_time: int

# Optimization logic
def optimize_well_schedule(wells, timeframes, capex, rig_limit):
    # Define the optimization problem
    problem = pulp.LpProblem("Well_Scheduling", pulp.LpMinimize)

    # Decision variables
    drill_vars = pulp.LpVariable.dicts("drill", (wells, range(1, timeframes + 1)), 0, 1, pulp.LpBinary)

    # Objective: Minimize CAPEX
    problem += pulp.lpSum([drill_vars[well][t] * capex[well][t-1] for well in wells for t in range(1, timeframes + 1)])

    # Constraints: Each well is drilled once
    for well in wells:
        problem += pulp.lpSum([drill_vars[well][t] for t in range(1, timeframes + 1)]) <= 1, f"Drill_{well}_once"

    # Constraints: Rig limit per timeframe
    for t in range(1, timeframes + 1):
        problem += pulp.lpSum([drill_vars[well][t] for well in wells]) <= rig_limit, f"Rig_Limit_{t}"

    # Solve the problem
    problem.solve()

    # Collect the results
    schedule = []
    for well in wells:
        for t in range(1, timeframes + 1):
            if pulp.value(drill_vars[well][t]) == 1:
                schedule.append({"well": well, "start_time": t, "finish_time": t+1})

    return schedule

# Create FastAPI app
app = FastAPI()

@app.post("/optimize-schedule/", response_model=List[WellScheduleResponse])
def optimize_schedule(request: WellScheduleRequest):
    result = optimize_well_schedule(request.wells, request.timeframes, request.capex, request.rig_limit)
    return result

# Visualization endpoint
@app.get("/schedule-visualization/")
def visualize_schedule():
    # Sample data from the optimization result
    schedule_data = {
        "Well": ['Well_1', 'Well_2', 'Well_3', 'Well_4', 'Well_5'],
        "Start": ['2024-01-01', '2024-02-15', '2024-03-01', '2024-03-20', '2024-04-01'],
        "Finish": ['2024-02-01', '2024-03-15', '2024-04-01', '2024-04-20', '2024-05-01'],
        "Resource": ['Rig_A', 'Rig_A', 'Rig_B', 'Rig_B', 'Rig_A']
    }

    df_schedule = pd.DataFrame(schedule_data)

    # Create a Gantt chart
    fig = px.timeline(df_schedule, x_start="Start", x_end="Finish", y="Well", color="Resource", title="Well Schedule")

    # Convert Plotly figure to HTML
    graph_html = fig.to_html(full_html=False)

    return HTMLResponse(content=f"<html><body>{graph_html}</body></html>", status_code=200)
