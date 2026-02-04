# Seat Advisor

Creating a seat recommendation system for libraries in Tübingen during exam phases to support planning-oriented decision making.

---

## Overview

This project provides a reproducible pipeline that cleans, merges, analyses, and visualizes seat availability data from libraries in and around Tübingen. The goal is to move beyond real-time checks and provide planning metrics and personalized recommendations for library choice during high-demand periods (exam phases).

## Repository Structure

- `input/`: Raw data sources (SQL dumps, `locations.csv`, `priors.csv`).
- `seatadvisor_analysis/`: Core notebooks for cleaning, merging, and statistical analysis.
- `seatadvisor_app/`: Python source code for the recommendation GUI.
- `datasanity/`: Quality checks and missing value inspections.
- `plots/`: Visualization scripts and final figures.
- `data/`: Processed and merged CSV files (e.g., `final_data.csv`).
- `archive/`: Old or deprecated notebooks.

## Data Sources

- `seatfinder_dump.sql` (2016–2024) with four relevant tables:
  - `public.locations`
  - `public.seat_estimates`
  - `public.wlan_clients`
  - `public.manual_counts`

Use `seatadvisor_analysis/Seatfinder_Sql_to_csv.ipynb` to create the initial CSV files.

## Data Model

**Fact tables (time series):**
- Seat estimates
- Manual counts (ground truth)
- WLAN clients (proxy for occupancy)

**Dimension tables (static):**
- Locations (with manually verified opening hours)

**Keys:**
- `location_id`
- `t10` (10-minute aggregated time bin)

---

## Methodology: Key Metrics

This project moves beyond real-time checks by calculating two planning metrics used for recommendations:

1. **Capacity Stress Index (CSI)**
   - Definition: The proportion of time a location operates at >85% capacity.
   - Goal: Identifies libraries that are structurally overcrowded vs. "hidden gems".

2. **SeatAdvisor Score (SAS)**
   - A composite score for personalized recommendations.
   - Formula: SAS = (1 − λ) · ((1 − CSI) + μ − σ − d) + λ · p
     - Objective factors: Capacity Stress (CSI), Mean Availability (μ), Predictability (σ), Distance (d).
     - Subjective priors (p): User weights for Light, Air Quality, Power Outlets, Accessibility.

---

## Preprocessing and Merging

Work through the notebooks in `seatadvisor_analysis/`.

### Step 1: Cleaning
- Notebook: `Seatfinder_DataCleaning.ipynb`
- Opening hours: Adds manually verified opening/closing times from `input/locations.csv`.
- Filtering: Removes data outside opening hours to prevent "ghost user" bias.
- Output: Saves cleaned intermediate files to `data/` (e.g., `estimate_during_opening_hours.csv`).

### Step 2: Merging
- Notebook: `Seatfinder_DataMerging.ipynb`
- Aggregation: Creates 10-minute time bins (`t10`) for all streams.
- Enrichment: Adds `building_id`, `is_hill` (campus flag), and other metadata.
- COVID filter: Removes data from `2020-03-17` to `2022-04-03` due to atypical patterns.
- Final output: Saves the master dataset as `data/final_data.csv.gz`.

---

## Usage Example

1. Set up the Environment
Create a virtual environment and install the required libraries (Pandas, Numpy, Streamlit, etc.). The project expects a local virtual environment named `.venv`.

Recommended commands (macOS / Linux):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

Troubleshooting:

- If `pip` is not found after activating the venv (e.g. `zsh: command not found: pip`), use `python -m pip` instead of `pip`.
- If the venv lacks pip, run:

```bash
python -m ensurepip --upgrade
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```
- If your system uses the `python` command for a different interpreter, prefer `python3` when creating the venv: `python3 -m venv .venv`.

Note: On some macOS setups `python3` is the correct system interpreter — the commands above explicitly use `python3` for creating the venv and `python -m pip` for installing packages inside the activated environment.

2. Data
The repository contains the compressed datasets (.gz).

Note: The code has been updated to read the compressed files directly. Manual unzipping is not required.

3. Run SeatAdvisor
Run the application:


# Start the GUI (if local)
python seatadvisor_app/seatadvisor_gui.py
Python:

```python
import pandas as pd

# Load the final processed data
df = pd.read_csv("data/final_data.csv.gz")
print(df.head())
```

Running the GUI (what to expect)

- The GUI is a small desktop application implemented with `tkinter` and opens in a separate window when you run `python seatadvisor_app/seatadvisor_gui.py`.
- By default it reads data from `input/final_data.csv.gz` and priors from `input/priors.csv`. Place your prepared `final_data.csv.gz` and `priors.csv` files under the `input/` directory to use them.
- Controls available in the window:
  - Campus filters (Valley / Hill)
  - Your current campus (for reachability/distance penalty)
  - Weekday selector (Any, Monday ... Sunday)
  - Time-of-day selector (Any, Morning, Afternoon, Evening)
  - Exam period toggle and wheelchair accessibility requirement
  - Stress threshold and Top-N results
  - Priors sliders (Reachability, Air quality, Light, Power outlets) — these are normalized before use

- The GUI computes recommendations using the processed dataset and the chosen priors. You can run it for any weekday or time-of-day combination and adjust priors interactively; results are shown in the recommendations table.
- To change the data/priors paths, edit `DATA_PATH` and `PRIORS_PATH` at the top of `seatadvisor_app/seatadvisor_gui.py`.

---

## Notes & Contact

If you have questions or want to contribute, please open an issue or a pull request.


<!-- End of README -->