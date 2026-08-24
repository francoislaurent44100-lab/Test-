"""Registry of ADEME DPE datasets exposed on data.gouv.fr.

Discovered via the data.gouv.fr MCP tools (search_dataservices("DPE logements")).
Each dataset is served by ADEME's data-fair API, documented at
"<base_url>/api-docs.json" and queried through "<base_url>/lines".
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DpeDataset:
    key: str
    label: str
    base_url: str
    datagouv_dataservice_id: str
    primary_key: str = "N°DPE"


DATASETS = {
    "existant": DpeDataset(
        key="existant",
        label="DPE Logements existants (depuis juillet 2021)",
        base_url="https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant",
        datagouv_dataservice_id="6a32b72effd87aed836dffac",
    ),
    "neuf": DpeDataset(
        key="neuf",
        label="DPE Logements neufs (depuis juillet 2021)",
        base_url="https://data.ademe.fr/data-fair/api/v1/datasets/dpe02neuf",
        datagouv_dataservice_id="6a43986230662c6d0e7a4805",
    ),
    "tertiaire": DpeDataset(
        key="tertiaire",
        label="DPE Tertiaire (depuis juillet 2021)",
        base_url="https://data.ademe.fr/data-fair/api/v1/datasets/dpe01tertiaire",
        datagouv_dataservice_id="6a43986c6c96f658cf7d88df",
    ),
    "existant_avant_2021": DpeDataset(
        key="existant_avant_2021",
        label="DPE Logements (avant juillet 2021)",
        base_url="https://data.ademe.fr/data-fair/api/v1/datasets/dpe-france",
        datagouv_dataservice_id="6a4397d760eb5134015eafcc",
    ),
    "tertiaire_avant_2021": DpeDataset(
        key="tertiaire_avant_2021",
        label="DPE tertiaire (avant juillet 2021)",
        base_url="https://data.ademe.fr/data-fair/api/v1/datasets/dpe-tertiaire",
        datagouv_dataservice_id="6a439856d31be11940ba9177",
    ),
}

DEFAULT_DATASET = "existant"

# Core fields we always try to project out of the (very wide) ADEME schema.
# Exact availability/spelling is confirmed at run time via /schema and the
# extractor falls back to "select everything" if a field is missing, so this
# list is a convenience default rather than a hard requirement.
DEFAULT_SELECT = [
    "N°DPE",
    "Date_établissement_DPE",
    "Date_réception_DPE",
    "Etiquette_DPE",
    "Etiquette_GES",
    "Type_bâtiment",
    "Année_construction",
    "Surface_habitable_logement",
    "Adresse_BAN",
    "Code_postal_BAN",
    "Nom__commune_BAN",
    "Code_INSEE_BAN",
    "N°_département_BAN",
    "Conso_5_usages_par_m²_é_primaire",
    "Conso_5_usages_é_finale",
    "Emission_GES_5_usages_par_m²",
    "Coordonnée_cartographique_X_(BAN)",
    "Coordonnée_cartographique_Y_(BAN)",
]
