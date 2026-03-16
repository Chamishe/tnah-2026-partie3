import json
import geojson
from pathlib import Path
# Classe encapsulant l'accès au géocodeur Nominatim d'OpenStreetMap
from geopy.geocoders import Nominatim
# Le résultat d'un géocodage est un objet de type Location
from geopy.location import Location
# Un rate limiter permet de limiter le nombre de requêtes envoyées par secondes
# En effet, Nominatim **bannit** les usagers qui "spamment" le géocodeur
from geopy.extra.rate_limiter import RateLimiter


# --- Variables globales

DIR = Path(__file__).parent / "photographies_avec_themes"
json_files = list(DIR.glob("*.json"))

# --- Initialisation du géocodeur
geocoder = Nominatim(user_agent="tnah-équipe-2")
limited_geocoder = RateLimiter(geocoder.geocode, min_delay_seconds=5)


# --- Fonctions
def read_json_file(file_path: Path) -> dict:
    """Lit un fichier JSON et retourne son contenu sous forme de dictionnaire."""
    with open(file_path, "r") as file:
        data = json.load(file)
    return data


def build_geocoding_query(data: dict, level: str) -> str:
    """Construit une requête de géocodage en fonction du niveau de précision demandé."""

# fix du prof avant correction des .json

#   if data.get("entites_geographiques"): # voir s'il y a bien "entités géographiques"
#        data = data.get("entites_geographiques") # si c'est le cas, le récupérer
#        if isinstance(data, list): # vérifier si c'est une liste
#            data = dict(zip( # si c'est une liste, on crée un dictionnaire en associant la liste a et b
#                ["toponyme","adresse", "voie", "ville", "pays"], # liste a, les niveaux
#                [item.get("entite") if isinstance(item, dict) else item for item in data] # liste b, les items contenus dans le json
#            ))

    values = {
            "pays": data.get("pays") or "France",
            "ville": data.get("ville") or "Paris",
            "voie": data.get("voie"),
            "adresse": data.get("adresse"),
            "toponyme": data.get("toponyme") # rajouts pour corriger les errances de Mistral
            or data.get("édifice")
            or data.get("place")
            or data.get("établissement")
            or ""
        }

    if level not in values:
        return ""

    if level == "pays":
        query = [values["pays"]]
    elif level == "ville":
        query = [values["ville"], values["pays"]]
    elif level == "voie":
        query = [values["voie"], values["ville"], values["pays"]]
    elif level == "adresse":
        query = [values["adresse"], values["ville"], values["pays"]]
    elif level == "toponyme":
        query = [values["toponyme"], values["adresse"], values["ville"], values["pays"]]
    else:
        return ""

    # On filtre les éléments vides et on joint avec des virgules
    query = ", ".join(part for part in query if part)

    print(f"[{level}] 🔍 Query : {query}")
    return query

    #query = "..."

    #print(f"[{level}] 🔍 Query : {query}")
    #return query


def geocode(query: str):
    """Exécute le géocodage de la requête et retourne le résultat."""
    print(f"📍 Geocoding : {query}")
    location = limited_geocoder(query)
    return location

def create_geojson_feature(location: Location, properties: dict) -> geojson.Feature:
    point = geojson.Point((location.longitude, location.latitude))
    feature = geojson.Feature(geometry=point, properties=properties)
    return feature

def save_geocoding(feature: geojson.Feature, input_json_file: Path) -> None:
    output_file = input_json_file.with_suffix(".geojson")
    with open(output_file, "w") as file:
        geojson.dump(feature, file, indent=2, ensure_ascii=False)
    print(f"📁 Saved: {output_file}")

# -- Traitement principal


def main():

    # PSEUDO-CODE :
    # Pour chaque fichier JSON dans le dossier `photographies_avec_themes/`:
    #   Afficher "📁 Processing: {json_file.name}"
    #   Pour chaque niveau hiérarchique dans l'ordre "toponyme", "adresse", "voie", "ville", "pays"
    #      Crée la requête de géocodage adéquate avec `build_geocoding_query(data: dict, level: str)`
    #      Si la requête n'est pas vide:
    #         Exécute le géocodage de la requête avec `geocode(query: str)` et
    #         stocke le résultat dans une variable `location`
    #         Si `location` n'est pas None:
    #             Afficher "[{level}] ✅ : {location}"
    #             Passer au fichier suivant (ℹ️  utiliser le mot clé Python `break`)
    #         Sinon:
    #             Afficher "[{level}] ❌"

    features = [] # liste originale

    for json_file in json_files: # première boucle récupérant les fichiers json un par un
        print(f"📁 Processing: {json_file.name}") # print indiquant sur quel fichier on opère
        data = read_json_file(json_file) # appel de la fonction 'read_json_file' pour lire le contenu du fichier
        levels = ["toponyme","adresse","voie","ville","pays"] # liste 'levels' indiquant la hiérarchie des requêtes
        for level in levels: # deuxième boucle permettant de séquencer les requêtes par niveau
            query: str = build_geocoding_query(data, level) # appel de 'build_geocoding_query' pour créer la requête
            if query is not None : # s'il y a un résultat, exécution du code ci-dessous
                location = geocode(query)
                if location is not None:
                    print(f"[{level}] ✅ : {location}") # indique le succès
                    properties = { # création d'un dictionnaire à partir des informations de la boucle
                        "extraction": data,
                        "query": query,
                        "level": level,
                        "response": location.raw,
                        "photo_id": json_file.stem,
                    }
                    feature = create_geojson_feature(location, properties) # création de la variable feature
                    save_geocoding(feature, json_file) # création du .geojson
                    features.append(feature) # ajout de la feature à la liste features
                    break # arrête la boucle
                else : # s'il n'y a pas de résultats, indique l'échec
                    print(f"[{level}] ❌")

    # le code ci-dessous crée un fichier débug additionnant toutes les features

    debug_geojson_file = Path("debug_geocoding_results.geojson")
    feature_collection = geojson.FeatureCollection(features)
    with open(debug_geojson_file, "w") as file:
        geojson.dump(feature_collection, file, indent=2, ensure_ascii=False)
    print(f"📁 Saved on disk: {debug_geojson_file}")

if __name__ == "__main__":
    main()
