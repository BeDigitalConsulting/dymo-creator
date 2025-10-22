"""
Streamlit Web App per generazione etichette DYMO.
App dashboard per Bamboom - Carica Excel, Genera etichette, Scarica ZIP.

SELECTION ARCHITECTURE (Code-based tracking):
- selection_override: Dict[Code: bool] - Maps product Code to selection state
- Uses stable product Code instead of Pandas row index
- Survives file uploads, data reordering, UI sorting, row insertions/deletions
- Redundant overrides (matching group baseline) are automatically pruned
- File upload change detection resets all selection state
"""

import io
from pathlib import Path
import streamlit as st
import pandas as pd

from utils import (
    read_template,
    read_excel_data,
    merge_product_ean_data,
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
    st.header("📤 1. Carica File Dati")

    st.markdown("**File 1: Informazioni Prodotti**")
    product_file = st.file_uploader(
        "Carica il file con le informazioni prodotto (Code, Desc, Color, Size, Group, ecc.)",
        type=["xlsx", "xls", "csv"],
        help="Il file deve contenere le colonne: Code, Desc, Color, Size, Group",
        key="product_file_upload"
    )

    st.markdown("**File 2: Mappatura Codici EAN**")
    ean_file = st.file_uploader(
        "Carica il file con la mappatura EAN (Code, Barcode)",
        type=["xlsx", "xls", "csv"],
        help="Il file deve contenere le colonne: Code, Barcode",
        key="ean_file_upload"
    )

    # Verifica che entrambi i file siano stati caricati
    if product_file is None or ean_file is None:
        if product_file is None and ean_file is None:
            st.info("👆 Carica entrambi i file per iniziare")
        elif product_file is None:
            st.warning("⚠️ Carica il file prodotti per continuare")
        else:
            st.warning("⚠️ Carica il file EAN per continuare")
        st.stop()

    # Leggi il file prodotti
    try:
        # Converti uploaded_file in BytesIO
        product_bytes = io.BytesIO(product_file.read())
        product_extension = Path(product_file.name).suffix.lower()

        if product_extension in [".xlsx", ".xls"]:
            product_df, _ = read_excel_data(product_bytes, sheet=None)
        elif product_extension == ".csv":
            product_df, _ = read_excel_data(product_bytes, sep=",", encoding="utf-8")
        else:
            st.error("❌ Formato file prodotti non supportato")
            st.stop()

    except Exception as e:
        st.error(f"❌ Errore nella lettura del file prodotti: {str(e)}")
        st.stop()

    # Leggi il file EAN
    try:
        ean_bytes = io.BytesIO(ean_file.read())
        ean_extension = Path(ean_file.name).suffix.lower()

        if ean_extension in [".xlsx", ".xls"]:
            ean_df, _ = read_excel_data(ean_bytes, sheet=None)
        elif ean_extension == ".csv":
            ean_df, _ = read_excel_data(ean_bytes, sep=",", encoding="utf-8")
        else:
            st.error("❌ Formato file EAN non supportato")
            st.stop()

    except Exception as e:
        st.error(f"❌ Errore nella lettura del file EAN: {str(e)}")
        st.stop()

    # Unisci i due file
    try:
        df, merge_stats = merge_product_ean_data(product_df, ean_df)
        rows = df.to_dict(orient="records")

    except ValueError as e:
        st.error(f"❌ Errore nell'unione dei file: {str(e)}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Errore imprevisto: {str(e)}")
        st.stop()

    # Mostra statistiche
    st.success(f"✅ File caricati e uniti con successo!")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Prodotti totali", merge_stats['total'])
    with col2:
        st.metric("Con EAN", merge_stats['matched'], delta=None)
    with col3:
        st.metric("Senza EAN", merge_stats['unmatched'], delta=None)

    if merge_stats['unmatched'] > 0:
        st.warning(f"⚠️ {merge_stats['unmatched']} prodotti non hanno un codice EAN (il campo Barcode sarà vuoto)")

    # Sezione 2: Selezione Prodotti
    st.header("📋 2. Seleziona Prodotti")
    st.caption(f"📊 {len(rows)} prodotti totali nel file")

    # Store total count for selection summary
    total_products = len(rows)

    # Keep a full copy of df before filtering for counting all selections
    df_full = df.copy()

    # PHASE 2: File upload change detection and state reset
    # Track which files are currently loaded
    current_files = (product_file.name, ean_file.name)

    if 'uploaded_files' not in st.session_state:
        st.session_state['uploaded_files'] = current_files

    # If files changed, reset all selection state
    if st.session_state['uploaded_files'] != current_files:
        st.session_state['selected_groups'] = []
        st.session_state['selection_override'] = {}  # Now keyed by Code, not index
        st.session_state['selection_version'] = 0
        st.session_state['groups_display_limit'] = 5
        st.session_state['uploaded_files'] = current_files

    # Initialize session state for selections if not exists
    if 'selected_groups' not in st.session_state:
        st.session_state['selected_groups'] = []
    if 'selection_override' not in st.session_state:
        st.session_state['selection_override'] = {}  # PHASE 1: Now keyed by Code (str), not index (int)
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

                            # PHASE 3: Clear selection_override for ALL products in this group (use df_full, not df)
                            # Use Code-based tracking instead of index
                            group_codes = df_full[df_full['Group'] == group]['Code'].tolist()
                            for code in group_codes:
                                if code in st.session_state['selection_override']:
                                    del st.session_state['selection_override'][code]

                            # Increment version to force widget recreation with clean state
                            st.session_state['selection_version'] += 1
                            # PHASE 7: Clear data_editor's edited_rows with correct versioned key
                            widget_key = f'product_selector_{st.session_state["selection_version"] - 1}'
                            if widget_key in st.session_state:
                                del st.session_state[widget_key]

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

    # PHASE 4: Bulk action buttons with explicit scope
    # Make button text explicit about whether it affects filtered or all products
    link_col1, link_col2, link_col3 = st.columns([2.5, 1.0, 1.0])

    is_filtered = desc_search != ""
    select_text = "Seleziona visibili" if is_filtered else "Seleziona tutto"
    deselect_text = "Deseleziona visibili" if is_filtered else "Deseleziona tutto"

    with link_col2:
        if st.button(select_text, key="select_all_btn", help="Seleziona i prodotti mostrati", use_container_width=True):
            # PHASE 1: Use Code-based tracking instead of index
            # Get codes from currently displayed df (filtered or full)
            codes_to_select = df['Code'].tolist()
            for code in codes_to_select:
                st.session_state['selection_override'][code] = True

            # Increment version to force widget recreation with clean state
            st.session_state['selection_version'] += 1
            # PHASE 7: Clear data_editor's edited_rows with correct versioned key
            widget_key = f'product_selector_{st.session_state["selection_version"] - 1}'
            if widget_key in st.session_state:
                del st.session_state[widget_key]
            st.rerun()

    with link_col3:
        if st.button(deselect_text, key="clear_all_btn", help="Deseleziona i prodotti mostrati", use_container_width=True):
            # PHASE 1: Use Code-based tracking instead of index
            # Get codes from currently displayed df (filtered or full)
            codes_to_deselect = df['Code'].tolist()
            for code in codes_to_deselect:
                st.session_state['selection_override'][code] = False

            # Increment version to force widget recreation with clean state
            st.session_state['selection_version'] += 1
            # PHASE 7: Clear data_editor's edited_rows with correct versioned key
            widget_key = f'product_selector_{st.session_state["selection_version"] - 1}'
            if widget_key in st.session_state:
                del st.session_state[widget_key]
            st.rerun()

    # Interactive data editor wrapped in form to prevent rerun on every click
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

    # PHASE 1: Apply manual overrides to df to show current state in form
    # Now using Code-based tracking instead of index
    for code, override_value in st.session_state.get('selection_override', {}).items():
        # Find row(s) with this Code in the displayed df
        matching_rows = df[df['Code'] == code]
        if len(matching_rows) > 0:
            # Get the index in the displayed df (may be reset index if filtered)
            display_idx = matching_rows.index[0]
            df.at[display_idx, 'Selected'] = override_value

    # Store input df for comparison (to detect NEW changes)
    df_before_edit = df.copy()

    # Wrap data_editor in form to prevent rerun on every click
    # This solves both disappearing checkbox and scroll reset issues
    with st.form("product_selection_form", clear_on_submit=False):
        # Pass df with current selection state (group + manual overrides)
        # Form prevents rerun until submit button is clicked
        edited_df = st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            column_config=column_config,
            disabled=[col for col in df.columns if col not in ['Selected']],
            key=f"product_selector_{st.session_state['selection_version']}"
        )

        # Submit button to apply changes
        submitted = st.form_submit_button("✓ Applica Selezioni", use_container_width=True, type="primary")

    # PHASE 1: Only process changes when form is submitted
    # Use Code-based tracking instead of index to handle sorting/reordering
    manual_selections = {}
    if submitted:
        for idx in range(len(df_before_edit)):
            if idx < len(edited_df):
                old_value = df_before_edit.iloc[idx]['Selected']
                new_value = edited_df.iloc[idx]['Selected']
                if old_value != new_value:
                    # User changed this row - get the Code to identify it
                    code = df_before_edit.iloc[idx]['Code']
                    manual_selections[code] = new_value

    # PHASE 1: Build final selection state for full dataset
    # Priority: manual_selections > selection_override > group_selections
    # Now using Code-based tracking
    df_full_final = df_full.copy()

    # Start with group selections (already in df_full['Selected'])
    # Then apply stored overrides from previous sessions/filters
    for code, override_value in st.session_state.get('selection_override', {}).items():
        # Find row with this Code in df_full
        matching_rows = df_full_final[df_full_final['Code'] == code]
        if len(matching_rows) > 0:
            idx = matching_rows.index[0]
            df_full_final.at[idx, 'Selected'] = override_value

    # Finally apply current manual selections (highest priority)
    for code, manual_value in manual_selections.items():
        # Find row with this Code in df_full
        matching_rows = df_full_final[df_full_final['Code'] == code]
        if len(matching_rows) > 0:
            idx = matching_rows.index[0]
            df_full_final.at[idx, 'Selected'] = manual_value
            # Also update selection_override to persist this choice
            st.session_state['selection_override'][code] = manual_value

    # PHASE 5: Prune redundant overrides that match group baseline
    # This prevents the override dict from growing unbounded
    codes_to_remove = []
    for code, override_value in st.session_state.get('selection_override', {}).items():
        # Find this product's group
        product_rows = df_full_final[df_full_final['Code'] == code]
        if len(product_rows) > 0:
            group = product_rows.iloc[0]['Group']
            group_selected = group in st.session_state['selected_groups']
            # If override matches group baseline, it's redundant
            if override_value == group_selected:
                codes_to_remove.append(code)

    # Remove redundant overrides
    for code in codes_to_remove:
        del st.session_state['selection_override'][code]

    # If manual selections were made, reset widget state and rerun for clean state
    if manual_selections:
        # Increment version to force widget recreation with clean state
        st.session_state['selection_version'] += 1
        # PHASE 7: Clear data_editor's edited_rows with correct versioned key
        widget_key = f"product_selector_{st.session_state['selection_version'] - 1}"
        if widget_key in st.session_state:
            del st.session_state[widget_key]
        st.rerun()

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
