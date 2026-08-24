# DPE pipeline

An extract/transform/load pipeline for French DPE (*Diagnostic de
Performance Énergétique*) records, published by ADEME and catalogued on
[data.gouv.fr](https://www.data.gouv.fr).

## Data source

The datasets were located with the data.gouv.fr MCP tools
(`search_dataservices("DPE logements")`). ADEME exposes each DPE dataset
through its own [data-fair](https://koumoul-dev.github.io/data-fair/) REST
API (paginated JSON, live/continuously updated for the two "depuis juillet
2021" datasets). `dpe_pipeline/config.py` registers the five datasets found:

| key                     | dataset                                      |
|--------------------------|-----------------------------------------------|
| `existant` (default)     | DPE Logements existants (depuis juillet 2021) |
| `neuf`                    | DPE Logements neufs (depuis juillet 2021)     |
| `tertiaire`                | DPE Tertiaire (depuis juillet 2021)           |
| `existant_avant_2021`     | DPE Logements (avant juillet 2021, frozen)    |
| `tertiaire_avant_2021`     | DPE tertiaire (avant juillet 2021, frozen)    |

## Pipeline

```
ADEME data-fair API  --client.py-->  raw JSON records
                       (pagination via the "next" cursor, retry/backoff,
                        429 handling, /schema introspection)

raw records  --transform.py-->  normalized rows
             (French/accented keys -> snake_case, numeric coercion)

normalized rows  --load.py-->  SQLite database
                  (upsert by N°DPE, auto-adds new columns, keeps the
                   full raw record as JSON alongside the flattened columns)
```

`dpe_pipeline/pipeline.py` wires the three stages together; `dpe_pipeline/cli.py`
exposes them as a command.

## Usage

```bash
pip install -r requirements.txt

# List the known datasets and their API base URLs
python -m dpe_pipeline list-datasets

# Load every 2024 DPE for department 75 (Paris) into ./dpe.db
python -m dpe_pipeline run --dataset existant --departement 75 \
    --since 2024-01-01 --until 2024-12-31 --db dpe.db -v

# Advanced filtering: pass a raw data-fair Lucene query string directly
python -m dpe_pipeline run --qs 'Etiquette_DPE:"G" AND Code_postal_BAN:69*'
```

Output is one SQLite table per dataset (e.g. `existant`), with a text
column per API field (dynamically discovered — the ADEME schema is wide
and evolves) plus `_source_dataset` and `_raw_json` bookkeeping columns.
Re-running the same command upserts rows by `N°DPE`, so it's safe to run
on a schedule for incremental refreshes.

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

All HTTP calls are mocked in tests (`tests/test_client.py`,
`tests/fixtures/*.json`) — the sandbox this pipeline was built in has no
network egress to `data.ademe.fr`, so the ADEME API was explored via the
data.gouv.fr MCP tools (schema/field names below) rather than live HTTP
calls, and the fixtures mirror ADEME's documented field set. Before
relying on this in production, run `python -m dpe_pipeline run --limit 5 -v`
once against the real API to confirm the field names still match; the
pipeline degrades gracefully (falls back to selecting every field) if
`DEFAULT_SELECT` in `config.py` drifts from the live schema.
