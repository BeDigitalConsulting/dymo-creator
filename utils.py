"""
Utility functions for DYMO label generation.
Shared between CLI tool and Streamlit web app.
"""

import io
import re
import zipfile
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Union
import pandas as pd
from xml.sax.saxutils import escape as xml_escape


PLACEHOLDER_RX = re.compile(r"\{\{(\w+)\}\}")


def read_template(template_path: Union[str, Path]) -> str:
    """
    Legge il file template DYMO.

    Args:
        template_path: Percorso del file template .dymo

    Returns:
        Contenuto XML del template

    Raises:
        FileNotFoundError: Se il template non esiste
    """
    path = Path(template_path)
    if not path.exists():
        raise FileNotFoundError(f"Template non trovato: {path}")
    return path.read_text(encoding="utf-8")


def extract_placeholders(xml_content: str) -> Set[str]:
    """
    Estrae i placeholder dal template XML.

    Args:
        xml_content: Contenuto XML del template

    Returns:
        Set di nomi placeholder (es: {'Code', 'Desc', 'Color'})
    """
    return set(PLACEHOLDER_RX.findall(xml_content))


def read_excel_data(
    file_path: Union[str, Path, io.BytesIO],
    sheet: Optional[str] = None,
    sep: str = ",",
    encoding: str = "utf-8"
) -> Tuple[pd.DataFrame, List[Dict[str, str]]]:
    """
    Legge i dati da file Excel o CSV.

    Args:
        file_path: Percorso del file o BytesIO object
        sheet: Nome foglio Excel (None = primo foglio)
        sep: Separatore CSV
        encoding: Encoding CSV

    Returns:
        Tupla (DataFrame, lista di dizionari con righe)

    Raises:
        ValueError: Se formato file non supportato
        FileNotFoundError: Se file non esiste (solo per Path)
    """
    # Determina il tipo di file
    if isinstance(file_path, (str, Path)):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File dati non trovato: {path}")
        suffix = path.suffix.lower()
        file_obj = path
    elif isinstance(file_path, io.BytesIO):
        # Per Streamlit file upload, determina tipo dal nome o contenuto
        # Assume Excel per BytesIO (Streamlit usa questo per upload)
        suffix = ".xlsx"
        file_obj = file_path
    else:
        raise ValueError("file_path deve essere str, Path o BytesIO")

    # Leggi dati
    if suffix in (".xlsx", ".xls"):
        sheet_to_read = sheet if sheet is not None else 0
        df = pd.read_excel(file_obj, sheet_name=sheet_to_read, dtype=str).fillna("")
    elif suffix == ".csv":
        df = pd.read_csv(file_obj, sep=sep, dtype=str, encoding=encoding).fillna("")
    else:
        raise ValueError("Formato dati non supportato. Usa .xlsx/.xls o .csv")

    rows = df.to_dict(orient="records")
    return df, rows


