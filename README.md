# VES On-set VFX Data Collection and usage web site.

> [!NOTE]
> This project uses a Python virtual environment. Please use `source .venv/bin/activate` or use the python executable at `.venv/bin/python3` when running scripts.

On-set VFX Data Collection and usage web site. This processes the google doc https://docs.google.com/document/d/13TsptYa5uNO52btOw1nat1cLSBG88t27W3BXHBZPvoc/edit?tab=t.0#heading=h.h7s96q27odn9 into a format that is easily filterable, since the document is huge and can be overwhelming.

## Setup
1.  Ensure you have Python 3 installed.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Data Import
The dashboard data is generated from a Google Doc export.

### Option 1: Automatic Download (Recommended)
Run the converter with the Google Doc ID:
```bash
python3 data/convert_doc.py --doc-id 13TsptYa5uNO52btOw1nat1cLSBG88t27W3BXHBZPvoc
```
This will automatically download the HTML export and update `data/data.json` and `data/directory_data.json`.

### Option 2: Manual Import
1.  **Export the Google Doc**:
    *   Open the source Google Doc.
    *   Go to **File > Download > Web Page (.html, zipped)**.
2.  **Prepare the File**:
    *   Unzip the downloaded file.
    *   Rename the HTML file inside to `doc_export.html`.
    *   Place it in the `data/` directory of this repository.
3.  **Run the Converter**:
    ```bash
    python3 data/convert_doc.py
    ```

## Running the Dashboard

The dashboard now loads data via `fetch()`, so a local HTTP server is required:

```bash
python3 -m http.server 8080
```

Then open **http://localhost:8080/dashboard/index.html** in your browser.

> [!NOTE]
> Opening `dashboard/index.html` directly as a `file://` URL will no longer work because browsers block `fetch()` requests on the `file://` protocol.

## Authors

Web page and import script by Sam Richards.
On-set document by Sheena Duggal with contributions from Sam Richards, Jim Geduldick, and Jake Morrison, and technical support from Jean-Francois Panisset