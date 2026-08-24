import sqlite3
from unittest.mock import MagicMock, patch

from dpe_pipeline.cli import build_qs
from dpe_pipeline.pipeline import resolve_dataset, run


def test_resolve_dataset_known_and_unknown():
    assert resolve_dataset("existant").key == "existant"
    try:
        resolve_dataset("nope")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "existant" in str(exc)


def test_build_qs_combines_filters():
    qs = build_qs(department="75", commune_insee=None, since="2024-01-01", until="2024-12-31")
    assert qs == 'N°_département_BAN:"75" AND Date_établissement_DPE:[2024-01-01 TO 2024-12-31]'
    assert build_qs(None, None, None, None) is None


def test_run_end_to_end_with_fake_client(tmp_path):
    fake_records = [
        {"N°DPE": "A1", "Etiquette_DPE": "D", "Surface_habitable_logement": "62.5"},
        {"N°DPE": "A2", "Etiquette_DPE": "A", "Surface_habitable_logement": "45"},
    ]

    fake_client = MagicMock()
    fake_client.available_fields.return_value = {"N°DPE", "Etiquette_DPE", "Surface_habitable_logement"}
    fake_client.iter_lines.return_value = iter(fake_records)

    with patch("dpe_pipeline.pipeline.AdemeDpeClient", return_value=fake_client):
        result = run(dataset_key="existant", db_path=str(tmp_path / "dpe.db"))

    assert result.records_loaded == 2
    conn = sqlite3.connect(result.db_path)
    rows = conn.execute('SELECT ndpe, etiquette_dpe FROM "existant" ORDER BY ndpe').fetchall()
    assert rows == [("A1", "D"), ("A2", "A")]


def test_run_respects_limit(tmp_path):
    fake_records = ({"N°DPE": f"A{i}", "Etiquette_DPE": "D"} for i in range(100))

    fake_client = MagicMock()
    fake_client.available_fields.return_value = {"N°DPE", "Etiquette_DPE"}
    fake_client.iter_lines.return_value = fake_records

    with patch("dpe_pipeline.pipeline.AdemeDpeClient", return_value=fake_client):
        result = run(dataset_key="existant", db_path=str(tmp_path / "dpe.db"), limit=5)

    assert result.records_loaded == 5
