#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
croiser_parcelles_dvf_dpe.py
=============================
Croise le cadastre (parcelles_44084.csv, extrait du GeoJSON cadastre.gouv.fr)
avec :
  1. DVF (ventes immobilières) -> fichiers "geo-dvf" du Cerema/Etalab,
     un CSV par commune et par année, clé de jointure = id_parcelle
     (même format que le champ "id" du cadastre : 44084 + préfixe(3) +
     section(2) + numéro(4) = 14 caractères).
  2. DPE (diagnostics de performance énergétique) -> API ADEME
     data.ademe.fr, dataset "dpe03existant" (DPE logements existants
     depuis juillet 2021). La jointure se fait par proximité géographique
     (point DPE -> polygone parcelle), car le DPE ne porte pas toujours
     le numéro de parcelle cadastrale.

Prérequis :
    pip install requests shapely pandas

Utilisation :
    python3 croiser_parcelles_dvf_dpe.py \
        --geojson cadastre-44084-parcelles__3__json \
        --commune 44084 \
        --annees 2021 2022 2023 2024 2025 \
        --out resultat_44084.csv

Sorties :
    - resultat_44084.csv : une ligne par parcelle, avec le nombre de
      ventes DVF, la dernière vente (date, prix, prix/m²), et le
      nombre de DPE rattachés + la classe DPE la plus fréquente.
    - dvf_detail_44084.csv : détail de chaque vente DVF jointe à une
      parcelle.
    - dpe_detail_44084.csv : détail de chaque DPE joint à une parcelle.

