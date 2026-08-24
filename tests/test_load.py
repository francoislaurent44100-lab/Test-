import json
import sqlite3

from dpe_pipeline.load import SqliteLoader


def test_upsert_creates_table_and_columns(tmp_path):
    db_path = str(tmp_path / "dpe.db")
    rows = [
        {"ndpe": "A1", "etiquette_dpe": "D", "surface_habitable_logement": 62.5},
        {"ndpe": "A2", "etiquette_dpe": "F"},  # missing a column present in the other row
    ]
    with SqliteLoader(db_path, table="existant", primary_key="N°DPE") as loader:
        loaded = loader.upsert_many(rows, source_dataset="existant")

    assert loaded == 2
    conn = sqlite3.connect(db_path)
    cols = {r[1] for r in conn.execute('PRAGMA table_info("existant")')}
    assert {"ndpe", "etiquette_dpe", "surface_habitable_logement", "_source_dataset", "_raw_json"} <= cols

    row_a1 = conn.execute('SELECT etiquette_dpe, surface_habitable_logement FROM "existant" WHERE ndpe = ?', ("A1",)).fetchone()
    assert row_a1 == ("D", "62.5")
    row_a2 = conn.execute('SELECT etiquette_dpe, surface_habitable_logement FROM "existant" WHERE ndpe = ?', ("A2",)).fetchone()
    assert row_a2 == ("F", None)


def test_upsert_replaces_existing_row(tmp_path):
    db_path = str(tmp_path / "dpe.db")
    with SqliteLoader(db_path, table="existant", primary_key="N°DPE") as loader:
        loader.upsert_many([{"ndpe": "A1", "etiquette_dpe": "D"}], source_dataset="existant")
        loader.upsert_many([{"ndpe": "A1", "etiquette_dpe": "A"}], source_dataset="existant")

    conn = sqlite3.connect(db_path)
    rows = conn.execute('SELECT etiquette_dpe FROM "existant"').fetchall()
    assert rows == [("A",)]


def test_raw_json_column_preserves_full_row(tmp_path):
    db_path = str(tmp_path / "dpe.db")
    row = {"ndpe": "A1", "etiquette_dpe": "D", "annee_construction": 1975}
    with SqliteLoader(db_path, table="existant", primary_key="N°DPE") as loader:
        loader.upsert_many([row], source_dataset="existant")

    conn = sqlite3.connect(db_path)
    raw = conn.execute('SELECT _raw_json, _source_dataset FROM "existant"').fetchone()
    assert json.loads(raw[0]) == row
    assert raw[1] == "existant"
