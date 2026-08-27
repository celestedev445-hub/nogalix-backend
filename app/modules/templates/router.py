from fastapi import APIRouter

router = APIRouter(prefix="/templates", tags=["templates"])

# Templates de rendu vivent dans le frontend pour la réactivité.
# Ce endpoint optionnel expose seulement des métadonnées (ids) si besoin futur.
CATALOG = [
    {"id": "atlas", "name": "Atlas", "category": "moderne", "premium": False},
    {"id": "ndame", "name": "Ndame", "category": "moderne", "premium": False},
    {"id": "simple-colonne", "name": "Simple colonne", "category": "minimaliste", "premium": False},
    {"id": "ndiaye", "name": "Ndiaye", "category": "classique", "premium": False},
    {"id": "elongou-editorial", "name": "Elongou Editorial", "category": "creatif", "premium": True},
    {"id": "deux-colonnes", "name": "Deux colonnes", "category": "moderne", "premium": False},
    {"id": "bongue", "name": "Bongue", "category": "moderne", "premium": False},
    {"id": "bongue-sidebar", "name": "Bongue Sidebar", "category": "moderne", "premium": True},
    {"id": "ngo-yellow", "name": "Ngo Yellow", "category": "creatif", "premium": False},
    {"id": "mbarga", "name": "Mbarga", "category": "moderne", "premium": False},
    {"id": "photo-haut", "name": "Photo haut", "category": "creatif", "premium": False},
    {"id": "elongou-typo", "name": "Elongou Typo", "category": "creatif", "premium": True},
    {"id": "kouame-photo", "name": "Kouame Photo", "category": "moderne", "premium": False},
    {"id": "amina-pastel", "name": "Amina Pastel", "category": "creatif", "premium": False},
    {"id": "classique", "name": "Classique", "category": "classique", "premium": False},
    {"id": "mvondo", "name": "Mvondo", "category": "moderne", "premium": False},
    {"id": "enzo-dark", "name": "Enzo Dark", "category": "premium", "premium": True},
    {"id": "amina-minimal", "name": "Amina Minimal", "category": "minimaliste", "premium": False},
    {"id": "voundi-dark", "name": "Voundi Dark", "category": "premium", "premium": True},
    {"id": "voundi-editorial", "name": "Voundi Editorial", "category": "creatif", "premium": True},
    {"id": "ndjock", "name": "Ndjock", "category": "moderne", "premium": False},
    {"id": "lateral", "name": "Latéral", "category": "moderne", "premium": False},
    {"id": "essomba", "name": "Essomba", "category": "moderne", "premium": False},
    {"id": "ngo-clean", "name": "Ngo Clean", "category": "minimaliste", "premium": False},
]


@router.get("")
def index():
    return {"data": CATALOG}
