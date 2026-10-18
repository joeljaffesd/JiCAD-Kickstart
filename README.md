# JiCAD-Kickstart

A starting point for a git-tracked JiCAD (KiCad) hardware project. 

Create your repo from this template, then run
`make board` to generate your board files.

## Quick start

New project, from a fresh clone of a repo made from this template:

```sh
git clone <your-repo-url> MyBoard && cd MyBoard
make board # MyBoard.kicad_pro / .kicad_sch / .kicad_pcb (named after the folder; NAME=… to override)
```

`make board` runs once per repo: it refuses if the repo already has a board.

Fresh clone of a project that already has a board: open it in JiCAD, which restores any missing JLC 3D models.

## What's tracked and what isn't

| Tracked (source of truth) | Ignored (per-machine or rebuildable) |
|---|---|
| `*.kicad_pro`, `*.kicad_sch`, `*.kicad_pcb`, `*.kicad_dru`, `*.kicad_jobset` | `.history/` (JiCAD's local autosave repo) |
| `sym-lib-table`, `fp-lib-table` | `*.kicad_prl`, `*.lck`, `fp-info-cache`, `*-backups/` |
| `JLC-PARTS/JLC.kicad_sym`, `JLC-PARTS/JLC.pretty/` | `JLC-PARTS/JLC.3dshapes/`: restored by JiCAD |
| project libraries (`*.pretty/`, `*.kicad_sym`) | `JLC_Order/`, `compat/`, `*.step`, renders, ERC/DRC reports |
| `tools/`, `Makefile` | |
| `vendor-3d/` (non-JLC models, via Git LFS) | |

**Why the 3D models can be ignored.** Every footprint imported from JLC records its EasyEDA model id in a
`JLC_3DModel` property. JiCAD reads those ids and restores the exact same STEP, byte for byte, instead of
re-importing by C-number (which could bring back a newer or different model). Footprints and symbols
stay tracked: they hold your edits (variants, pad swaps, model offsets) and are tiny. Fab outputs (gerbers,
drills, BOM, CPL) don't use 3D models at all, so a fresh clone can build a complete order before fetching any.

**Models that can't be re-fetched:** put them in `vendor-3d/`. It's
tracked through Git LFS (`git lfs install` once), as set up in `.gitattributes`.

## Make targets

| | |
|---|---|
| `make board` | create the board files and retitle this README (once per repo; refuses if a board exists) |
| `make erc`, `make drc` | ERC / DRC (with schematic parity) |
| `make order` | `JLC_Order/`: gerbers + drills (JLC's KiCad settings), zip, JLC BOM and CPL |
| `make step` | 3D export with silkscreen |
| `make compatible` | `compat/<Name>-kicad10/` + zip: a copy release KiCad 10.0 can open (needs only Python; refuses if the board uses JiCAD-only features) |

`KICAD_CLI` and `BOARD` can be overridden, e.g. `make drc BOARD=Other KICAD_CLI=/path/to/kicad-cli`.

## Working rules

- **Releases:** tag the commit you order from, and attach `JLC_Order/*.zip`, the BOM and the CPL to the release
  instead of committing them.
- **Merges:** KiCad files are text but merge badly. One person per board file at a time.
- **Unsaved state:** run `make order` from a saved board. JiCAD's local history (`.history/`) is your undo safety
  net, not git.
