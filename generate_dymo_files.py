
import argparse
import re
import sys
from pathlib import Path
from typing import List, Dict, Set
import pandas as pd
from xml.sax.saxutils import escape as xml_escape

PLACEHOLDER_RX = re.compile(r"\{\{(\w+)\}\}")

def read_text(path: Path) -> str:
    if not path.exists():
        sys.exit(f"Template non trovato: {path}")
    return path.read_text(encoding="utf-8")

def extract_placeholders(xml: str) -> Set[str]:
    return set(PLACEHOLDER_RX.findall(xml))

def xml_fill(template_xml: str, mapping: Dict[str, str]) -> str:
    out = template_xml
    for k, v in mapping.items():
        out = out.replace(f"{{{{{k}}}}}", xml_escape("" if v is None else str(v)))
    return out

def sanitize_filename(s: str) -> str:
    s = s.strip().replace("/", "-").replace("\\", "-").replace(":", "-")
    s = re.sub(r"[^\w\-. ]+", "-", s)
    s = re.sub(r"\s+", "_", s)
    return s[:180] or "label"

def build_filename(pattern: str, row: Dict[str, str], idx: int) -> str:
    safe = {k: "" if v is None else str(v) for k, v in row.items()}
    safe.setdefault("i", idx)  # indice riga disponibile come {i}
    try:
        name = pattern.format(**safe)
    except KeyError:
        name = f"label_{idx}.dymo"
    return sanitize_filename(name)

def read_rows(data_path: Path, sheet: str | None, sep: str, encoding: str) -> List[Dict[str, str]]:
    if not data_path.exists():
        sys.exit(f"File dati non trovato: {data_path}")

    suffix = data_path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        # If sheet is None, read the first sheet (sheet_name=0)
        sheet_to_read = sheet if sheet is not None else 0
        df = pd.read_excel(data_path, sheet_name=sheet_to_read, dtype=str).fillna("")
    elif suffix == ".csv":
        df = pd.read_csv(data_path, sep=sep, dtype=str, encoding=encoding).fillna("")
    else:
        sys.exit("Formato dati non supportato. Usa .xlsx/.xls o .csv")
    return df.to_dict(orient="records")

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

    template_xml = read_text(args.template)
    needed = extract_placeholders(template_xml)

    rows = read_rows(args.data, args.sheet, args.sep, args.encoding)
    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        print("Dati vuoti: nessuna riga da processare.", file=sys.stderr)
        sys.exit(0)

    cols = set(rows[0].keys())
    missing = sorted([p for p in needed if p not in cols])
    unused = sorted([c for c in cols if c not in needed])

    print(f"Placeholder nel template: {sorted(needed)}")
    print(f"Colonne nei dati:        {sorted(cols)}")
    if missing:
        print(f"ATTENZIONE: placeholder senza colonna dati: {missing}", file=sys.stderr)
    if unused:
        print(f"Nota: colonne non usate dal template: {unused}")

    if args.dry_run:
        # Mostra un esempio di riempimento e nome file
        ex_row = rows[0]
        ex_filled = xml_fill(template_xml, ex_row)
        ex_name = build_filename(args.name, ex_row, 1)
        print("\n--- DRY RUN ---")
        print("Esempio nome file:", ex_name)
        # Mostra solo un estratto per non inondare il terminale
        snippet = ex_filled[:400].replace("\n", " ")
        print("Estratto label XML:", snippet + ("..." if len(ex_filled) > 400 else ""))
        sys.exit(0)

    args.out.mkdir(parents=True, exist_ok=True)

    count = 0
    for i, row in enumerate(rows, 1):
        filled_xml = xml_fill(template_xml, row)
        fname = build_filename(args.name, row, i)
        (args.out / fname).write_text(filled_xml, encoding="utf-8")
        count += 1

    print(f"Creati {count} file in: {args.out.resolve()}")

if __name__ == "__main__":
    main()
