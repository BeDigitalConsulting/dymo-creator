
# DYMO: Generare file `.dymo` da un template e da Excel/CSV (locale, Python)

Questo documento spiega **come creare automaticamente molti file `.dymo`** partendo da:
- un **template `.dymo`** progettato in **DYMO Connect** (con *placeholder* tipo `{{Code}}`, `{{Desc}}`, …);
- un file **Excel/CSV** con le colonne corrispondenti ai placeholder.

> **Scopo (dal meeting):** non stampare direttamente, ma **produrre i file `.dymo`** finali da consegnare/usare con il software DYMO.  
> Vogliamo un processo **locale**, semplice da mantenere e ripetibile in azienda.

---

## Cosa costruiremo

- Una **cartella di lavoro** con:
  - `template.dymo` → il layout creato in DYMO Connect, con testi/Barcode che contengono **placeholder** (es. `{{Code}}`).
  - `data.xlsx` (o `data.csv`) → i dati riga-per-riga; **le intestazioni devono coincidere** con i placeholder.
  - `generate_dymo_files.py` → lo script che legge dati, sostituisce i placeholder nell’XML e **scrive 1 file `.dymo` per riga**.
  - `out/` → cartella di output con i `.dymo` generati.

```
dymo-gen/
├─ generate_dymo_files.py
├─ template.dymo
├─ data.xlsx            # oppure data.csv
└─ out/                 # verrà creata se non esiste
```

---

## Requisiti

- **DYMO Connect** installato (serve solo per **creare** il template e verificare l’anteprima).  
- **Python 3.10+** con `pandas` (per leggere Excel/CSV).  
  - Se usi **Excel**, installa anche `openpyxl` (`pip install openpyxl`).  
  - Per **CSV** non servono extra.

Installazione rapida ambiente:

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1

pip install pandas openpyxl
```

> Se useremo **solo CSV**, `openpyxl` è opzionale.

---

## Preparare il template `.dymo`

1. Apri **DYMO Connect** e crea il layout dell’etichetta (testo, codici a barre, ecc.).  
2. Nei campi che cambiano, inserisci **letteralmente** il testo del placeholder, ad es. `{{Code}}`, `{{Desc}}`, `{{Barcode}}`.  
   - Per i Barcode: imposta il loro contenuto al testo `{{Barcode}}`.  
3. **Salva** come `template.dymo` nella cartella di lavoro.

> I **nomi dei placeholder** sono *case-sensitive*. Evita spazi: preferisci `Code`, `ItemCode`, `Color`, `Size`.

---

## Preparare i dati (Excel/CSV)

- Ogni **colonna** deve corrispondere a un **placeholder** del template. Esempio intestazioni:
  - `Code, Desc, Color, Size, Barcode, Copies`
- Ogni **riga** produce **un file `.dymo`**.
- Puoi aggiungere una colonna opzionale **`Copies`** (intero) se vuoi già decidere le copie *per eventuale stampa futura* (qui la includiamo solo come dato).

### Esempio `data.csv`

```csv
Code,Desc,Color,Size,Barcode
A123,Guanto nitrile,Blue,M,8051234567890
A124,Guanto nitrile,Blue,L,8051234567891
```

> Se usi **Excel**, stesso schema di intestazioni nel foglio principale.

---

## Script: `generate_dymo_files.py`

Lo script:
- legge `template.dymo`;
- estrae i placeholder `{{...}}` presenti;
- carica dati da `data.xlsx` **o** `data.csv` (rileva dal suffisso del file);
- per ogni riga **sostituisce** i placeholder con valori *XML-escaped*;
- genera un nome file con un **pattern** (di default `{Code}_{Color}_{Size}.dymo`), sanificando i caratteri non validi;
- salva in `out/`.

### Uso

```bash
# Esempio con Excel
python generate_dymo_files.py \\
  --template template.dymo \\
  --data data.xlsx \\
  --out out \\
  --name "{Code}_{Color}_{Size}.dymo"

# Esempio con CSV (con separatore ';')
python generate_dymo_files.py \\
  --template template.dymo \\
  --data data.csv \\
  --sep ";" \\
  --out out \\
  --name "{Code}_{i}.dymo"
```

**Opzioni principali**
- `--template` : percorso del template `.dymo`.
- `--data` : `data.xlsx` / `data.csv`.
- `--sheet` : nome foglio Excel (opzionale).
- `--sep` : separatore CSV (default `,`).
- `--out` : cartella di output (default `out`).
- `--name` : pattern nome file, usa **intestazioni colonna** (es. `{Code}_{i}.dymo`). `{i}` è l’indice 1-based.
- `--limit` : processa solo le prime N righe (debug).
- `--dry-run` : non scrive file, mostra anteprime/sintesi (validazione).
- `--encoding` : encoding CSV (default `utf-8`).

---

## Codice completo

> Il file è incluso anche come download in questa chat: `generate_dymo_files.py`.

```python

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
        df = pd.read_excel(data_path, sheet_name=sheet, dtype=str).fillna("")
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

```

---

## Validazioni & logiche utili

- **Placeholder mancanti:** lo script avvisa se il template contiene placeholder senza colonna corrispondente nell’input.  
- **Colonne inutilizzate:** lo script segnala se l’input ha colonne non mappate da nessun placeholder (non è errore).  
- **Escape XML:** i valori vengono *XML-escaped* per sicurezza (`&`, `<`, `>`, `"` e `'`).  
- **Sanitizzazione nomi file:** rimuove caratteri non validi e limita la lunghezza.

---

## Troubleshooting

- **Caratteri speciali non renderizzati:** assicurati che i valori nell’input non contengano markup XML; lo script già fa l’escape.  
- **Zeri iniziali (es. Barcode):** leggiamo come `str` per preservare gli zeri; evita formati numerici in Excel.  
- **Template senza placeholder:** verifica in DYMO Connect che nei campi variabili sia scritto `{{NomeCampo}}`.  
- **Estensione differente (es. `.demo`):** tecnicamente è sempre XML DYMO; puoi cambiare il pattern `--name` di conseguenza.

---

## Estensioni future (facoltative)

- **Stampa automatica via DYMO Connect Web Service:** 
  - Invece di generare file, si può inviare `labelXml` all’endpoint locale (`PrintLabel`).  
  - Utile quando vuoi un **batch print** direttamente da Python.  
- **Generatori di Barcode** nella pipeline dei dati (es. costruire EAN/Code128 da parti).  
- **Regole di naming** file più complesse (slug, date, progressivi, PID lotto, ecc.).

Se vuoi, posso aggiungere una **variante** dello script che prende i `.dymo` generati e li invia *subito* in stampa, quando decideremo di farlo.

---

## FAQ

**D: Possiamo usare solo CSV?**  
R: Sì. Lo script auto-rileva in base all’estensione; per CSV non serve `openpyxl`.

**D: Serve DYMO installato per generare file?**  
R: No. Serve DYMO Connect solo per progettare/verificare il template. La generazione è puro XML.

**D: I placeholder devono coincidere con le intestazioni Excel?**  
R: Sì, altrimenti lo script segnala i mismatch.

**D: Come valido il risultato?**  
R: Apri a campione alcuni `.dymo` in DYMO Connect. In alternativa usa `--dry-run` per controllare mappature e nomi file prima di generare.

---

**Pronto per l’uso.** Se mi invii `template.dymo` + un estratto reale di `data.xlsx`, aggiungo una **config di naming** su misura e, se serve, una **whitelist di campi obbligatori** con errori dettagliati.
