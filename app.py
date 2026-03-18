# --- IMPORTS

import json
from pathlib import Path

import streamlit as st
import folium # Libraire Python qui enveloppe Leaflet. 
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


@st.cache_data # Décorateur qui fait de la mémorisation. Stocke les exécutions de la fonction pour que quand il recharge la page, il récuppère les informations stockées, si elles existent et évite d'avoir un traitement trop lourd en chargeant tout le script à chaque fois.
def load_all_photos() -> dict[str, dict]:
    """
    Fusionne les informations que contiennent le fichier turtle avec les information du GeoJson dans un objet Python (dictionnaire). 
    Chaque photo a son objet Python
    """
    turtle_files = list(DIR.glob("*.ttl"))

    all_photos_metadata = {} # Initialise un dictionnaire vide
    for ttl_file in turtle_files:
        g = Graph().parse(ttl_file, format="turtle") # Créer un graphe par fichier turtle

        uri: Node | None = g.value(predicate=RDF.type, object=FRBR.Manifestation) # Créer une URI à partir du fichier du graph

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
        } # Créer un dictionnaire de photo à partir des informations graph et de l'URI

        geojson_path = DIR / f"{ttl_file.stem}.geojson" # Charge fichier GeoJson qui correspond à l'ARK

        with open(geojson_path, "r", encoding="utf-8") as f: # Lit le geoJson
            location = geojson.loads(f.read()) # Charge le fichier geoJson
            photo["location"] = location # Ajouter location au dictionnaire. Donc ajouter les données du geoJson

        all_photos_metadata[str(uri)] = photo # Associe l'URI au dictionnaire photo
    return all_photos_metadata # Réccupère le résultat de tout ce qui vient d'être, toutes les métadonnées et affiche le résultat. 


# ---
# --- FONCTIONS DE TRANSFORMATION DE DONNÉES
# ---

def build_folium_feature(location: dict, photo_title: str, photo_uri: str): 
    """Crée une feature Folium à partir du geojson de localisation d'une photo."""
    folium_feature = folium.GeoJson(location, tooltip=photo_title) # Créer un objet Folium à partir d'un GeoJson, en créer un feature. Tooltip : ce qui s'affichera quand on passera la souris. Ici le titre de la photo. 
    folium_feature.data["properties"]["uri"] = photo_uri
    return folium_feature

def add_locations_to_map(m: folium.Map, photos_metadata: dict[str, dict]):
    """Ajoute les localisations de toutes les photos sur la carte."""
    for photo in photos_metadata.values(): # Boucle sur toutes les valeurs du dictionnaire. 
        feature = build_folium_feature(photo["location"], photo["titre"], photo["uri"]) # Construit feature folium sur les données du dictionnaire : la location, titre et URI. 
        feature.add_to(m) # Ajoute à la carte avec la méthode add_to avec ne paramètre la carte. 

def build_iiif_url(gallica_link):
   """
   Transforme un lien Gallica en manifeste IIIF.
    
    Paramètre : Lien Gallica
   """
   parts = gallica_link.split("ark:/12148/") # split découpe le lien en utilisant comme séparateur : ark:/12148/. 
   ark_id = parts[1] # Récuppère l'identifiant qui se trouve dans la deuxième partie de la liste crée précédemment. 
   return (
       f"https://openapi.bnf.fr/iiif/presentation/v3/ark:/12148/{ark_id}/manifest.json" # Réinsère le résulat dans ce template.
   )

# ---
# --- PREMIERS PAS
# ---

DIR = Path("photographies_avec_themes")

photos_metadata = load_all_photos()

# print(json.dumps(photos_metadata, indent=2, ensure_ascii=False)) # Affiche le dictionnaire 


# ---
# --- BASES DE L'INTERFACE
# ---

def afficher_infobox(p):
   """Affiche les métadonnées dans un menu déroulant."""
   with st.expander("Voir les métadonnées détaillées"):
       st.write(f"**Titre :** {p['titre']}")
       st.write(f"**Date :** {p['date']}")
       st.write(f"**Description :** {p['description']}")
       if p["catalogue"]:
           st.write(f"**Catalogue BnF :** [{p['catalogue']}]({p['catalogue']})")
       for s in p["sujets"]:
           st.write(f"**Sujet :** [{s['label']}]({s['uri']})")
       for link in p["gallica_urls"]:
           st.write(f"**Numérisation :** [{link}]({link})")

st.set_page_config(layout="wide") # Pour que la page prenne toute la largeur de ma page. 

default_uri = "http://data.bnf.fr/ark:/12148/cb40265861p#about" # ⚠️ URI de la MANIFESTATION : forme : "http://data.bnf.fr/ark:/12148/...#about"
default_photo = photos_metadata.get(default_uri) #Réccupère dans mon dictionnaire crée dans "load_all_photos()" le dictionnaire de cette photo précise. 

if "selected_uri" not in st.session_state:
    st.session_state.selected_uri = default_uri
current_photo = photos_metadata[st.session_state.selected_uri] # Sinon on met la photo par défaut. Comportement par défaut. 


st.title(f"{current_photo['titre']} – {current_photo['date']}") # Créer un titre grâce à Streamlit. Ce dernier fait tout tout seul. 
afficher_infobox(current_photo)

map_container, iiif_container = st.columns([1, 1]) # Déclare les colonnes. st.columns renvoie autant de colonnes que demandées. On les stocke dnas map_container et iif_container.
# Gestionnaire de contexte : Bloc de code dnas lequel, avec with on fait un appel de fonction avec un objet qui gère des ressources, cette ressource est accessible tant que l'on reste dans le bloc.
# Streamlit propose cela pour gérer les composants. A chaque fois que l'on appelle une méthode st, elle s'applique à tout. Toutes les instructions Streamlit st.... déclarées à l'intérieur de ce contexte concerneront `map_container`, sans avoir besoin de le préciser à chaque appel !   
with map_container:
    # Une carte Folium centrée sur Paris. Coordonnées du centre. zoom_start = Zoom de départ. 
    interactive_map = folium.Map(location=[48.8566, 2.3522], zoom_start=10)
    add_locations_to_map(interactive_map, photos_metadata) # Ajoute toutes les photos à la carte. 
    # ... et on la transforme en composant Streamlit avec le plugin `st folium`. use_container_width : la carte prend la totalité de la taille de container parce qu'il est sur True. st folium créer le composant folium et un objet qui donne accès à toutes interactions crées sur la carte. 
    map_data = st_folium(interactive_map, use_container_width=True, height=800) # Ajouter comme composant de streamlit.

    selected_feature = map_data["last_active_drawing"] # Renvoie une feature folium que l'on va stocker. En l'occurence la dernière cliquée. 
    if selected_feature: # Si on a sélectionné une feature, si elle n'est pas None. 
        selected_uri = selected_feature["properties"]["uri"] #Réccupère l'URI
        if selected_uri != st.session_state.selected_uri: # Si on a pas déjà l'image en mémoire.  
            print(f"Photo sélectionnée : {selected_uri}")
            st.session_state.selected_uri = selected_uri # Stocke dans la mémoire de l'application. 
            st.rerun() #Réexécute tous le fichier afin de retourner sur le "if" qui se demande si une photo est sélectionnée. 

    with iiif_container:
        # Variable qui créer l'url iif grâce à la fonction. On utilise le "Gallica_urls du dictionnaire "photo" et la première numérisation "[O]". 
        url_iiif = build_iiif_url(current_photo["gallica_urls"][0])
        # Fonction qui crée une instance de tify et en fait un composant streamlit
        iiif_viewer( 
            viewer="tify",
            manifest=url_iiif,
            height=800,
        )