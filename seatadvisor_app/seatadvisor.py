import pandas as pd
import numpy as np
from typing import Optional, Iterable, Literal, Dict, Tuple

TimeOfDay = Optional[Literal["morning", "afternoon", "evening"]]

SAS_WEIGHTS = {"stress": 0.40, "mean": 0.30, "var": 0.20, "dist": 0.10}
if not (abs(sum(SAS_WEIGHTS.values()) - 1.0) < 1e-9 and all(0.0 <= v <= 1.0 for v in SAS_WEIGHTS.values())):
    raise ValueError("SAS_WEIGHTS must be in [0,1] and sum to 1.")

LAMBDA_PRIOR = 0.25

BUILDING_NAME_MAP = {
    1: "Ammerbau",
    2: "Waschhalle",
    3: "PCB",
    4: "Bonatzbau",
    5: "Bereichsbibliothek",
    6: "Lernzentrum Tal",
    7: "Lernzentrum Morgenstelle",
}

EXAM_WEEKS = set(range(3, 9)) | set(range(29, 33))  # KW 3–8 and KW 29–32

def _tod_from_hour(h: int) -> str:
    if h < 12:
        return "morning"
    if h < 17:
        return "afternoon"
    return "evening"

def capacity_stress_index(df: pd.DataFrame, threshold: float = 0.15) -> float:
    if len(df) == 0:
        return np.nan
    return (df["relative_availability"] <= threshold).mean()

def _normalize_prior_weights(w_reach: float, w_air: float, w_light: float, w_outlet: float) -> Tuple[float, float, float, float]:
    ws = np.array([w_reach, w_air, w_light, w_outlet], dtype=float)
    ws = np.clip(ws, 0.0, 1.0)
    s = float(ws.sum())
    if s <= 0.0:
        return 0.25, 0.25, 0.25, 0.25
    ws = ws / s
    return float(ws[0]), float(ws[1]), float(ws[2]), float(ws[3])

def load_priors_csv(path: str) -> Tuple[Dict[int, Dict[str, float]], Dict[int, int]]:
    pri = pd.read_csv(path).copy()
    pri.columns = [c.strip().lower() for c in pri.columns]

    def pick(candidates):
        for c in candidates:
            if c in pri.columns:
                return c
        return None

    id_col = pick(["location_id", "loc_id", "id", "location"])
    acc_col = pick(["acc", "accessible", "is_accessible", "wheelchair", "barrierfree"])

    reach_col = pick(["reach", "reachability", "bus", "accessibility_score"])
    air_col = pick(["air", "airquality", "air_quality"])
    light_col = pick(["light", "lighting"])
    outlet_col = pick(["outlet", "outlets", "power", "sockets", "socket"])

    if id_col is None:
        raise ValueError("priors.csv: no location id column found (e.g. location_id / id).")
    if acc_col is None:
        raise ValueError("priors.csv: no accessibility column found (e.g. acc).")
    if any(c is None for c in [reach_col, air_col, light_col, outlet_col]):
        raise ValueError("priors.csv: need columns for reach/air/light/outlet (names can vary).")

    pri[id_col] = pd.to_numeric(pri[id_col], errors="coerce")
    pri = pri.dropna(subset=[id_col]).copy()
    pri["location_id"] = pri[id_col].astype(int)

    def to_norm01(v):
        x = pd.to_numeric(v, errors="coerce")
        if pd.isna(x):
            return np.nan
        x = float(x)
        x = min(10.0, max(1.0, x))
        return x / 10.0

    priors: Dict[int, Dict[str, float]] = {}
    acc: Dict[int, int] = {}

    for _, r in pri.iterrows():
        loc = int(r["location_id"])
        priors[loc] = {
            "reach": float(to_norm01(r[reach_col])),
            "air": float(to_norm01(r[air_col])),
            "light": float(to_norm01(r[light_col])),
            "outlet": float(to_norm01(r[outlet_col])),
        }
        a = pd.to_numeric(r[acc_col], errors="coerce")
        acc[loc] = int(1 if pd.notna(a) and int(a) == 1 else 0)

    return priors, acc

def _prior_score(loc_id: int, w: Tuple[float, float, float, float], priors: Dict[int, Dict[str, float]]) -> float:
    p = priors.get(int(loc_id))
    if p is None or any(pd.isna(p[k]) for k in ["reach", "air", "light", "outlet"]):
        return 0.5
    return (
        w[0] * float(p["reach"])
        + w[1] * float(p["air"])
        + w[2] * float(p["light"])
        + w[3] * float(p["outlet"])
    )

