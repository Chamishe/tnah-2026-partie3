# --- IMPORTS

import json
from pathlib import Path

import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_iiif_viewer import iiif_viewer
import geojson

from rdflib import Graph, Namespace, Node

# Rdflib fournit des Namespaces pré-définis pour les vocabulaires courants.
from rdflib.namespace import DCTERMS, RDF, SKOS, RDFS

# La BnF utilise des vocabulaires spécifiques, on les définit ici.
# FRBR pour décrire les œuvres, expressions, manifestations, etc.
# RDA pour les relations entre les entités (ex. reproduction électronique).
FRBR = Namespace("http://rdvocab.info/uri/schema/FRBRentitiesRDA/")
RDA = Namespace("http://rdvocab.info/RDARelationshipsWEMI/")

# ---
# --- FONCTIONS DE CHARGEMENT DES MÉTADONNÉES
# ---


def get_triple_value(graph: Graph, subject: Node, predicate: Node) -> str:
    """Dans un graphe RDF, étant donné un triplet
    [subject] -- [predicate]--> [value],
    retourne la valeur associée au prédicat pour le sujet,
    ou une chaîne vide si aucune valeur n'est trouvée.
    """
    val = graph.value(subject, predicate)
    return str(val) if val else ""


def get_rameau_subjects(graph: Graph, manifestation: Node) -> list[dict[str, str]]:
    """Extrait la liste des sujets Rameau associés à une manifestation."""
    sujets = []
    for s in graph.objects(manifestation, DCTERMS.subject):
        label = graph.value(s, SKOS.prefLabel)
        sujets.append({"label": str(label), "uri": str(s)})
    return sujets


def get_gallica_urls(graph: Graph, manifestation: Node) -> list[str]:
    """Extrait les liens Gallica associés à une manifestation"""
    reproductions = []
    for link in graph.objects(manifestation, RDA.electronicReproduction):
        reproductions.append(str(link))
    return reproductions


@st.cache_data
def load_all_photos() -> dict[str, dict]:
    """..."""
    turtle_files = list(DIR.glob("*.ttl"))

    all_photos_metadata = {}
    for ttl_file in turtle_files:
        g = Graph().parse(ttl_file, format="turtle")

        uri: Node | None = g.value(predicate=RDF.type, object=FRBR.Manifestation)

        if uri is None:
            print(f"⚠️ Aucune manifestation trouvée dans {ttl_file}")
            continue

        photo = {
            "uri": str(uri),
            "titre": get_triple_value(g, uri, DCTERMS.title),
            "date": get_triple_value(g, uri, DCTERMS.date),
            "description": get_triple_value(g, uri, DCTERMS.description),
            "catalogue": get_triple_value(g, uri, RDFS.seeAlso),
            "sujets": get_rameau_subjects(g, uri),
            "gallica_urls": get_gallica_urls(g, uri),
        }

        geojson_path = DIR / f"{ttl_file.stem}.geojson"

        with open(geojson_path, "r", encoding="utf-8") as f:
            location = geojson.loads(f.read())
            photo["location"] = location

        all_photos_metadata[str(uri)] = photo
    return all_photos_metadata


# ---
# --- FONCTIONS DE TRANSFORMATION DE DONNÉES
# ---

# ---
# --- PREMIERS PAS
# ---

DIR = Path("photographies_avec_themes")

photos_metadata = load_all_photos()

print(json.dumps(photos_metadata, indent=2, ensure_ascii=False))


# ---
# --- BASES DE L'INTERFACE
# ---
