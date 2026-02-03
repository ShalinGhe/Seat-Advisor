import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from seatadvisor import seat_advisor_locations, load_priors_csv

DATA_PATH = "input/final_data.csv.gz"
PRIORS_PATH = "input/priors.csv"

WEEKDAY_OPTIONS = [
    ("Any", None),
    ("Monday", 0),
    ("Tuesday", 1),
    ("Wednesday", 2),
    ("Thursday", 3),
    ("Friday", 4),
    ("Saturday", 5),
    ("Sunday", 6),
]
TOD_OPTIONS = [
    ("Any", None),
    ("Morning", "morning"),
    ("Afternoon", "afternoon"),
    ("Evening", "evening"),
]

df = pd.read_csv(DATA_PATH, parse_dates=["t10"])
priors_dict, acc_dict = load_priors_csv(PRIORS_PATH)

def main():
    root = tk.Tk()
    root.title("SeatAdvisor")
    root.geometry("1550x720")
    root.minsize(1550, 720)

    outer = ttk.Frame(root, padding=12)
    outer.pack(fill="both", expand=True)
    outer.columnconfigure(0, weight=0)
    outer.columnconfigure(1, weight=1)
    outer.rowconfigure(0, weight=1)

    controls = ttk.Frame(outer, padding=(0, 0, 12, 0))
    controls.grid(row=0, column=0, sticky="ns")

    output = ttk.Frame(outer)
    output.grid(row=0, column=1, sticky="nsew")
    output.columnconfigure(0, weight=1)
    output.rowconfigure(3, weight=1)

    valley_var = tk.BooleanVar(value=True)
    hill_var = tk.BooleanVar(value=True)

    weekday_label_var = tk.StringVar(value="Any")
    tod_label_var = tk.StringVar(value="Any")
    exam_var = tk.BooleanVar(value=True)

    threshold_var = tk.StringVar(value="0.15")
    topn_var = tk.StringVar(value="5")

    user_is_hill_var = tk.StringVar(value="0")
    require_accessible_var = tk.BooleanVar(value=False)

    w_reach_var = tk.DoubleVar(value=0.25)
    w_air_var = tk.DoubleVar(value=0.25)
    w_light_var = tk.DoubleVar(value=0.25)
    w_outlet_var = tk.DoubleVar(value=0.25)

    ttk.Label(controls, text="SeatAdvisor Settings", font=("Helvetica", 16, "bold")).pack(anchor="w", pady=(0, 10))

    ttk.Label(controls, text="Campuses").pack(anchor="w")
    campus_frame = ttk.Frame(controls)
    campus_frame.pack(anchor="w", pady=(0, 10))
    ttk.Checkbutton(campus_frame, text="Valley", variable=valley_var).pack(side="left", padx=(0, 12))
    ttk.Checkbutton(campus_frame, text="Hill", variable=hill_var).pack(side="left")

    ttk.Label(controls, text="Your current campus").pack(anchor="w")
    base_frame = ttk.Frame(controls)
    base_frame.pack(anchor="w", pady=(0, 10))
    ttk.Radiobutton(base_frame, text="Valley", variable=user_is_hill_var, value="0").pack(side="left", padx=(0, 12))
    ttk.Radiobutton(base_frame, text="Hill", variable=user_is_hill_var, value="1").pack(side="left")

    ttk.Label(controls, text="Weekday").pack(anchor="w")
    weekday_dropdown = ttk.Combobox(
        controls, textvariable=weekday_label_var,
        values=[x[0] for x in WEEKDAY_OPTIONS],
        state="readonly", width=20
    )
    weekday_dropdown.pack(anchor="w", pady=(0, 10))
    weekday_dropdown.set("Any")

    ttk.Label(controls, text="Time of day").pack(anchor="w")
    tod_dropdown = ttk.Combobox(
        controls, textvariable=tod_label_var,
        values=[x[0] for x in TOD_OPTIONS],
        state="readonly", width=20
    )
    tod_dropdown.pack(anchor="w", pady=(0, 10))
    tod_dropdown.set("Any")

    ttk.Checkbutton(controls, text="Exam period", variable=exam_var).pack(anchor="w", pady=(0, 6))
    ttk.Checkbutton(controls, text="Require wheelchair accessibility", variable=require_accessible_var).pack(anchor="w", pady=(0, 14))

    ttk.Label(controls, text="Stress threshold").pack(anchor="w")
    ttk.Entry(controls, textvariable=threshold_var, width=12).pack(anchor="w", pady=(0, 10))

    ttk.Label(controls, text="Top N results").pack(anchor="w")
    ttk.Entry(controls, textvariable=topn_var, width=12).pack(anchor="w", pady=(0, 14))

    ttk.Label(controls, text="Priors", font=("Helvetica", 13, "bold")).pack(anchor="w", pady=(0, 8))

    def slider_row(label, var):
        row = ttk.Frame(controls)
        row.pack(anchor="w", pady=(0, 8), fill="x")
        ttk.Label(row, text=label, width=12).pack(side="left")
        s = ttk.Scale(row, from_=0.0, to=1.0, variable=var)
        s.pack(side="left", fill="x", expand=True, padx=(6, 6))
        v = ttk.Label(row, width=6)
        v.pack(side="right")
        return v

    v_reach = slider_row("Reachability", w_reach_var)
    v_air = slider_row("Air quality", w_air_var)
    v_light = slider_row("Light", w_light_var)
    v_outlet = slider_row("Power outlets", w_outlet_var)

    weights_label = ttk.Label(controls, text="Normalized: 0.25 / 0.25 / 0.25 / 0.25")
    weights_label.pack(anchor="w", pady=(0, 10))

    def normalized_weights():
        w = [float(w_reach_var.get()), float(w_air_var.get()), float(w_light_var.get()), float(w_outlet_var.get())]
        w = [max(0.0, min(1.0, x)) for x in w]
        s = sum(w)
        if s <= 0.0:
            w = [0.25, 0.25, 0.25, 0.25]
        else:
            w = [x / s for x in w]
        return tuple(w)

    def update_weight_labels(*_):
        w = normalized_weights()
        v_reach.config(text=f"{w[0]:.2f}")
        v_air.config(text=f"{w[1]:.2f}")
        v_light.config(text=f"{w[2]:.2f}")
        v_outlet.config(text=f"{w[3]:.2f}")
        weights_label.config(text=f"Normalized: {w[0]:.2f} / {w[1]:.2f} / {w[2]:.2f} / {w[3]:.2f}")

    for var in (w_reach_var, w_air_var, w_light_var, w_outlet_var):
        var.trace_add("write", update_weight_labels)
    update_weight_labels()

    run_btn = ttk.Button(controls, text="Run SeatAdvisor")
    run_btn.pack(anchor="w", pady=(10, 0), fill="x")

    ttk.Label(output, text="Recommendations", font=("Helvetica", 16, "bold")).grid(row=0, column=0, sticky="w")
    status_var = tk.StringVar(value="Ready.")
    ttk.Label(output, textvariable=status_var).grid(row=1, column=0, sticky="w", pady=(4, 10))

    cols = ("location", "building", "final", "sas", "prior", "csi", "dist", "n")
    tree = ttk.Treeview(output, columns=cols, show="headings", height=18)

    headings = [
        ("location", "Location", 520),
        ("building", "Building", 220),
        ("final", "Final score", 90),
        ("sas", "Seat score", 90),
        ("prior", "Prior", 90),
        ("csi", "Crowding risk", 90),
        ("dist", "Campus switch", 70),
        ("n", "N", 90),
    ]

    for key, title, width in headings:
        tree.heading(key, text=title)
        tree.column(key, width=width, anchor="w" if key in ("location", "building") else "center")

    yscroll = ttk.Scrollbar(output, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=yscroll.set)

    tree.grid(row=3, column=0, sticky="nsew")
    yscroll.grid(row=3, column=1, sticky="ns")

    def get_weekday_value(label):
        for lab, val in WEEKDAY_OPTIONS:
            if lab == label:
                return val
        return None

    def get_tod_value(label):
        for lab, val in TOD_OPTIONS:
            if lab == label:
                return val
        return None

    def clear_table():
        for item in tree.get_children():
            tree.delete(item)

    def run():
        try:
            campuses = []
            if valley_var.get():
                campuses.append(0)
            if hill_var.get():
                campuses.append(1)
            if not campuses:
                messagebox.showerror("Invalid selection", "Select at least one campus.")
                return

            status_var.set("Running...")
            root.update_idletasks()

            weekday_val = get_weekday_value(weekday_label_var.get())
            tod_val = get_tod_value(tod_label_var.get())

            thr = float(threshold_var.get())
            topn = int(topn_var.get())

            user_is_hill = int(user_is_hill_var.get())
            req_acc = bool(require_accessible_var.get())
            pw = normalized_weights()

            res = seat_advisor_locations(
                df,
                campuses=campuses,
                weekday=weekday_val,
                time_of_day=tod_val,
                exam_period=bool(exam_var.get()),
                availability_threshold=thr,
                user_is_hill=user_is_hill,
                require_accessible=req_acc,
                topn=topn,
                prior_weights=pw,
                priors=priors_dict,
                acc=acc_dict,
            )

            clear_table()

            if res.empty:
                status_var.set("No results (try fewer filters).")
                return

            status_var.set(f"Done. Showing top {len(res)}.")
            for _, r in res.iterrows():
                tree.insert(
                    "",
                    "end",
                    values=(
                        r["location_name"],
                        r["building_name"],
                        f"{r['final_score']:.3f}",
                        f"{r['sas_score']:.3f}",
                        f"{r['prior_score']:.3f}",
                        f"{r['capacity_stress_index']:.3f}",
                        f"{r['distance_penalty']:.0f}",
                        int(r["n_obs"]),
                    ),
                )

        except Exception as e:
            status_var.set("Error.")
            messagebox.showerror("SeatAdvisor Error", str(e))

    run_btn.configure(command=run)
    root.mainloop()

if __name__ == "__main__":
    main()
