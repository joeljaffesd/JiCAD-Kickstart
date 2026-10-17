"""Prototype of a one-click "Export for JLC": builds <project>/JLC_Order/ with gerbers + drills, the gerber zip,
a JLC BOM and a JLC CPL, using kicad-cli only.

usage: python3 jlc_order.py <project_dir> [--pcb BOARD] [--sch SCHEMATIC] [--name NAME]
  --pcb/--sch let you export from a snapshot (e.g. Joel's unsaved GUI state saved with SaveDocumentToString
  into a scratch copy of the project) while still writing JLC_Order/ into the real project.

Settings follow JLC's KiCad guide: Protel extensions, no X2 / netlist attributes, soldermask subtracted from
silkscreen, Excellon mm / decimal / absolute origin, PTH and NPTH in separate files, alternate oval-hole mode.
"""
import argparse, csv, glob, io, os, shutil, subprocess, zipfile

CLI = os.environ.get("KICAD_CLI", "/Users/joeljaffesd/Desktop/SKNKWRKS/JiCAD/build/install/KiCad.app/Contents/MacOS/kicad-cli")
LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"
LCSC_FIELDS = ("LCSC", "LCSC Part #", "JLCPCB Part #", "Supplier Part")


def run(*args):
    r = subprocess.run([CLI, *args], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"kicad-cli {' '.join(args[:3])} failed:\n{r.stdout}\n{r.stderr}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--pcb"); ap.add_argument("--sch"); ap.add_argument("--name")
    a = ap.parse_args()
    proj = os.path.abspath(a.project)
    name = a.name or os.path.basename(glob.glob(proj + "/*.kicad_pro")[0])[:-len(".kicad_pro")]
    pcb = a.pcb or f"{proj}/{name}.kicad_pcb"
    sch = a.sch or f"{proj}/{name}.kicad_sch"
    out = f"{proj}/JLC_Order"
    gdir = f"{out}/gerbers"
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(gdir)

    # ---- fab: gerbers + drills + zip
    run("pcb", "export", "gerbers", pcb, "-o", gdir + "/", "--layers", LAYERS,
        "--no-x2", "--no-netlist", "--subtract-soldermask", "--check-zones")
    run("pcb", "export", "drill", pcb, "-o", gdir + "/", "--format", "excellon", "--excellon-units", "mm",
        "--excellon-zeros-format", "decimal", "--drill-origin", "absolute", "--excellon-oval-format", "alternate",
        "--excellon-separate-th")
    zpath = f"{out}/{name}_gerbers.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gdir)):
            z.write(f"{gdir}/{f}", f)

    # ---- assembly: BOM (one row per Value+Footprint+LCSC), only parts that carry an LCSC number
    raw = f"{out}/.bom_raw.csv"
    present = [f for f in LCSC_FIELDS if f'(property "{f}"' in open(sch).read()]
    lcsc = present[0] if present else "LCSC"
    run("sch", "export", "bom", sch, "-o", raw, "--fields", f"Value,Reference,Footprint,{lcsc},${{QUANTITY}}",
        "--labels", "Comment,Designator,Footprint,LCSC Part #,Qty", "--group-by", f"Value,Footprint,{lcsc}",
        "--exclude-dnp", "--ref-range-delimiter", "")
    rows = list(csv.DictReader(open(raw)))
    os.remove(raw)
    bom, skipped = [], []
    for r in rows:
        r["Footprint"] = r["Footprint"].split(":")[-1]
        (bom if r["LCSC Part #"].strip() else skipped).append(r)
    with open(f"{out}/{name}_BOM_JLC.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Comment", "Designator", "Footprint", "LCSC Part #"], extrasaction="ignore")
        w.writeheader(); w.writerows(bom)
    assembled = {d.strip() for r in bom for d in r["Designator"].split(",")}

    # ---- assembly: CPL for exactly the BOM's designators (board_only parts never reach the pos file)
    pos = run("pcb", "export", "pos", pcb, "-o", f"{out}/.pos.csv", "--format", "csv", "--units", "mm",
              "--side", "both", "--exclude-dnp")
    prow = list(csv.DictReader(open(f"{out}/.pos.csv")))
    os.remove(f"{out}/.pos.csv")
    with open(f"{out}/{name}_CPL_JLC.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for p in prow:
            if p["Ref"] in assembled:
                rot = float(p["Rot"]) % 360
                w.writerow([p["Ref"], f'{float(p["PosX"]):.4f}mm', f'{float(p["PosY"]):.4f}mm',
                            "Top" if p["Side"] == "top" else "Bottom", f"{rot:g}"])
    unplaced = sorted(assembled - {p["Ref"] for p in prow})

    print("JLC_Order ->", out)
    print("  gerbers/drills:", sorted(os.listdir(gdir)))
    print("  zip:", os.path.basename(zpath), os.path.getsize(zpath), "bytes")
    print("  BOM rows:", [(r["Designator"], r["LCSC Part #"]) for r in bom])
    print("  not in BOM (no LCSC #, hand-placed):", [r["Designator"] for r in skipped])
    if unplaced:
        print("  WARNING: in BOM but missing from CPL:", unplaced)
    board = open(pcb).read()
    if "(segment" not in board and "(arc" not in board:
        print("  WARNING: the board has no tracks - these gerbers are a dry run, not fab-ready")


if __name__ == "__main__":
    main()
