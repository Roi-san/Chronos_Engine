import sys, os, io, contextlib
root = sys.argv[1]; sys.path[:0] = [root, os.path.join(root, "tests")]; os.chdir(root)
with contextlib.redirect_stdout(io.StringIO()):
    from test_kairos_v2_direction import _run, _placed, _commitment, SLEEP
GYM = {"name": "Gym", "type": "habit", "duration": "60m", "frequency": "daily"}
MINI = {"name": "Mobility", "type": "habit", "duration": "20m", "mini_of": "Gym"}
SETTINGS = {
 "settings/status_settings.yml": {"Status_Settings": [{"Name": "Health", "Rank": 1}, {"Name": "Place", "Rank": 2}, {"Name": "Energy", "Rank": 3}]},
 "settings/health_settings.yml": {"Health_Settings": {"Excellent": {"value": 1}, "Good": {"value": 2}, "Fair": {"value": 3}, "Poor": {"value": 4}, "Critical": {"value": 5}}},
 "settings/energy_settings.yml": {"Energy_Settings": {"High": {"value": 1}, "Medium": {"value": 2}, "Low": {"value": 3}, "Exhausted": {"value": 4}}},
}
SICK = {"health": "poor", "energy": "low"}
GOOD = {"health": "good", "energy": "high"}
MED = {"health": "good", "energy": "medium"}
def req(**r): return {**GYM, "status_requirements": r}
CASES = [
 ("A  no requirements, sick day", {"habits/g.yml": GYM}, SICK),
 ("B  needs energy high, no mini, sick", {"habits/g.yml": req(energy="high")}, SICK),
 ("B2 needs energy high, no mini, good", {"habits/g.yml": req(energy="high")}, GOOD),
 ("C  needs energy [high,medium], medium day", {"habits/g.yml": req(energy=["high","medium"])}, MED),
 ("D  needs energy high + mini, sick", {"habits/g.yml": req(energy="high"), "habits/m.yml": MINI}, SICK),
 ("D2 needs energy high + mini, good", {"habits/g.yml": req(energy="high"), "habits/m.yml": MINI}, GOOD),
 ("D3 needs energy MEDIUM + mini, HIGH-energy day", {"habits/g.yml": req(energy="medium"), "habits/m.yml": MINI}, GOOD),
 ("E  needs high + mini needs medium, sick(low)", {"habits/g.yml": req(energy="high"), "habits/m.yml": {**MINI, "status_requirements": {"energy": "medium"}}}, SICK),
 ("F  'low-energy item' (needs low), HIGH day", {"habits/g.yml": {**req(energy="low"), "name":"Gym"}}, GOOD),
 ("F2 'low-energy item' + mini, HIGH day", {"habits/g.yml": req(energy="low"), "habits/m.yml": MINI}, GOOD),
 ("G  needs health good, no mini, last-chance commitment, sick", {"habits/g.yml": {**req(health=["excellent","good"]), "frequency":"monday"}, "commitments/c.yml": _commitment(times=4, targets=[{"type":"habit","name":"Gym"}])}, SICK),
 ("H  TASK due today needs energy high, no mini, sick", {"tasks/t.yml": {"name":"Gym","type":"task","duration":"60m","due_date":"2026-04-16","status_requirements":{"energy":"high"}}}, SICK),
 ("I  template fixed slot 18:00 needs energy high, sick", {"habits/g.yml": {**req(energy="high"), "frequency": None}, "days/plain_day.yml": {"name":"Plain Day","type":"day","children":[SLEEP, {"name":"Gym","type":"habit","start_time":"18:00","duration":60,"status_requirements":{"energy":"high"}}]}}, SICK),
 ("K  needs energy high, status never set", {"habits/g.yml": req(energy="high")}, None),
 ("L  needs energy 'hgih' (typo), sick", {"habits/g.yml": req(energy="hgih")}, SICK),
 ("M  needs focus laser (dimension not declared), sick", {"habits/g.yml": req(focus="laser")}, SICK),
 ("P  needs health good only, fair day (1 step short)", {"habits/g.yml": req(health="good")}, {"health": "fair", "energy": "high"}),
 ("N  needs energy high, medium day (1 step short)", {"habits/g.yml": req(energy="high")}, MED),
]
for label, files, status in CASES:
    files = {**SETTINGS, **files}; day = files.pop("days/plain_day.yml", None)
    with contextlib.redirect_stdout(io.StringIO()):
        s = _run(files, status=status, day=day)
    placed = _placed(s)
    got = [n for n in ("Gym", "Mobility") if n in placed]
    print(f"{label:58s} -> {', '.join(got) or 'NOTHING'}")
