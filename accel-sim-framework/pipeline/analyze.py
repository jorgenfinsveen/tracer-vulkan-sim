#!/usr/bin/env python3

# Todo: Her kan vi lage kode for å lese csv- og visualizer-fil for å generere plots 
# Todo: Det er mulig vi er interessert i andre plots enn det som allerede finnes av plottescripts
# Todo: Det kan også være en idé å lage noe som trekker ut et gitt sett med verdier fra de forskjellige resultat-filene 
# Todo: ... og sammenligner hvilket som oppnådde best IPC, og deretter lagrer disse tallene + konfigurasjonen som ble brukt
# Todo: ... Det ville være gull verdt når vi gjør design-sweepinga!

from pathlib import Path
import sys

#Impoter funksjoner for ploting
from utility.plots.bar_chart import bar_chart

PIPELINE_ROOT = Path(__file__).resolve().parent

def find_file(root: Path, filename: str) -> Path | None:
    for p in root.rglob(filename):
        if p.is_file():
            return p
    return None

def main():
    plots = {
        1: ("Bar chart", bar_chart),
    }

    print("Available plot types:")
    for k, (name, _) in plots.items():
        print(f"{k}: {name}")

    choice = input("Choose a plot type: ").strip()

    if not choice.isdigit() or int(choice) not in plots:
        print("Invalid choice")
        sys.exit(1)

    csv_file = input("CSV file to use: ").strip()
    if not csv_file:
        print("No filename was provided.")
        sys.exit(1)
    if "/" in csv_file or "\\" in csv_file:
        print("Pleas provide only the filname")
        sys.exit(1)

    csv_path = find_file(PIPELINE_ROOT, csv_file)
    if csv_path is None:
        print(f"Didn't find a file with the name of {csv_file}")
        sys.exit(1)

    plot_name, plot_func = plots[int(choice)]

    plot_func(str(csv_path))

if __name__ == "__main__":
    main()