# Repository Guidelines

## Project Structure & Module Organization
- `app.py` is the Streamlit UI orchestrating data import, validation, and label generation.
- `utils.py` holds reusable data handling and label logic; keep business rules centralized there.
- `generate_dymo_files.py` exposes the CLI flow for batch runs and mirrors the web pipeline.
- `template_update.dymo` plus the `template/` directory store label XML layouts; keep generated archives under `out/` out of version control.
- Test spreadsheets and fixtures live in `test_data/`; sample Excel files for manual validation sit at the repo root.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` creates an isolated environment (`.venv\Scripts\activate` on PowerShell).
- `pip install -r requirements.txt` installs Streamlit, pandas, and openpyxl.
- `streamlit run app.py` serves the dashboard at `http://localhost:8501`; keep the terminal open to watch validation logs.
- `python generate_dymo_files.py --template template_update.dymo --data data_test.xlsx --ean-data test_data/barcode_code_only.xlsx --dry-run` validates template/data alignment without writing files.

## Coding Style & Naming Conventions
- Follow PEP 8 with four-space indentation; prefer descriptive snake_case identifiers (`merge_product_ean_data`).
- Keep pure logic in `utils.py` with docstrings in English; UI copy and emojis stay Italian to match branding.
- Reuse helper functions instead of duplicating Streamlit widget patterns; place new modules alongside existing Python entry points.

## Testing Guidelines
- No automated suite yet; add lightweight `pytest` coverage around `utils.py` before altering data transforms.
- For manual QA, run the CLI `--dry-run`, inspect merge statistics, then generate a small batch into `out/` and open the ZIP.
- Use spreadsheets in `test_data/` to exercise edge cases (missing barcodes, partial attributes).

## Commit & Pull Request Guidelines
- Commit summaries stay short, imperative, and <72 characters (`Fix selection issues with st.form() wrapper`).
- Pull requests should outline motivation, link the relevant task/issue, list validation steps, and attach screenshots or sample output for UI changes.
- Confirm the Streamlit app starts cleanly and the CLI dry run passes before requesting review; call out any skipped checks or known data limitations.
