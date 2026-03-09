import json
from pathlib import Path

# --- Variables globales

DIR = Path(__file__).parent / "photographies_avec_themes"

# --- Initialisation du géocodeur
geocoder = ...
limited_geocoder = ...


# --- Fonctions
def read_json_file(file_path: Path) -> dict:
    """Lit un fichier JSON et retourne son contenu sous forme de dictionnaire."""
    with open(file_path, "r") as file:
        data = json.load(file)
    return data


def build_geocoding_query(data: dict, level: str) -> str:
    """Construit une requête de géocodage en fonction du niveau de précision demandé."""

    query = "..."  # Placeholder

    print(f"[{level}] 🔍 Query : {query}")
    return query


def geocode(query: str):
    """Exécute le géocodage de la requête et retourne le résultat."""
    print(f"📍 Geocoding : {query}")
    return None  # Placeholder


# -- Traitement principal


def main():
    json_files = list(DIR.glob("*.json"))
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


if __name__ == "__main__":
    main()
