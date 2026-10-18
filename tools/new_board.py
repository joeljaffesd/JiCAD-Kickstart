"""Create an empty JiCAD board: NAME.kicad_pro / .kicad_sch / .kicad_pcb, and retitle README.md. Called by `make board`;
refuses if the repo already has a board (any *.kicad_pro)."""
import glob, json, os, sys, uuid
name = sys.argv[1]
tpl = os.path.join(os.environ.get("JICAD_APP", "/Users/joeljaffesd/Desktop/SKNKWRKS/JiCAD/build/install/KiCad.app"),
                   "Contents/SharedSupport/template/kicad.kicad_pro")
existing = glob.glob("*.kicad_pro")
if existing:
    sys.exit("make board: this repo already has a board (%s); nothing created" % ", ".join(existing))
try:
    pro = json.load(open(tpl))
except OSError:
    pro = {"meta": {"version": 3}}
pro.setdefault("meta", {})["filename"] = name + ".kicad_pro"
pro["sheets"] = []
json.dump(pro, open(name + ".kicad_pro", "w"), indent=2)
open(name + ".kicad_sch", "w").write(
    '(kicad_sch\n\t(version 20250114)\n\t(generator "eeschema")\n\t(generator_version "9.0")\n'
    f'\t(uuid "{uuid.uuid4()}")\n\t(paper "A4")\n\t(lib_symbols)\n'
    '\t(sheet_instances\n\t\t(path "/"\n\t\t\t(page "1")\n\t\t)\n\t)\n\t(embedded_fonts no)\n)\n')
open(name + ".kicad_pcb", "w").write(
    '(kicad_pcb\n\t(version 20241229)\n\t(generator "pcbnew")\n\t(generator_version "9.0")\n'
    '\t(general\n\t\t(thickness 1.6)\n\t\t(legacy_teardrops no)\n\t)\n\t(paper "A4")\n\t(embedded_fonts no)\n)\n')
# Stamp the files with the running JiCAD build's own format versions (no "created by an older version" warning).
import subprocess
cli = os.environ.get("KICAD_CLI", "/Users/joeljaffesd/Desktop/SKNKWRKS/JiCAD/build/install/KiCad.app/Contents/MacOS/kicad-cli")
for kind, ext in (("sch", ".kicad_sch"), ("pcb", ".kicad_pcb")):
    r = subprocess.run([cli, kind, "upgrade", "--force", name + ext], capture_output=True, text=True)
    if r.returncode:
        print(f"warning: kicad-cli {kind} upgrade failed ({r.stderr.strip() or r.stdout.strip()}); JiCAD will offer to convert on first save")
print("created", name + ".kicad_pro/.kicad_sch/.kicad_pcb")

# The template README's intro and quick start are for setting up the repo; once the board exists, replace
# everything above "## Make targets" with the board's own title.
try:
    readme = open("README.md").read()
    cut = readme.find("## Make targets")
    if cut < 0:
        print("README.md: no '## Make targets' heading found, left unchanged")
    else:
        open("README.md", "w").write(f"# {name}\n\n" + readme[cut:])
        print(f"README.md: title set to '# {name}'")
except OSError:
    pass
