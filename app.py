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
    if 'groups_display_limit' not in st.session_state:
        st.session_state['groups_display_limit'] = 5
    if 'selection_version' not in st.session_state:
        st.session_state['selection_version'] = 0

    # Group filter
    all_groups = sorted(df['Group'].unique()) if 'Group' in df.columns else []

    if all_groups:
        # Calculate product counts per group
        group_counts = df['Group'].value_counts().to_dict()

        # Sort groups by product count (descending)
        sorted_groups = sorted(all_groups, key=lambda g: group_counts.get(g, 0), reverse=True)

        # Display groups as checkboxes in a grid
        st.markdown("**Seleziona gruppi:**")

        # Search box for filtering groups (compact, no label, interactive)
        search_term = st.text_input(
            label="group_search_label",
            placeholder="Cerca gruppo...",
            key="group_search_input",
            label_visibility="collapsed"
        )

        # Determine which groups to display
        if search_term:
            # Search mode: show all matching groups
            filtered_groups = [g for g in sorted_groups if search_term.lower() in g.lower()]
            show_more_button = False
        else:
            # Normal mode: show top N groups based on display limit
            display_limit = st.session_state.get('groups_display_limit', 5)
            filtered_groups = sorted_groups[:display_limit]
            remaining_groups = len(sorted_groups) - display_limit
            show_more_button = remaining_groups > 0

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
                        checkbox_value = st.checkbox(f"{group} ({count})", value=is_selected, key=f"group_{group}")

                        if checkbox_value != is_selected:
                            # Group selection changed - update selected_groups and clear overrides for this group
                            if checkbox_value:
                                if group not in st.session_state['selected_groups']:
                                    st.session_state['selected_groups'].append(group)
                            else:
                                if group in st.session_state['selected_groups']:
                                    st.session_state['selected_groups'].remove(group)

                            # Clear selection_override for all rows in this group so group logic takes over
                            group_indices = df[df['Group'] == group].index.tolist()
                            for idx in group_indices:
                                if idx in st.session_state['selection_override']:
                                    del st.session_state['selection_override'][idx]

                            # Increment version to force widget recreation with clean state
                            st.session_state['selection_version'] += 1
                            # Clear data_editor's edited_rows to remove manual selections for this group
                            if 'product_selector' in st.session_state:
                                del st.session_state['product_selector']

        # Show "Mostra altri" or "Mostra meno" button
        if show_more_button:
            # There are more groups to show
            col1, col2, col3 = st.columns([1, 1, 3])
            with col1:
                if st.button(f"Mostra altri ({remaining_groups})", key="show_more_groups", use_container_width=True):
                    st.session_state['groups_display_limit'] += 10
                    st.rerun()
            # Show collapse button if we've expanded beyond initial 5
            if st.session_state.get('groups_display_limit', 5) > 5:
                with col2:
                    if st.button("Mostra meno", key="show_less_groups", use_container_width=True):
                        st.session_state['groups_display_limit'] = 5
                        st.rerun()
        elif st.session_state.get('groups_display_limit', 5) > 5:
            # All groups shown but we're expanded - show only collapse button
            if st.button("Mostra meno", key="show_less_groups_only", use_container_width=False):
                st.session_state['groups_display_limit'] = 5
                st.rerun()

        selected_groups = st.session_state['selected_groups']
    else:
        selected_groups = []
        st.warning("⚠️ Colonna 'Group' non trovata nel file")

    # Create base selection state from group selections only
    # This will be the "clean" base state for data_editor (no manual overrides)
    if selected_groups:
        base_selection = df['Group'].isin(selected_groups)
        base_selection_full = df_full['Group'].isin(selected_groups)
    else:
        base_selection = pd.Series([False] * len(df), index=df.index)
        base_selection_full = pd.Series([False] * len(df_full), index=df_full.index)

    # Add selection column for display DataFrame (group selections only, no overrides yet)
    if 'Selected' not in df.columns:
        df.insert(0, 'Selected', base_selection)

    # For full DataFrame, combine group selections + manual overrides
    if 'Selected' not in df_full.columns:
        df_full.insert(0, 'Selected', base_selection_full)

    # Product search box (searches both Code and Desc)
    desc_search = st.text_input(
        label="desc_search_label",
        placeholder="Cerca prodotto (codice o descrizione)...",
        key="desc_search_input",
        label_visibility="collapsed"
    )

    # Filter dataframe by Code or Desc search
    if desc_search:
        code_mask = df['Code'].str.contains(desc_search, case=False, na=False)
        desc_mask = df['Desc'].str.contains(desc_search, case=False, na=False)
        combined_mask = code_mask | desc_mask  # OR condition - match either column
        df = df[combined_mask].copy()
        # Store original indices before resetting
        df['_original_index'] = df.index
        # Reset index to avoid KeyError when accessing rows by position
        df.reset_index(drop=True, inplace=True)

    # Bulk action buttons
    link_col1, link_col2, link_col3 = st.columns([2.5, 1.0, 1.0])
    with link_col2:
        if st.button("Seleziona tutto", key="select_all_btn", help="Seleziona tutti i prodotti", use_container_width=True):
            # Use original indices if available (when filtered), otherwise use current indices
            if '_original_index' in df.columns:
                for i in range(len(df)):
                    orig_idx = df.iloc[i]['_original_index']
                    st.session_state['selection_override'][orig_idx] = True
            else:
                st.session_state['selection_override'] = {i: True for i in range(len(df))}
            # Increment version to force widget recreation with clean state
            st.session_state['selection_version'] += 1
            # Clear data_editor's edited_rows by deleting the widget state
            if 'product_selector' in st.session_state:
                del st.session_state['product_selector']
            st.rerun()
    with link_col3:
        if st.button("Deseleziona tutto", key="clear_all_btn", help="Deseleziona tutti i prodotti", use_container_width=True):
            # Use original indices if available (when filtered), otherwise use current indices
            if '_original_index' in df.columns:
                for i in range(len(df)):
                    orig_idx = df.iloc[i]['_original_index']
                    st.session_state['selection_override'][orig_idx] = False
            else:
                st.session_state['selection_override'] = {i: False for i in range(len(df))}
            # Increment version to force widget recreation with clean state
            st.session_state['selection_version'] += 1
            # Clear data_editor's edited_rows by deleting the widget state
            if 'product_selector' in st.session_state:
                del st.session_state['product_selector']
            st.rerun()

    # Apply manual overrides to display DataFrame so visual state matches actual selections
    # This ensures checkboxes in data_editor reflect selections from bulk buttons and previous sessions
    for idx, override_value in st.session_state.get('selection_override', {}).items():
        # Map override index to current df index
        if '_original_index' in df.columns:
            # When filtered, find row with matching original index
            matching_rows = df[df['_original_index'] == idx]
            if len(matching_rows) > 0:
                # Get the reset index (0-based position in filtered df)
                display_idx = matching_rows.index[0]
                df.at[display_idx, 'Selected'] = override_value
        else:
            # Not filtered, use index directly
            if idx < len(df):
                df.at[idx, 'Selected'] = override_value

    # Interactive data editor
    column_config = {
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
    }

    # Hide _original_index column if it exists
    if '_original_index' in df.columns:
        column_config["_original_index"] = None

    # Store input df for comparison (to detect NEW changes)
    df_before_edit = df.copy()

    # Pass df with current selection state to data_editor
    # Visual checkboxes will match actual selections (group + manual overrides)
    # Use versioned key: increments on bulk/group changes to force widget recreation
    # but stays stable for manual selections to avoid disappearing checkboxes
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        disabled=[col for col in df.columns if col not in ['Selected']],
        key=f"product_selector_{st.session_state['selection_version']}"
    )

    # Detect NEW manual selections by comparing input to output
    # This avoids state conflicts with edited_rows
    manual_selections = {}
    for idx in range(len(df_before_edit)):
        if idx < len(edited_df):
            old_value = df_before_edit.iloc[idx]['Selected']
            new_value = edited_df.iloc[idx]['Selected']
            if old_value != new_value:
                # User changed this row in THIS render
                # Map display index to original index
                if '_original_index' in df.columns:
                    orig_idx = int(df.iloc[idx]['_original_index'])
                else:
                    orig_idx = idx

                manual_selections[orig_idx] = new_value

    # Build final selection state for full dataset
    # Priority: manual_selections > selection_override > group_selections
    df_full_final = df_full.copy()

    # Start with group selections (already in df_full['Selected'])
    # Then apply stored overrides from previous sessions/filters
    for idx, override_value in st.session_state.get('selection_override', {}).items():
        if idx < len(df_full_final):
            df_full_final.at[idx, 'Selected'] = override_value

    # Finally apply current manual selections (highest priority)
    for idx, manual_value in manual_selections.items():
        if idx < len(df_full_final):
            df_full_final.at[idx, 'Selected'] = manual_value
            # Also update selection_override to persist this choice
            st.session_state['selection_override'][idx] = manual_value

    # Selection summary - count from full dataset
    num_selected_total = int(df_full_final['Selected'].sum())
    st.info(f"**{num_selected_total}** di **{total_products}** prodotti selezionati")

    if num_selected_total == 0:
        st.warning("⚠️ Nessun prodotto selezionato. Seleziona almeno un prodotto per continuare.")
        st.stop()

    # Filter rows to only selected ones from the final dataset
    selected_mask = df_full_final['Selected'] == True
    selected_df = df_full_final[selected_mask].copy()
    selected_df = selected_df.drop(columns=['Selected'])  # Remove selection column

    # Remove _original_index if it exists
    if '_original_index' in selected_df.columns:
        selected_df = selected_df.drop(columns=['_original_index'])

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
