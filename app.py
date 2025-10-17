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
    page_icon="favicon.jpg",
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

    /* Text links for bulk actions */
    .text-link {
        color: #8EA395;
        text-decoration: none;
        cursor: pointer;
        font-size: 0.9rem;
        margin: 0 0.5rem;
    }

    .text-link:hover {
        text-decoration: underline;
        color: #6B8271;
    }

    /* Compact success message */
    .success-compact {
        padding: 0.5rem 1rem;
        margin-bottom: 1rem;
    }

    /* Group checkbox grid */
    .group-checkbox-container {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 0.5rem;
        margin: 1rem 0;
    }

    .group-checkbox-item {
        padding: 0.4rem 0.6rem;
        border: 1px solid #E6E4E0;
        border-radius: 6px;
        font-size: 0.9rem;
    }

    .group-checkbox-item:hover {
        background-color: rgba(142, 163, 149, 0.05);
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

    # Sezione 2: Selezione Prodotti
    st.header("📋 2. Seleziona Prodotti")
    st.caption(f"📊 {len(rows)} prodotti totali nel file")

    # Store total count for selection summary
    total_products = len(rows)

    # Keep a full copy of df before filtering for counting all selections
    df_full = df.copy()

    # Initialize session state for selections if not exists
    if 'selected_groups' not in st.session_state:
        st.session_state['selected_groups'] = []
    if 'selection_override' not in st.session_state:
        st.session_state['selection_override'] = {}
    if 'desc_search' not in st.session_state:
        st.session_state['desc_search'] = ""

    # Group filter
    all_groups = sorted(df['Group'].unique()) if 'Group' in df.columns else []

    if all_groups:
        # Calculate product counts per group
        group_counts = df['Group'].value_counts().to_dict()

        # Display groups as checkboxes in a grid
        st.markdown("**Seleziona gruppi:**")

        # Search box for filtering groups (compact, no label, interactive)
        search_term = st.text_input(
            label="group_search_label",
            placeholder="Cerca gruppo...",
            key="group_search_input",
            label_visibility="collapsed"
        )

        # Filter groups based on search
        filtered_groups = [g for g in all_groups if search_term.lower() in g.lower()]

        # Create columns for checkbox grid (5 per row)
        num_cols = 5
        for i in range(0, len(filtered_groups), num_cols):
            cols = st.columns(num_cols)
            for j, col in enumerate(cols):
                if i + j < len(filtered_groups):
                    group = filtered_groups[i + j]
                    count = group_counts.get(group, 0)
                    with col:
                        is_selected = group in st.session_state['selected_groups']
                        if st.checkbox(f"{group} ({count})", value=is_selected, key=f"group_{group}"):
                            if group not in st.session_state['selected_groups']:
                                st.session_state['selected_groups'].append(group)
                        else:
                            if group in st.session_state['selected_groups']:
                                st.session_state['selected_groups'].remove(group)

        selected_groups = st.session_state['selected_groups']
    else:
        selected_groups = []
        st.warning("⚠️ Colonna 'Group' non trovata nel file")

    # Add selection column to both dataframes
    if 'Selected' not in df.columns:
        # Auto-select rows based on group filter
        if selected_groups:
            df.insert(0, 'Selected', df['Group'].isin(selected_groups))
            df_full.insert(0, 'Selected', df_full['Group'].isin(selected_groups))
        else:
            df.insert(0, 'Selected', False)
            df_full.insert(0, 'Selected', False)

    # Apply manual overrides from session state to BOTH dataframes
    for idx, override_value in st.session_state.get('selection_override', {}).items():
        if idx < len(df):
            df.at[idx, 'Selected'] = override_value
        if idx < len(df_full):
            df_full.at[idx, 'Selected'] = override_value

    # Desc filter search box
    desc_search = st.text_input(
        label="desc_search_label",
        placeholder="Cerca nella descrizione...",
        key="desc_search_input",
        label_visibility="collapsed"
    )

    # Filter dataframe by Desc search
    if desc_search:
        desc_mask = df['Desc'].str.contains(desc_search, case=False, na=False)
        df = df[desc_mask].copy()
        # Reset index to avoid KeyError when accessing rows by position
        df.reset_index(drop=True, inplace=True)

    # Bulk action buttons
    link_col1, link_col2, link_col3 = st.columns([2.5, 1.0, 1.0])
    with link_col2:
        if st.button("Seleziona tutto", key="select_all_btn", help="Seleziona tutti i prodotti", use_container_width=True):
            df['Selected'] = True
            st.session_state['selection_override'] = {i: True for i in range(len(df))}
            st.rerun()
    with link_col3:
        if st.button("Deseleziona tutto", key="clear_all_btn", help="Deseleziona tutti i prodotti", use_container_width=True):
            df['Selected'] = False
            st.session_state['selection_override'] = {i: False for i in range(len(df))}
            st.rerun()

    # Interactive data editor
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Selected": st.column_config.CheckboxColumn(
                "Seleziona",
                help="Seleziona i prodotti per cui generare etichette",
                default=False,
            ),
            "Desc": st.column_config.TextColumn(
                "Desc",
                help="Descrizione prodotto",
                width="medium",
            )
        },
        disabled=[col for col in df.columns if col != 'Selected'],
        key="product_selector"
    )

    # Update selection overrides using iloc for positional access
    for idx in range(len(edited_df)):
        # Use iloc to access by position instead of label (handles filtered/reset indices)
        if idx < len(df):
            edited_value = edited_df.iloc[idx]['Selected']
            original_value = df.iloc[idx]['Selected']
            if edited_value != original_value:
                st.session_state['selection_override'][idx] = edited_value

    # Selection summary - count from full dataset, not just filtered view
    num_selected_total = df_full['Selected'].sum()
    st.info(f"**{num_selected_total}** di **{total_products}** prodotti selezionati")

    if num_selected_total == 0:
        st.warning("⚠️ Nessun prodotto selezionato. Seleziona almeno un prodotto per continuare.")
        st.stop()

    # Filter rows to only selected ones
    selected_mask = edited_df['Selected'] == True
    selected_df = edited_df[selected_mask].copy()
    selected_df = selected_df.drop(columns=['Selected'])  # Remove selection column
    selected_rows = selected_df.to_dict(orient="records")

    # Pattern fisso e genera tutte le etichette
    filename_pattern = DEFAULT_FILENAME_PATTERN
    limit_labels = 0

    # Sezione 3: Validazione
    st.header("✓ 3. Validazione")

    try:
        template_xml = read_template(TEMPLATE_PATH)
        validation = validate_data(template_xml, selected_rows)

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

    # Genera solo le etichette selezionate
    num_labels = len(selected_rows)

    # Bottone genera
    if st.button(f"🏷️ Genera {num_labels} Etichette Selezionate", type="primary", width="stretch"):
        try:
            with st.spinner(f"Generazione di {num_labels} etichette in corso..."):
                # Genera etichette
                labels = generate_labels(
                    template_xml,
                    selected_rows,
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