def merge_product_ean_data(
    product_df: pd.DataFrame,
    ean_df: pd.DataFrame,
    join_key: str = "Code",
    ean_column: str = "Barcode"
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Unisce i dati prodotto con i codici EAN tramite join su colonna chiave.

    Args:
        product_df: DataFrame con informazioni prodotto (deve contenere join_key)
        ean_df: DataFrame con mappatura EAN (deve contenere join_key e ean_column)
        join_key: Nome colonna per il join (default: "Code")
        ean_column: Nome colonna EAN nel file mappatura (default: "Barcode")

    Returns:
        Tupla (merged_df, statistics) dove:
        - merged_df: DataFrame unito con colonna Barcode aggiunta
        - statistics: Dict con conteggi {'total': int, 'matched': int, 'unmatched': int}

    Raises:
        ValueError: Se manca la colonna join_key in uno dei DataFrame
    """
    # Valida che entrambi i DataFrame abbiano la colonna chiave
    if join_key not in product_df.columns:
        raise ValueError(f"Colonna '{join_key}' non trovata nel file prodotti")
    if join_key not in ean_df.columns:
        raise ValueError(f"Colonna '{join_key}' non trovata nel file EAN")
    if ean_column not in ean_df.columns:
        raise ValueError(f"Colonna '{ean_column}' non trovata nel file EAN")

    # Prepara DataFrame EAN: seleziona solo le colonne necessarie
    ean_mapping = ean_df[[join_key, ean_column]].copy()

    # Rimuovi duplicati nel file EAN (prendi il primo se ci sono duplicati)
    ean_mapping = ean_mapping.drop_duplicates(subset=[join_key], keep='first')

    # Left join: mantieni tutti i prodotti, aggiungi EAN dove disponibile
    merged_df = product_df.merge(ean_mapping, on=join_key, how='left')

    # Se Barcode già esisteva in product_df, usa i valori del merge
    # Il suffisso _y viene da pandas quando ci sono colonne duplicate
    if f"{ean_column}_y" in merged_df.columns:
        # Prendi il valore dal file EAN se disponibile, altrimenti quello originale
        merged_df[ean_column] = merged_df[f"{ean_column}_y"].fillna(merged_df[f"{ean_column}_x"])
        merged_df = merged_df.drop(columns=[f"{ean_column}_x", f"{ean_column}_y"])

    # Riempi valori mancanti con stringa vuota
    merged_df[ean_column] = merged_df[ean_column].fillna("")

    # Calcola statistiche
    total_products = len(merged_df)
    matched_products = int((merged_df[ean_column] != "").sum())
    unmatched_products = total_products - matched_products

    statistics = {
        'total': total_products,
        'matched': matched_products,
        'unmatched': unmatched_products
    }

    return merged_df, statistics


def validate_data(template_xml: str, data_rows: List[Dict[str, str]]) -> Dict[str, any]:
    """
    Valida che i dati Excel contengano tutte le colonne richieste dal template.

    Args:
        template_xml: Contenuto XML del template
        data_rows: Lista di righe dati

    Returns:
        Dizionario con:
        - 'placeholders': Set di placeholder nel template
        - 'columns': Set di colonne nei dati
        - 'missing': Lista di placeholder mancanti nei dati
        - 'unused': Lista di colonne non usate dal template
        - 'is_valid': bool, True se tutti i placeholder hanno colonne
    """
    placeholders = extract_placeholders(template_xml)

    if not data_rows:
        return {
            'placeholders': placeholders,
            'columns': set(),
            'missing': sorted(placeholders),
            'unused': [],
            'is_valid': False
        }

    columns = set(data_rows[0].keys())
    missing = sorted([p for p in placeholders if p not in columns])
    unused = sorted([c for c in columns if c not in placeholders])

    return {
        'placeholders': placeholders,
        'columns': columns,
        'missing': missing,
        'unused': unused,
        'is_valid': len(missing) == 0
    }


def fill_template(template_xml: str, data: Dict[str, str]) -> str:
    """
    Riempie il template XML con i dati di una riga.

    Args:
        template_xml: Contenuto XML del template
        data: Dizionario con i dati per questa etichetta

    Returns:
        XML riempito con i dati
    """
    result = template_xml
    for key, value in data.items():
        placeholder = f"{{{{{key}}}}}"
        safe_value = xml_escape("" if value is None else str(value))
        result = result.replace(placeholder, safe_value)
    return result


def sanitize_filename(filename: str) -> str:
    """
    Pulisce un nome file rimuovendo caratteri non validi.

    Args:
        filename: Nome file da pulire

    Returns:
        Nome file pulito e sicuro
    """
    s = filename.strip().replace("/", "-").replace("\\", "-").replace(":", "-")
    s = re.sub(r"[^\w\-. ]+", "-", s)
    s = re.sub(r"\s+", "_", s)
    return s[:180] or "label"


def build_filename(pattern: str, row_data: Dict[str, str], row_index: int) -> str:
    """
    Costruisce il nome file per un'etichetta usando il pattern specificato.

    Args:
        pattern: Pattern nome file (es: "{Code}_{Color}_{Size}.dymo")
        row_data: Dati della riga
        row_index: Indice riga (1-based)

    Returns:
        Nome file pulito
    """
    safe_data = {k: "" if v is None else str(v) for k, v in row_data.items()}
    safe_data.setdefault("i", row_index)

    try:
        name = pattern.format(**safe_data)
    except KeyError:
        name = f"label_{row_index}.dymo"

    return sanitize_filename(name)


def generate_labels(
    template_xml: str,
    data_rows: List[Dict[str, str]],
    filename_pattern: str = "{Code}_{Color}_{Size}.dymo",
    limit: Optional[int] = None
) -> List[Tuple[str, str]]:
    """
    Genera tutte le etichette DYMO.

    Args:
        template_xml: Contenuto XML del template
        data_rows: Lista di righe dati
        filename_pattern: Pattern per nome file
        limit: Numero massimo di etichette da generare (None = tutte)

    Returns:
        Lista di tuple (filename, xml_content)
    """
    rows_to_process = data_rows[:limit] if limit else data_rows
    labels = []

    for idx, row in enumerate(rows_to_process, 1):
        filled_xml = fill_template(template_xml, row)
        filename = build_filename(filename_pattern, row, idx)
        labels.append((filename, filled_xml))

    return labels


def create_zip_archive(labels: List[Tuple[str, str]]) -> io.BytesIO:
    """
    Crea un archivio ZIP contenente tutte le etichette generate.

    Args:
        labels: Lista di tuple (filename, xml_content)

    Returns:
        BytesIO object contenente il file ZIP
    """
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in labels:
            zip_file.writestr(filename, content)

    zip_buffer.seek(0)
    return zip_buffer
