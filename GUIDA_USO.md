# Guida all'uso - Generatore di Etichette DYMO

Questa guida spiega come utilizzare il sistema per generare automaticamente file `.dymo` da dati Excel o CSV.

## Requisiti

### Software Necessario

1. **Python 3.10 o superiore**
   - Verifica la versione installata: `python3 --version`
   - Se hai Python 3.10+, puoi usare: `python3`
   - Se hai Python 3.11, puoi usare: `python3.11`

2. **DYMO Connect** (solo per creare/verificare template)
   - Necessario per progettare il template iniziale
   - Necessario per aprire e stampare i file `.dymo` generati
   - Non serve per la generazione automatica dei file

3. **Librerie Python**
   - `pandas` - per leggere file Excel/CSV
   - `openpyxl` - per supporto file Excel

## Installazione

### 1. Creare l'ambiente virtuale

```bash
# Naviga nella cartella del progetto
cd /percorso/della/cartella/DymoProject

# Crea ambiente virtuale con Python 3.11 (o 3.10+)
python3.11 -m venv .venv

# Attiva l'ambiente virtuale
source .venv/bin/activate
```

### 2. Installare le dipendenze

```bash
# Aggiorna pip
pip install --upgrade pip

# Installa pandas e openpyxl
pip install pandas openpyxl
```

## Preparazione dei File

### Template DYMO (`template.dymo`)

1. Apri **DYMO Connect**
2. Crea il layout dell'etichetta (testi, codici a barre, ecc.)
3. Nei campi variabili, inserisci i **placeholder** tra doppie parentesi graffe:
   - Esempio: `{{Code}}`, `{{Desc}}`, `{{Color}}`, `{{Size}}`, `{{Barcode}}`
4. Per i codici a barre: imposta il contenuto come `{{Barcode}}`
5. Salva il file come `template.dymo`

**Importante:** I nomi dei placeholder sono case-sensitive (maiuscole/minuscole contano).

### File Dati Excel (`data.xlsx`)

Crea un file Excel con:
- **Prima riga:** intestazioni che corrispondono ai placeholder del template
- **Righe successive:** i dati per ogni etichetta

**Esempio:**

| Code | Desc              | Color | Size | Barcode       |
|------|-------------------|-------|------|---------------|
| A123 | Guanto nitrile    | Blue  | M    | 8051234567890 |
| A124 | Guanto nitrile    | Blue  | L    | 8051234567891 |
| B210 | Mascherina FFP2   | White | UNI  | 8059876543210 |

**Note:**
- Le intestazioni devono corrispondere esattamente ai placeholder nel template
- Ogni riga genera un file `.dymo` separato
- Usa il formato testo per codici a barre con zeri iniziali

### File Dati CSV (alternativa)

Se preferisci CSV, crea un file `data.csv`:

```csv
Code,Desc,Color,Size,Barcode
A123,Guanto nitrile,Blue,M,8051234567890
A124,Guanto nitrile,Blue,L,8051234567891
B210,Mascherina FFP2,White,UNI,8059876543210
```

## Utilizzo

### 1. Attivare l'ambiente virtuale

```bash
source .venv/bin/activate
```

### 2. Validare i dati (dry-run)

Prima di generare i file, verifica che tutto sia configurato correttamente:

```bash
python generate_dymo_files.py --template template.dymo --data data.xlsx --dry-run
```

Questo comando:
- Verifica che i placeholder corrispondano alle colonne
- Mostra un esempio di nome file
- Non crea nessun file

### 3. Generare i file .dymo

```bash
python generate_dymo_files.py --template template.dymo --data data.xlsx --out out
```

I file verranno creati nella cartella `out/` con nomi come:
- `A123_Blue_M.dymo`
- `A124_Blue_L.dymo`
- `B210_White_UNI.dymo`

### 4. Verificare e stampare

1. Apri uno dei file generati in **DYMO Connect**
2. Verifica che i dati siano corretti
3. Stampa le etichette necessarie

## Opzioni Avanzate

### Personalizzare il nome dei file

```bash
# Usa solo il codice e un indice progressivo
python generate_dymo_files.py --template template.dymo --data data.xlsx --name "{Code}_{i}.dymo"

# Usa codice e descrizione
python generate_dymo_files.py --template template.dymo --data data.xlsx --name "{Code}_{Desc}.dymo"
```

**Variabili disponibili:**
- Qualsiasi nome di colonna dal file dati (es. `{Code}`, `{Color}`)
- `{i}` - numero progressivo (1, 2, 3, ...)

### Processare solo alcune righe

```bash
# Genera solo le prime 5 etichette (per test)
python generate_dymo_files.py --template template.dymo --data data.xlsx --limit 5
```

### Usare un file CSV con separatore diverso

```bash
# CSV con punto e virgola come separatore
python generate_dymo_files.py --template template.dymo --data data.csv --sep ";" --out out
```

### Specificare un foglio Excel diverso

```bash
# Se hai più fogli nel file Excel
python generate_dymo_files.py --template template.dymo --data data.xlsx --sheet "Foglio2"
```

## Risoluzione Problemi

### Errore: "placeholder senza colonna dati"

**Causa:** Il template contiene un placeholder che non esiste nel file Excel.

**Soluzione:**
- Verifica che le intestazioni Excel corrispondano esattamente ai placeholder
- Controlla maiuscole/minuscole

### Errore: "File dati non trovato"

**Causa:** Il percorso del file dati non è corretto.

**Soluzione:**
- Verifica che il file `data.xlsx` sia nella stessa cartella dello script
- Usa il percorso completo: `--data /percorso/completo/data.xlsx`

### Errore: "ModuleNotFoundError: No module named 'pandas'"

**Causa:** Le librerie non sono installate o l'ambiente virtuale non è attivo.

**Soluzione:**
```bash
source .venv/bin/activate
pip install pandas openpyxl
```

### I codici a barre perdono gli zeri iniziali

**Causa:** Excel interpreta i numeri e rimuove gli zeri iniziali.

**Soluzione:**
- Formatta la colonna Barcode come "Testo" in Excel
- Oppure aggiungi un apostrofo all'inizio: `'8051234567890`

### I caratteri speciali non vengono visualizzati correttamente

**Causa:** Problema di codifica del file CSV.

**Soluzione:**
- Salva il CSV con codifica UTF-8
- Oppure specifica la codifica: `--encoding iso-8859-1`

## Workflow Consigliato

1. **Crea il template** in DYMO Connect con i placeholder
2. **Prepara i dati** in Excel con le intestazioni corrette
3. **Esegui dry-run** per verificare la configurazione
4. **Genera i file** nella cartella `out/`
5. **Verifica** aprendo 1-2 file in DYMO Connect
6. **Stampa** le etichette necessarie

## Esempio Completo

```bash
# 1. Attiva ambiente
source .venv/bin/activate

# 2. Valida (dry-run)
python generate_dymo_files.py --template template.dymo --data data.xlsx --dry-run

# 3. Genera file
python generate_dymo_files.py --template template.dymo --data data.xlsx --out out

# 4. Controlla output
ls -lh out/

# 5. Apri un file in DYMO Connect per verificare
open out/A123_Blue_M.dymo
```

## Supporto

Per problemi o domande, verifica:
1. Versione Python: `python3 --version` (deve essere 3.10+)
2. Ambiente virtuale attivo (dovresti vedere `(.venv)` nel prompt)
3. Librerie installate: `pip list | grep pandas`

---

**Ultimo aggiornamento:** Ottobre 2025
