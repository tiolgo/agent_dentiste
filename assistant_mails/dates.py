"""Repérage des dates dans un e-mail (5 langues), sans LLM.

Le résultat reste « flou » (jour/mois sans année, plage « la semaine dernière ») :
c'est la confrontation avec le dossier (rendez-vous, factures) qui tranche.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from .modeles import DateFloue
from .normalisation import replier

MOIS: dict[str, int] = {
    # français
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
    # allemand / luxembourgeois
    "januar": 1, "janner": 1, "februar": 2, "marz": 3, "maerz": 3, "april": 4, "abrell": 4, "mee": 5,
    "juni": 6, "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11, "dezember": 12,
    # anglais
    "january": 1, "february": 2, "march": 3, "may": 5, "june": 6, "july": 7, "october": 10,
    "december": 12,
    # portugais
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
    "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
# Abréviations : acceptées seulement collées à un numéro de jour.
ABREVIATIONS: dict[str, int] = {
    "janv": 1, "jan": 1, "fevr": 2, "fev": 2, "feb": 2, "avr": 4, "apr": 4, "juil": 7, "jul": 7, "jun": 6,
    "aug": 8, "sept": 9, "sep": 9, "oct": 10, "okt": 10, "nov": 11, "dec": 12, "dez": 12,
}

_NOMS_MOIS = "|".join(sorted(MOIS, key=len, reverse=True))
_NOMS_ABR = "|".join(sorted(ABREVIATIONS, key=len, reverse=True))

_RE_JOUR_MOIS = re.compile(
    rf"\b(\d{{1,2}})(?:er|st|nd|rd|th|\.)?\s+(?:de\s+)?({_NOMS_MOIS}|(?:{_NOMS_ABR})\.?)(?=\W|$)(?:\s+(?:de\s+)?(\d{{4}}))?")
_RE_MOIS_JOUR = re.compile(rf"\b({_NOMS_MOIS})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?:,?\s+(\d{{4}}))?")
_RE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_RE_NUMERIQUE = re.compile(r"(?<![\d/.-])(\d{1,2})[./](\d{1,2})(?:[./](\d{2,4}))?(?![\d/])")
_RE_MOIS_SEUL = re.compile(rf"\b({_NOMS_MOIS})\b(?:\s+(\d{{4}}))?")

_ANNEE_PRECEDENTE = re.compile(
    r"\b(l'an (dernier|passe)|l'annee (derniere|passee)|last year|letzte[ns]? jahr\w*|vorig\w* jahr\w*|"
    r"vergangene[ns]? jahr\w*|ano passado|no ano anterior|d'lescht joer|vum leschte joer|leschte joer)\b")
_ANNEE_EXPLICITE = re.compile(r"\b(?:de|en|in|for|of|von|vun|em|do ano|annee|year|jahr|ano|joer|pour|fur|fir)\s+(20\d\d)\b")
_ANNEE_COURANTE = re.compile(r"\b(cette annee|this year|dieses jahr\w*|este ano|dest joer|des joer)\b")
_SEMAINE_DERNIERE = re.compile(
    r"\b(la semaine (derniere|passee)|semaine derniere|last week|letzte woche|vergangene woche|"
    r"vorige woche|semana passada|ultima semana|lescht woch|leschter woch)\b")
_CETTE_SEMAINE = re.compile(r"\b(cette semaine|this week|diese woche|esta semana|des woch|dest woch)\b")
_HIER = re.compile(r"\b(hier|yesterday|gestern|ontem|gestern|geschter)\b")
_AUJOURDHUI = re.compile(r"\b(aujourd'hui|ce matin|cet apres-midi|today|this morning|heute|hoje|haut de moien)\b")
_DEMAIN = re.compile(r"\b(demain|tomorrow|amanha|muer)\b|(?<!guten )\bmorgen\b")
_APRES_DEMAIN = re.compile(r"\b(apres-demain|apres demain|day after tomorrow|ubermorgen|depois de amanha|iwwermuer)\b")
_HEURE = re.compile(r"\b(\d{1,2})\s?(?:h|:|uhr|heures?|hours?|auer)\s?(\d{2})?\b(?!\s?%)")


@dataclass
class Reperes:
    dates: list[DateFloue] = field(default_factory=list)
    mois_seuls: list[DateFloue] = field(default_factory=list)   # « de septembre », « vum August »
    plage: tuple[date, date] | None = None
    annee_indice: int = 0
    heure: str = ""


def _ajouter(liste: list[DateFloue], d: DateFloue) -> None:
    if d not in liste:
        liste.append(d)


def _annee(texte_annee: str | None) -> int | None:
    if not texte_annee:
        return None
    a = int(texte_annee)
    if a < 100:
        a += 2000
    return a if 2000 <= a <= 2100 else None


def reperer_dates(texte: str, ref: date) -> Reperes:
    plie = replier(texte)
    r = Reperes()

    for m in _RE_ISO.finditer(plie):
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            _ajouter(r.dates, DateFloue(d.day, d.month, d.year))
        except ValueError:
            pass
    for m in _RE_JOUR_MOIS.finditer(plie):
        nom = m.group(2).rstrip(".")
        mois = MOIS.get(nom) or ABREVIATIONS.get(nom)
        jour = int(m.group(1))
        if mois and 1 <= jour <= 31:
            _ajouter(r.dates, DateFloue(jour, mois, _annee(m.group(3))))
    for m in _RE_MOIS_JOUR.finditer(plie):
        jour = int(m.group(2))
        if 1 <= jour <= 31:
            _ajouter(r.dates, DateFloue(jour, MOIS[m.group(1)], _annee(m.group(3))))
    for m in _RE_NUMERIQUE.finditer(plie):
        jour, mois = int(m.group(1)), int(m.group(2))
        contexte = plie[max(0, m.start() - 3):m.start()]
        if 1 <= jour <= 31 and 1 <= mois <= 12 and "h" not in contexte:
            _ajouter(r.dates, DateFloue(jour, mois, _annee(m.group(3))))
    jours_mois = {(d.jour, d.mois) for d in r.dates}
    for m in _RE_MOIS_SEUL.finditer(plie):
        mois = MOIS[m.group(1)]
        if m.group(1) in {"mai", "may", "mee", "marco", "march", "august"} and not m.group(2):
            # mots ambigus (« may » anglais, « mee »...) : seulement après une préposition de date
            avant = plie[max(0, m.start() - 12):m.start()]
            if not re.search(r"\b(de|du|d'|en|in|im|vum|vun|vu|from|of|em|since|depuis|seit|fur|for|pour|para|fir|von|vom)\s*$", avant):
                continue
        if not any(mo == mois for _, mo in jours_mois):
            _ajouter(r.mois_seuls, DateFloue(None, mois, _annee(m.group(2))))

    explicite = _ANNEE_EXPLICITE.search(plie)
    if explicite and 2000 <= int(explicite.group(1)) <= ref.year + 1:
        r.annee_indice = int(explicite.group(1))
    elif _ANNEE_PRECEDENTE.search(plie):
        r.annee_indice = ref.year - 1
    elif _ANNEE_COURANTE.search(plie):
        r.annee_indice = ref.year

    lundi = ref - timedelta(days=ref.weekday())
    if _SEMAINE_DERNIERE.search(plie):
        r.plage = (lundi - timedelta(days=7), lundi - timedelta(days=1))
    elif _CETTE_SEMAINE.search(plie):
        r.plage = (lundi, lundi + timedelta(days=6))
    for motif, ecart in ((_APRES_DEMAIN, 2), (_HIER, -1), (_AUJOURDHUI, 0), (_DEMAIN, 1)):
        if motif.search(plie):
            d = ref + timedelta(days=ecart)
            _ajouter(r.dates, DateFloue(d.day, d.month, d.year))
            break

    h = _HEURE.search(plie)
    if h and 0 <= int(h.group(1)) <= 23:
        r.heure = f"{int(h.group(1)):02d}:{h.group(2) or '00'}"
    return r
