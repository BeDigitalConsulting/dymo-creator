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

# Template path (hardcoded come richiesto)
TEMPLATE_PATH = Path("template_update.dymo")
DEFAULT_FILENAME_PATTERN = "{Code}_{Color}_{Size}.dymo"


def main():
    # Header
    st.title("🏷️ Generatore Etichette DYMO")
    st.markdown("**Bamboom** - Carica il tuo file Excel e genera le etichette DYMO")
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
    st.dataframe(df.head(preview_rows), use_container_width=True)

    if len(rows) > preview_rows:
        st.caption(f"Mostrate le prime {preview_rows} righe di {len(rows)} totali")

    # Sezione 3: Configurazione
    st.header("⚙️ 3. Configurazione")

    col1, col2 = st.columns(2)

    with col1:
        filename_pattern = st.text_input(
            "Pattern nome file",
            value=DEFAULT_FILENAME_PATTERN,
            help="Usa le intestazioni delle colonne tra graffe. Es: {Code}_{Color}_{Size}.dymo"
        )

    with col2:
        limit_labels = st.number_input(
            "Limite etichette (0 = tutte)",
            min_value=0,
            max_value=len(rows),
            value=0,
            help="Utile per test. 0 genera tutte le etichette."
        )

    # Sezione 4: Validazione
    st.header("✓ 4. Validazione")

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

    # Sezione 5: Generazione
    st.header("🚀 5. Genera Etichette")

    # Mostra anteprima nome file
    if rows:
        example_filename = generate_labels(
            template_xml,
            rows[:1],
            filename_pattern,
            limit=1
        )[0][0]
        st.info(f"📄 Esempio nome file: `{example_filename}`")

    # Determina quante etichette generare
    num_labels = limit_labels if limit_labels > 0 else len(rows)

    # Bottone genera
    if st.button("🏷️ Genera Etichette DYMO", type="primary", use_container_width=True):
        try:
            with st.spinner(f"Generazione di {num_labels} etichette in corso..."):
                # Genera etichette
                labels = generate_labels(
                    template_xml,
                    rows,
                    filename_pattern,
                    limit=limit_labels if limit_labels > 0 else None
                )

                # Crea ZIP
                zip_buffer = create_zip_archive(labels)

                # Salva in session state per download
                st.session_state['zip_file'] = zip_buffer
                st.session_state['num_labels'] = len(labels)
                st.session_state['generated'] = True

            st.success(f"✅ {len(labels)} etichette generate con successo!")
            st.balloons()

        except Exception as e:
            st.error(f"❌ Errore durante la generazione: {str(e)}")
            st.exception(e)

    # Sezione 6: Download
    if st.session_state.get('generated', False):
        st.header("⬇️ 6. Download")

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
            use_container_width=True
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
