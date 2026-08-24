from dpe_pipeline.transform import (
    dpe_letter_bucket,
    normalize_record,
    parse_iso_date,
    to_snake_case,
)


def test_to_snake_case_strips_accents_and_symbols():
    assert to_snake_case("N°DPE") == "ndpe"
    assert to_snake_case("N°_département_BAN") == "n_departement_ban"
    assert to_snake_case("Conso_5_usages_par_m²_é_primaire") == "conso_5_usages_par_m2_e_primaire"


def test_normalize_record_renames_and_coerces():
    raw = {
        "N°DPE": "2400E1234567A",
        "Surface_habitable_logement": "62.5",
        "Année_construction": "1975",
        "Etiquette_DPE": "D",
        "Date_établissement_DPE": "",
    }
    row = normalize_record(raw)
    assert row["ndpe"] == "2400E1234567A"
    assert row["surface_habitable_logement"] == 62.5
    assert row["annee_construction"] == 1975
    assert row["etiquette_dpe"] == "D"
    assert row["date_etablissement_dpe"] is None


def test_dpe_letter_bucket():
    assert dpe_letter_bucket("A") == "sobre"
    assert dpe_letter_bucket("c") == "sobre"
    assert dpe_letter_bucket("D") == "moyen"
    assert dpe_letter_bucket("G") == "passoire"
    assert dpe_letter_bucket(None) == "inconnu"
    assert dpe_letter_bucket("Z") == "inconnu"


def test_parse_iso_date():
    assert parse_iso_date("2024-03-15").isoformat() == "2024-03-15"
    assert parse_iso_date("2024-03-15T10:00:00Z").isoformat() == "2024-03-15"
    assert parse_iso_date(None) is None
    assert parse_iso_date("not-a-date") is None