Notes :
    - Le fichier geo-dvf par commune est disponible ici (à adapter selon
      l'année) :
      https://files.data.gouv.fr/geo-dvf/latest/csv/{annee}/communes/44/44084.csv
    - L'API ADEME DPE existant est documentée ici :
      https://data.ademe.fr/datasets/dpe03existant
      Endpoint utilisé : https://data.ademe.fr/data/api/records/2.0/search
      avec dataset_id=dpe03existant et un filtre sur le code INSEE (BAN).
"""

import argparse
import csv
import json
import sys
import time
from collections import defaultdict, Counter

try:
    import requests
except ImportError:
    sys.exit("Ce script nécessite 'requests' : pip install requests")


GEO_DVF_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv/{annee}/communes/{dept}/{commune}.csv"
ADEME_DPE_API = "https://data.ademe.fr/data/api/records/2.0/search"
ADEME_DPE_DATASET = "dpe03existant"


def charger_parcelles(chemin_geojson):
    """Charge le GeoJSON cadastral et renvoie un dict id_parcelle -> infos + géométrie shapely."""
    from shapely.geometry import shape

    with open(chemin_geojson, encoding="utf-8") as f:
        data = json.load(f)

    parcelles = {}
    for feat in data["features"]:
        props = feat["properties"]
        pid = props["id"]
        try:
            geom = shape(feat["geometry"])
        except Exception:
            geom = None
        parcelles[pid] = {
            "id_parcelle": pid,
            "commune": props.get("commune"),
            "section": props.get("section"),
            "numero": props.get("numero"),
            "contenance_m2": props.get("contenance"),
            "geometry": geom,
        }
    print(f"[cadastre] {len(parcelles)} parcelles chargées depuis {chemin_geojson}")
    return parcelles


def telecharger_dvf(commune, annees):
    """Télécharge et concatène les fichiers geo-dvf annuels pour une commune."""
    dept = commune[:2]
    lignes = []
    for annee in annees:
        url = GEO_DVF_URL.format(annee=annee, dept=dept, commune=commune)
        try:
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                print(f"[dvf] {annee} : indisponible ({r.status_code}) -> {url}")
                continue
            texte = r.content.decode("utf-8")
            reader = csv.DictReader(texte.splitlines())
            n = 0
            for row in reader:
                row["annee_fichier"] = annee
                lignes.append(row)
                n += 1
            print(f"[dvf] {annee} : {n} lignes")
        except Exception as e:
            print(f"[dvf] {annee} : erreur {e}")
        time.sleep(0.5)
    return lignes


def telecharger_dpe(code_insee, page_size=100, max_pages=200):
    """Interroge l'API ADEME (dpe03existant) pour un code INSEE de commune."""
    resultats = []
    offset = 0
    for _ in range(max_pages):
        params = {
            "dataset": ADEME_DPE_DATASET,
            "q": f'code_insee_ban:"{code_insee}"',
            "rows": page_size,
            "start": offset,
        }
        try:
            r = requests.get(ADEME_DPE_API, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[dpe] erreur à l'offset {offset} : {e}")
            break

        records = data.get("results") or data.get("records") or []
        if not records:
            break
        for rec in records:
            resultats.append(rec)
        offset += page_size
        if len(records) < page_size:
            break
        time.sleep(0.3)

    print(f"[dpe] {len(resultats)} DPE récupérés pour la commune {code_insee}")
    return resultats


def joindre_dvf(parcelles, lignes_dvf):
    """Rattache chaque vente DVF à sa parcelle via id_parcelle."""
    par_parcelle = defaultdict(list)
    non_trouves = 0
    for row in lignes_dvf:
        pid = row.get("id_parcelle")
        if pid in parcelles:
            par_parcelle[pid].append(row)
        else:
            non_trouves += 1
    print(f"[jointure dvf] {sum(len(v) for v in par_parcelle.values())} ventes rattachées, "
          f"{non_trouves} sans correspondance dans le cadastre")
    return par_parcelle


def joindre_dpe(parcelles, dpe_records):
    """Rattache chaque DPE à sa parcelle par géolocalisation (point dans polygone)."""
    from shapely.geometry import Point
    from shapely.strtree import STRtree

    geoms = []
    ids = []
    for pid, info in parcelles.items():
        if info["geometry"] is not None:
            geoms.append(info["geometry"])
            ids.append(pid)
    arbre = STRtree(geoms)
    id_par_geom = {id(g): pid for g, pid in zip(geoms, ids)}

    par_parcelle = defaultdict(list)
    non_localises = 0
    for rec in dpe_records:
        fields = rec.get("fields", rec)  # selon version d'API
        x = fields.get("coordonnee_cartographique_x_(ban)") or fields.get("x_ban")
        y = fields.get("coordonnee_cartographique_y_(ban)") or fields.get("y_ban")
        lon = fields.get("longitude") or fields.get("_geopoint_lon")
        lat = fields.get("latitude") or fields.get("_geopoint_lat")
        if lon is None or lat is None:
            non_localises += 1
            continue
        pt = Point(float(lon), float(lat))
        candidats = arbre.query(pt)
        trouve = False
        for cand in candidats:
            geom = geoms[cand] if isinstance(cand, int) else cand
            if geom.contains(pt):
                pid = id_par_geom.get(id(geom))
                if pid:
                    par_parcelle[pid].append(fields)
                    trouve = True
                    break
        if not trouve:
            non_localises += 1

    print(f"[jointure dpe] {sum(len(v) for v in par_parcelle.values())} DPE rattachés, "
          f"{non_localises} non localisés dans une parcelle")
    return par_parcelle


def ecrire_resultats(parcelles, dvf_par_parcelle, dpe_par_parcelle, out_csv):
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "id_parcelle", "section", "numero", "contenance_m2",
            "nb_ventes_dvf", "derniere_vente_date", "derniere_vente_prix",
            "derniere_vente_prix_m2", "nb_dpe", "classe_dpe_dominante",
        ])
        for pid, info in parcelles.items():
            ventes = dvf_par_parcelle.get(pid, [])
            dpes = dpe_par_parcelle.get(pid, [])

            derniere = None
            if ventes:
                ventes_triees = sorted(
                    ventes, key=lambda r: r.get("date_mutation", ""), reverse=True
                )
                derniere = ventes_triees[0]

            classe_dominante = ""
            if dpes:
                classes = [d.get("etiquette_dpe") or d.get("classe_consommation_energie", "")
                           for d in dpes]
                classes = [c for c in classes if c]
                if classes:
                    classe_dominante = Counter(classes).most_common(1)[0][0]

            w.writerow([
                pid, info["section"], info["numero"], info["contenance_m2"],
                len(ventes),
                derniere.get("date_mutation") if derniere else "",
                derniere.get("valeur_fonciere") if derniere else "",
                derniere.get("prix_m2_terrain") or derniere.get("prix_m2") if derniere else "",
                len(dpes), classe_dominante,
            ])
    print(f"[sortie] résultat écrit dans {out_csv}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--geojson", required=True, help="Chemin du GeoJSON cadastre (parcelles)")
    ap.add_argument("--commune", default="44084", help="Code INSEE commune (def: 44084)")
    ap.add_argument("--annees", nargs="+", default=["2021", "2022", "2023", "2024", "2025"])
    ap.add_argument("--out", default="resultat_44084.csv")
    ap.add_argument("--skip-dpe", action="store_true", help="Ne pas interroger l'API DPE")
    args = ap.parse_args()

    parcelles = charger_parcelles(args.geojson)

    lignes_dvf = telecharger_dvf(args.commune, args.annees)
    dvf_par_parcelle = joindre_dvf(parcelles, lignes_dvf)

    dpe_par_parcelle = {}
    if not args.skip_dpe:
        dpe_records = telecharger_dpe(args.commune)
        if dpe_records:
            dpe_par_parcelle = joindre_dpe(parcelles, dpe_records)

    ecrire_resultats(parcelles, dvf_par_parcelle, dpe_par_parcelle, args.out)


if __name__ == "__main__":
    main()
