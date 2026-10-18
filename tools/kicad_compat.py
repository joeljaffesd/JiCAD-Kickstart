"""Write a KiCad 10.0 (release) copy of this JiCAD project to compat/<NAME>-kicad10/ (+ .zip).

JiCAD saves newer file formats than release KiCad can read. Converting down is a plain text rewrite:
  - schematic / footprint libraries: only the format version changes
  - board: also each footprint's (transform (translate x y) (rotate r) (scale 1 1)) becomes (at x y r)
Anything JiCAD-only (a token release KiCad's parser doesn't know) makes the tool refuse, naming the feature,
rather than silently dropping it.

Needs only Python 3: no KiCad or JiCAD install.

usage: python3 tools/kicad_compat.py [NAME]        (make compatible)
The output is a hand-off copy, never the source: edits made in KiCad 10 come back by opening that copy in JiCAD.
"""
import re, shutil, sys
from pathlib import Path

# file format versions: what this converter understands (JiCAD) -> what KiCad 10.0.x reads
SRC = {"pcb": 20260901, "sch": 20260830}
DST = {"pcb": 20260206, "sch": 20260306}

# list heads added to the parsers after KiCad 10.0.6 (keyword-file diff, JiCAD vs the 10.0.6 tag).
# transform/translate are converted below; everything else is a JiCAD-only feature.
NEW_PCB = set("""affects all arrow arrow_open assignment background body_pcb_gap castellated column constant constraint
cursor custom_property default_marks dielectric_model djordjevic_sarkar dots drill_chart drill_map drill_symbol_profile
driving end_angle end_shape exclude_from_sim extent extruded filter fp_ellipse fp_ellipse_arc freeze_assignments gap
gr_ellipse gr_ellipse_arc grid_item group_by guide_cross ij key length major_radius mark member minor_radius net_chain
net_chains npth outline_slots overall_height plated polar rotation_angle routing row_keys row_shapes
sim_electrical_type sink slots source spacing spec_frequency square squares stagger start_angle start_shape template
templates terminal_pad thieving tick_interval totals""".split())
NEW_SCH = set("""arrow arrow_open associated_footprints custom_property delegate edit ellipse ellipse_arc end_angle
end_shape entry from identity library_default locked major_radius map minor_radius mode named_map net_chain net_class
nets passthrough pin_map pin_map_override pin_maps rotation_angle square start_angle start_shape symbol_override
to""".split())


def die(msg):
    sys.exit(f"make compatible: {msg}")


def version(text, kind):
    m = re.match(r"\((?:kicad_pcb|kicad_sch|footprint \"[^\"]*\")\s*\(version (\d+)\)", text)
    if not m: die(f"can't read the format version ({kind})")
    return int(m.group(1))


def check_tokens(text, new, where):
    heads = set(re.findall(r"\(([a-z_]+)[\s)]", text)) & new
    if heads: die(f"{where} uses JiCAD-only features KiCad 10.0 can't store: {', '.join(sorted(heads))}")


def down_pcb(text, where, kind="pcb"):
    v = version(text, where)
    if v <= DST["pcb"]: return text
    if v != SRC["pcb"]: die(f"{where} is format {v}; this tool knows {SRC['pcb']} (update it)")
    check_tokens(text, NEW_PCB, where)
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        if lines[i] == "\t\t(transform":
            blk = lines[i:i + 5]
            t = re.fullmatch(r"\t\t\t\(translate (\S+) (\S+)\)", blk[1])
            r = re.fullmatch(r"\t\t\t\(rotate (\S+)\)", blk[2])
            if not (t and r and blk[3] == "\t\t\t(scale 1 1)" and blk[4] == "\t\t)"):
                die(f"{where}: footprint transform near line {i + 1} isn't a plain move/rotate "
                    "(scaled or mirrored footprints can't be stored in KiCad 10.0)")
            a = float(r.group(1))
            out.append(f"\t\t(at {t.group(1)} {t.group(2)}" + (f" {a:g})" if a else ")"))
            i += 5
            continue
        out.append(lines[i]); i += 1
    text = "\n".join(out)
    if "(transform" in text or "(translate" in text: die(f"{where}: transform in an unexpected place")
    return text.replace(f"(version {SRC['pcb']})", f"(version {DST['pcb']})", 1)


def down_sch(text, where):
    v = version(text, where)
    if v <= DST["sch"]: return text
    if v != SRC["sch"]: die(f"{where} is format {v}; this tool knows {SRC['sch']} (update it)")
    check_tokens(text, NEW_SCH, where)
    return text.replace(f"(version {SRC['sch']})", f"(version {DST['sch']})", 1)


def main():
    root = Path.cwd()
    pros = sorted(root.glob("*.kicad_pro"))
    name = sys.argv[1] if len(sys.argv) > 1 else (pros[0].stem if pros else die("no .kicad_pro here"))
    dst = root / "compat" / f"{name}-kicad10"
    if dst.exists(): shutil.rmtree(dst)
    dst.mkdir(parents=True)

    # project files
    for p in [root / f"{name}.kicad_pro", root / f"{name}.kicad_dru", root / "sym-lib-table", root / "fp-lib-table"]:
        if p.exists(): shutil.copy2(p, dst / p.name)
    (dst / f"{name}.kicad_pcb").write_text(down_pcb((root / f"{name}.kicad_pcb").read_text(), f"{name}.kicad_pcb"))
    for s in sorted(root.glob("*.kicad_sch")):
        (dst / s.name).write_text(down_sch(s.read_text(), s.name))
    # project libraries: footprints restamped, symbol libs and 3D models copied
    nfp = 0
    for lib in [*root.glob("*.pretty"), *root.glob("JLC-PARTS/*.pretty")]:
        o = dst / lib.relative_to(root); o.mkdir(parents=True, exist_ok=True)
        for m in lib.glob("*.kicad_mod"):
            (o / m.name).write_text(down_pcb(m.read_text(), m.name)); nfp += 1
    for f in [*root.glob("*.kicad_sym"), *root.glob("JLC-PARTS/*.kicad_sym")]:
        (dst / f.relative_to(root)).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst / f.relative_to(root))
    for d in [*root.glob("*.3dshapes"), *root.glob("JLC-PARTS/*.3dshapes"), root / "vendor-3d"]:
        if d.is_dir(): shutil.copytree(d, dst / d.relative_to(root), dirs_exist_ok=True)
    print(f"wrote {dst.relative_to(root)}/ (board, {len(list(root.glob('*.kicad_sch')))} schematic(s), {nfp} library footprints)")

    z = shutil.make_archive(str(dst), "zip", dst.parent, dst.name)
    print(f"zip: {Path(z).relative_to(root)}")


if __name__ == "__main__":
    main()
