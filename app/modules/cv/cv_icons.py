"""Icônes Lucide autorisées pour compétences et centres d'intérêt."""

from __future__ import annotations

import re
from typing import Optional

CV_ICON_NAMES = {
    "code-2",
    "terminal",
    "database",
    "globe",
    "smartphone",
    "cpu",
    "cloud",
    "lock",
    "git-branch",
    "server",
    "wifi",
    "pen-tool",
    "palette",
    "camera",
    "video",
    "music",
    "megaphone",
    "line-chart",
    "calculator",
    "file-spreadsheet",
    "presentation",
    "wrench",
    "settings",
    "users",
    "heart-handshake",
    "headset",
    "scale",
    "stethoscope",
    "graduation-cap",
    "book-open",
    "languages",
    "car",
    "plane",
    "truck",
    "chef-hat",
    "utensils",
    "dumbbell",
    "leaf",
    "building-2",
    "landmark",
    "mic",
    "shopping-bag",
    "lightbulb",
    "sparkles",
    "briefcase",
    "messages-square",
    "bot",
    "brain",
    "flask-conical",
    "hammer",
    "gamepad-2",
    "heart",
    "coffee",
    "bike",
    "film",
    "tree-pine",
    "baby",
}

ICON_LIST = ", ".join(sorted(CV_ICON_NAMES))

_KEYWORDS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"html|css|javascript|typescript|\bjs\b|\bts\b|react|angular|vue|next|node|python|java|php|ruby|swift|kotlin|golang|rust|flutter|django|laravel|symfony|wordpress", re.I), "code-2"),
    (re.compile(r"terminal|bash|shell|linux|unix|powershell", re.I), "terminal"),
    (re.compile(r"sql|mysql|postgres|mongo|oracle|redis|firebase|base de donn", re.I), "database"),
    (re.compile(r"seo|web|internet|www|navigat", re.I), "globe"),
    (re.compile(r"android|ios|mobile|smartphone", re.I), "smartphone"),
    (re.compile(r"\bia\b|\bai\b|machine learning|deep learning|data science|llm|chatgpt", re.I), "brain"),
    (re.compile(r"robot|automat|rpa|\bbot\b", re.I), "bot"),
    (re.compile(r"cloud|aws|azure|gcp|devops|kubernetes|docker", re.I), "cloud"),
    (re.compile(r"s[eé]curit|cyber|owasp|pentest|rgpd", re.I), "lock"),
    (re.compile(r"git|github|gitlab", re.I), "git-branch"),
    (re.compile(r"r[eé]seau|wifi|cisco|tcp", re.I), "wifi"),
    (re.compile(r"serveur|server|admin sys|sysadmin", re.I), "server"),
    (re.compile(r"figma|photoshop|illustrator|\bui\b|\bux\b|graphis|design", re.I), "palette"),
    (re.compile(r"photo", re.I), "camera"),
    (re.compile(r"vid[eé]o|youtube|montage", re.I), "video"),
    (re.compile(r"musique|piano|guitare|chant", re.I), "music"),
    (re.compile(r"market|publicit|community|r[eé]seaux sociaux", re.I), "megaphone"),
    (re.compile(r"analys|statisti|kpi|power bi", re.I), "line-chart"),
    (re.compile(r"excel|spreadsheet|tableur", re.I), "file-spreadsheet"),
    (re.compile(r"compta|finance|budget", re.I), "calculator"),
    (re.compile(r"powerpoint|pitch|pr[eé]sent", re.I), "presentation"),
    (re.compile(r"mainten|r[eé]par|bricol", re.I), "wrench"),
    (re.compile(r"manag|encadr|leadership|gestion d.?[eé]quipe", re.I), "users"),
    (re.compile(r"\brh\b|recrut|ressources humaines", re.I), "heart-handshake"),
    (re.compile(r"support|helpdesk|\bsav\b|relation client", re.I), "headset"),
    (re.compile(r"droit|jurid|avocat|legal", re.I), "scale"),
    (re.compile(r"sant[eé]|m[eé]decin|infirm|soin|pharmac", re.I), "stethoscope"),
    (re.compile(r"enseign|p[eé]dago|professeur", re.I), "graduation-cap"),
    (re.compile(r"lecture|livre|r[eé]daction", re.I), "book-open"),
    (re.compile(r"anglais|espagnol|allemand|italien|arabe|chinois|langue", re.I), "languages"),
    (re.compile(r"permis|voiture|conduite", re.I), "car"),
    (re.compile(r"voyage|avion|touris", re.I), "plane"),
    (re.compile(r"logisti|transport|camion", re.I), "truck"),
    (re.compile(r"cuisin|chef|p[aâ]tiss", re.I), "chef-hat"),
    (re.compile(r"sport|foot|basket|tennis|muscu|yoga|natation", re.I), "dumbbell"),
    (re.compile(r"jardin|nature|ecolo|environnement", re.I), "leaf"),
    (re.compile(r"vente|commer|n[eé]goce", re.I), "shopping-bag"),
    (re.compile(r"projet|scrum|agile|jira", re.I), "briefcase"),
    (re.compile(r"communicat", re.I), "messages-square"),
    (re.compile(r"jeu|gaming|esport", re.I), "gamepad-2"),
    (re.compile(r"b[eé]n[eé]volat|associatif", re.I), "heart"),
    (re.compile(r"cin[eé]ma|film", re.I), "film"),
    (re.compile(r"v[eé]lo|cyclis", re.I), "bike"),
]


def normalize_icon(value: object) -> Optional[str]:
    if not isinstance(value, str):
        return None
    icon = value.strip().lower().replace("_", "-")
    return icon if icon in CV_ICON_NAMES else None


def resolve_icon(name: str, stored: object = None) -> Optional[str]:
    chosen = normalize_icon(stored)
    if chosen:
        return chosen
    haystack = (name or "").lower()
    for pattern, icon in _KEYWORDS:
        if pattern.search(haystack):
            return icon
    return None
