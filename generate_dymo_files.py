"""
CLI tool for generating DYMO labels from Excel/CSV data.
"""

import argparse
import sys
from pathlib import Path

from utils import (
    read_template,
    extract_placeholders,
    read_excel_data,
    validate_data,
    generate_labels
)


def main():
    ap = argparse.ArgumentParser(description="Genera file .dymo da template e Excel/CSV")
    ap.add_argument("--template", default="template.dymo", type=Path, help="Percorso del template .dymo")
    ap.add_argument("--data", default="data.xlsx", type=Path, help="Percorso dati (.xlsx/.xls/.csv)")
    ap.add_argument("--sheet", default=None, help="Nome foglio Excel (opzionale)")
    ap.add_argument("--sep", default=",", help="Separatore CSV (default ,)")
    ap.add_argument("--encoding", default="utf-8", help="Encoding CSV (default utf-8)")
    ap.add_argument("--out", default="out", type=Path, help="Cartella output")
    ap.add_argument("--name", default="{Code}_{Color}_{Size}.dymo",
                    help="Pattern nome file; usa intestazioni colonna. {i} è indice 1-based")
    ap.add_argument("--limit", type=int, default=None, help="Processa solo le prime N righe")
    ap.add_argument("--dry-run", action="store_true", help="Non scrive file; mostra anteprima e validazione")
    args = ap.parse_args()

    # Leggi template
    try:
        template_xml = read_template(args.template)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    # Leggi dati
    try:
        df, rows = read_excel_data(args.data, args.sheet, args.sep, args.encoding)
    except (FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    # Applica limite
    if args.limit:
        rows = rows[:args.limit]

    if not rows:
        print("Dati vuoti: nessuna riga da processare.", file=sys.stderr)
        sys.exit(0)

    # Valida dati
    validation = validate_data(template_xml, rows)

    print(f"Placeholder nel template: {sorted(validation['placeholders'])}")
    print(f"Colonne nei dati:        {sorted(validation['columns'])}")

    if validation['missing']:
        print(f"ATTENZIONE: placeholder senza colonna dati: {validation['missing']}", file=sys.stderr)

    if validation['unused']:
        print(f"Nota: colonne non usate dal template: {validation['unused']}")

    if args.dry_run:
        # Genera solo il primo per mostrare esempio
        labels = generate_labels(template_xml, rows, args.name, limit=1)
        if labels:
            filename, content = labels[0]
            print("\n--- DRY RUN ---")
            print("Esempio nome file:", filename)
            snippet = content[:400].replace("\n", " ")
            print("Estratto label XML:", snippet + ("..." if len(content) > 400 else ""))
        sys.exit(0)

    # Genera tutte le etichette
    labels = generate_labels(template_xml, rows, args.name, args.limit)

    # Crea cartella output
    args.out.mkdir(parents=True, exist_ok=True)

    # Scrivi file
    for filename, content in labels:
        output_path = args.out / filename
        output_path.write_text(content, encoding="utf-8")

    print(f"Creati {len(labels)} file in: {args.out.resolve()}")


if __name__ == "__main__":
    main()
