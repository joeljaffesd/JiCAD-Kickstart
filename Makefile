# JiCAD-Kickstart: common chores. BOARD defaults to the only *.kicad_pro in this folder.
KICAD_CLI ?= /Users/joeljaffesd/Desktop/SKNKWRKS/JiCAD/build/install/KiCad.app/Contents/MacOS/kicad-cli
BOARD ?= $(basename $(firstword $(wildcard *.kicad_pro)))
NAME ?= $(notdir $(CURDIR))
export KICAD_CLI

.PHONY: help board order step drc erc

help:
	@echo "make board         create NAME.kicad_pro/.kicad_sch/.kicad_pcb (NAME defaults to the folder: $(NAME)); fails if a board exists"
	@echo "make erc / drc      run ERC / DRC ($(BOARD))"
	@echo "make order          build JLC_Order/ (gerbers, zip, BOM, CPL)"
	@echo "make step           export $(BOARD).step"

board:
	@python3 tools/new_board.py $(NAME)
erc:
	@$(KICAD_CLI) sch erc $(BOARD).kicad_sch -o $(BOARD)-erc.rpt && tail -3 $(BOARD)-erc.rpt
drc:
	@$(KICAD_CLI) pcb drc $(BOARD).kicad_pcb --schematic-parity -o $(BOARD)-drc.rpt && grep Found $(BOARD)-drc.rpt
order:
	@python3 tools/jlc_order.py .
step:
	@$(KICAD_CLI) pcb export step $(BOARD).kicad_pcb --grid-origin --subst-models --include-silkscreen -f -o $(BOARD).step
