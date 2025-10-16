"""
Streamlit Web App per generazione etichette DYMO.
App dashboard per Bamboom - Carica Excel, Genera etichette, Scarica ZIP.
"""

import io
from pathlib import Path
import streamlit as st
import pandas as pd

from utils import (
    read_template,
    read_excel_data,
    validate_data,
    generate_labels,
    create_zip_archive
)


# Configurazione pagina
st.set_page_config(
    page_title="Generatore Etichette DYMO - Bamboom",
    page_icon="🏷️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS per brand BAMBOOM
st.markdown("""
<style>
    /* Brand colors e styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 500;
        border: 1px solid #E6E4E0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    .stButton>button:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }

    /* Success/info messages con brand colors */
    .stSuccess {
        background-color: rgba(142, 163, 149, 0.1);
        border-left: 4px solid #8EA395;
    }

    .stInfo {
        background-color: rgba(191, 201, 194, 0.1);
        border-left: 4px solid #BFC9C2;
    }

    /* Spacing migliorato */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Tabelle più eleganti */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# Template path (hardcoded come richiesto)
TEMPLATE_PATH = Path("template_update.dymo")
DEFAULT_FILENAME_PATTERN = "{Code}_{Color}_{Size}.dymo"


def main():
    # Header con Logo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("logo.png", width=300)
        except:
            st.title("🏷️ BAMBOOM")

    st.markdown("<h2 style='text-align: center;'>Generatore Etichette DYMO</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8E8E8E;'>Carica il tuo file Excel e genera le etichette DYMO</p>", unsafe_allow_html=True)
    st.divider()

    # Verifica che il template esista
    if not TEMPLATE_PATH.exists():
        st.error(f"❌ Template non trovato: {TEMPLATE_PATH}")
        st.info("Assicurati che il file `template_update.dymo` sia presente nella cartella del progetto.")
        st.stop()

    # Sezione 1: Upload file
    st.header("📤 1. Carica File Excel")
    uploaded_file = st.file_uploader(
        "Carica il tuo file Excel (.xlsx, .xls) o CSV",
        type=["xlsx", "xls", "csv"],
        help="Il file deve contenere le colonne: Code, Desc, Color, Size, Barcode"
    )

    if uploaded_file is None:
        st.info("👆 Carica un file Excel o CSV per iniziare")
        st.stop()

    # Leggi i dati
    try:
        # Converti uploaded_file in BytesIO
        file_bytes = io.BytesIO(uploaded_file.read())

        # Determina il tipo di file dall'estensione
        file_extension = Path(uploaded_file.name).suffix.lower()

        if file_extension in [".xlsx", ".xls"]:
            df, rows = read_excel_data(file_bytes, sheet=None)
        elif file_extension == ".csv":
            df, rows = read_excel_data(file_bytes, sep=",", encoding="utf-8")
        else:
            st.error("❌ Formato file non supportato")
            st.stop()

    except Exception as e:
        st.error(f"❌ Errore nella lettura del file: {str(e)}")
        st.stop()

    # Mostra statistiche
    st.success(f"✅ File caricato con successo: **{uploaded_file.name}**")
    st.metric("Numero di righe", len(rows))

    # Sezione 2: Anteprima dati
    st.header("📋 2. Anteprima Dati")

    # Mostra le prime 10 righe
    preview_rows = min(10, len(rows))
    st.dataframe(df.head(preview_rows), width="stretch")

    if len(rows) > preview_rows:
        st.caption(f"Mostrate le prime {preview_rows} righe di {len(rows)} totali")

    # Pattern fisso e genera tutte le etichette
    filename_pattern = DEFAULT_FILENAME_PATTERN
    limit_labels = 0

    # Sezione 3: Validazione
    st.header("✓ 3. Validazione")

    try:
        template_xml = read_template(TEMPLATE_PATH)
        validation = validate_data(template_xml, rows)

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Placeholder nel template:**")
            st.code(", ".join(sorted(validation['placeholders'])))

        with col2:
            st.write("**Colonne nel file Excel:**")
            st.code(", ".join(sorted(validation['columns'])))

        # Verifica validazione
        if not validation['is_valid']:
            st.error("❌ Validazione fallita!")
            st.write("**Placeholder mancanti nei dati:**")
            for missing in validation['missing']:
                st.write(f"- `{missing}`")
            st.warning("Il file Excel deve contenere tutte le colonne richieste dal template.")
            st.stop()
        else:
            st.success("✅ Validazione completata! Tutti i placeholder hanno colonne corrispondenti.")

        # Mostra colonne non usate (solo info)
        if validation['unused']:
            with st.expander("ℹ️ Colonne non utilizzate dal template"):
                st.write("Queste colonne sono presenti nei dati ma non vengono usate:")
                for unused in validation['unused']:
                    st.write(f"- `{unused}`")

    except Exception as e:
        st.error(f"❌ Errore nella validazione: {str(e)}")
        st.stop()

    # Sezione 4: Generazione
    st.header("🚀 4. Genera Etichette")

    # Genera tutte le etichette
    num_labels = len(rows)

    # Bottone genera
    if st.button("🏷️ Genera Etichette DYMO", type="primary", width="stretch"):
        try:
            with st.spinner(f"Generazione di {num_labels} etichette in corso..."):
                # Genera etichette
                labels = generate_labels(
                    template_xml,
                    rows,
                    filename_pattern,
                    limit=None
                )

                # Crea ZIP
                zip_buffer = create_zip_archive(labels)

                # Salva in session state per download
                st.session_state['zip_file'] = zip_buffer
                st.session_state['num_labels'] = len(labels)
                st.session_state['generated'] = True

            st.success(f"✅ {len(labels)} etichette generate con successo!")

        except Exception as e:
            st.error(f"❌ Errore durante la generazione: {str(e)}")
            st.exception(e)

    # Sezione 5: Download
    if st.session_state.get('generated', False):
        st.header("⬇️ 5. Download")

        zip_data = st.session_state['zip_file']
        num_labels = st.session_state['num_labels']

        # Genera nome file ZIP
        zip_filename = f"etichette_dymo_{num_labels}_labels.zip"

        st.download_button(
            label=f"📦 Scarica {num_labels} Etichette (ZIP)",
            data=zip_data,
            file_name=zip_filename,
            mime="application/zip",
            type="primary",
            width="stretch"
        )

        st.success(f"✅ {num_labels} file .dymo pronti per il download!")

        # Info aggiuntiva
        with st.expander("ℹ️ Come usare le etichette"):
            st.markdown("""
            1. Scarica il file ZIP
            2. Estrai tutti i file .dymo
            3. Apri i file con DYMO Label Software
            4. Stampa le etichette sulla tua stampante DYMO
            """)

    # Footer
    st.divider()
    st.caption("Bamboom - Generatore Etichette DYMO | Versione 1.0")


if __name__ == "__main__":
    main()