def seat_advisor_locations(
    data: pd.DataFrame,
    campuses: Optional[Iterable[int]] = None,
    weekday: Optional[int] = None,
    time_of_day: TimeOfDay = None,
    exam_period: bool = True,
    availability_threshold: float = 0.15,
    user_is_hill: Optional[int] = None,
    require_accessible: bool = False,
    topn: Optional[int] = None,
    min_obs: int = 200,
    prior_weights: Tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25),
    priors: Optional[Dict[int, Dict[str, float]]] = None,
    acc: Optional[Dict[int, int]] = None,
) -> pd.DataFrame:
    df = data.copy()

    required = {"t10", "building_id", "location_id", "is_hill", "relative_availability"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df["t10"] = pd.to_datetime(df["t10"], errors="coerce")
    df = df.dropna(subset=["t10"]).copy()

    df["relative_availability"] = pd.to_numeric(df["relative_availability"], errors="coerce")
    df = df.dropna(subset=["relative_availability"]).copy()
    df["relative_availability"] = df["relative_availability"].clip(0, 1)

    df["weekday"] = df["t10"].dt.weekday
    df["hour"] = df["t10"].dt.hour
    df["time_of_day"] = df["hour"].map(_tod_from_hour)

    df["iso_week"] = df["t10"].dt.isocalendar().week.astype(int)

    if campuses is not None:
        campuses = list(campuses)
        df = df[df["is_hill"].isin(campuses)]

    if weekday is not None:
        df = df[df["weekday"] == weekday]

    if time_of_day is not None:
        df = df[df["time_of_day"] == time_of_day]

    if exam_period:
        df = df[df["iso_week"].isin(EXAM_WEEKS)]
    else:
        df = df[~df["iso_week"].isin(EXAM_WEEKS)]

    if require_accessible:
        if acc is None:
            raise ValueError("require_accessible=True but no acc dict provided from priors.csv")
        df = df[df["location_id"].map(lambda x: acc.get(int(x), 0)) == 1]

    has_longname = "longname" in df.columns

    w_reach, w_air, w_light, w_outlet = _normalize_prior_weights(*prior_weights)
    w_prior = (w_reach, w_air, w_light, w_outlet)

    rows = []
    for loc_id, g in df.groupby("location_id"):
        if len(g) < min_obs:
            continue

        stress = capacity_stress_index(g, availability_threshold)
        mu = float(g["relative_availability"].mean())
        std_av = g["relative_availability"].std()
        sigma = 0.0 if pd.isna(std_av) else min(1.0, 2.0 * float(std_av))

        if user_is_hill is None:
            d = 0.0
        else:
            d = float(int(g["is_hill"].iloc[0]) != int(user_is_hill))

        sas = (
            SAS_WEIGHTS["stress"] * (1.0 - float(stress))
            + SAS_WEIGHTS["mean"] * mu
            - SAS_WEIGHTS["var"] * sigma
            - SAS_WEIGHTS["dist"] * d
        )

        if priors is None:
            prior = 0.5
        else:
            prior = _prior_score(int(loc_id), w_prior, priors=priors)

        final = (1.0 - LAMBDA_PRIOR) * sas + LAMBDA_PRIOR * prior

        b_id = g["building_id"].iloc[0]
        b_id_int = int(b_id) if pd.notna(b_id) else None
        building_name = BUILDING_NAME_MAP.get(b_id_int, f"Building {b_id_int}" if b_id_int is not None else "Unknown")
        location_name = str(g["longname"].iloc[0]) if has_longname else f"Location {int(loc_id)}"

        rows.append({
            "location_name": location_name,
            "location_id": int(loc_id),
            "building_name": building_name,
            "final_score": float(final),
            "sas_score": float(sas),
            "prior_score": float(prior),
            "capacity_stress_index": float(stress),
            "mean_relative_availability": float(mu),
            "sigma_norm": float(sigma),
            "distance_penalty": float(d),
            "n_obs": int(len(g)),
        })

    res = pd.DataFrame(rows)
    if res.empty:
        return res

    res = res.sort_values("final_score", ascending=False).reset_index(drop=True)
    if topn is not None:
        return res.head(int(topn)).reset_index(drop=True)
    return res

