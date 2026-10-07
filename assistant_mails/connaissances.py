"""Informations du cabinet utilisées dans les réponses — reprises UNIQUEMENT de infos_cabinet.md.

Le système n'invente aucune information : ce qui n'est pas ici (politique de facturation
des rendez-vous manqués, parking, etc.) est laissé « à compléter » par le secrétariat.
`verifier_coherence()` contrôle que les montants et coordonnées ci-dessous figurent bien
dans infos_cabinet.md (à relancer à chaque mise à jour des tarifs).
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

NOM_CABINET = "Cabinet dentaire Dr Reuter & associés"
ADRESSE = "12, rue de l'Exemple, L-1234 Luxembourg"
TELEPHONE = "+352 20 00 00 00"

HORAIRES = {
    "fr": "du lundi au vendredi, de 8h à 12h et de 13h30 à 18h",
    "de": "Montag bis Freitag, 8–12 Uhr und 13:30–18 Uhr",
    "en": "Monday to Friday, 8:00–12:00 and 13:30–18:00",
    "pt": "de segunda a sexta-feira, das 8h às 12h e das 13h30 às 18h",
    "lb": "Méindes bis Freides, vun 8 bis 12 Auer a vun 13:30 bis 18 Auer",
}

DOCTENA = {
    "fr": "en ligne via Doctena (lien sur notre site)",
    "de": "online über Doctena (Link auf unserer Website)",
    "en": "online via Doctena (link on our website)",
    "pt": "online, através da Doctena (link no nosso site)",
    "lb": "online iwwer Doctena (Link op eisem Site)",
}

# Tarifs indicatifs (honoraires conventionnés CNS) — une ligne par acte et par langue.
TARIFS: dict[str, dict[str, str]] = {
    "consultation": {
        "fr": "Consultation / contrôle : 65 €",
        "de": "Untersuchung / Kontrolle: 65 €",
        "en": "Consultation / check-up: €65",
        "pt": "Consulta / controlo: 65 €",
        "lb": "Konsultatioun / Kontroll: 65 €",
    },
    "detartrage": {
        "fr": "Détartrage : 75 €",
        "de": "Zahnsteinentfernung: 75 €",
        "en": "Scale and polish (tartar removal): €75",
        "pt": "Destartarização: 75 €",
        "lb": "Zännsteen ewechhuelen (Detartrage): 75 €",
    },
    "radio_panoramique": {
        "fr": "Radiographie panoramique : 60 €",
        "de": "Panorama-Röntgenaufnahme: 60 €",
        "en": "Panoramic X-ray: €60",
        "pt": "Radiografia panorâmica: 60 €",
        "lb": "Panorama-Röntgenbild: 60 €",
    },
    "extraction_simple": {
        "fr": "Extraction simple : 80 €",
        "de": "Einfache Zahnentfernung: 80 €",
        "en": "Simple extraction: €80",
        "pt": "Extração simples: 80 €",
        "lb": "Einfach Extraktioun: 80 €",
    },
    "extraction_dent_sagesse": {
        "fr": "Extraction d'une dent de sagesse : 140 €",
        "de": "Entfernung eines Weisheitszahns: 140 €",
        "en": "Wisdom tooth extraction: €140",
        "pt": "Extração de dente do siso: 140 €",
        "lb": "Extraktioun vun engem Weisheetszant: 140 €",
    },
    "traitement_canal": {
        "fr": "Traitement de canal : de 210 € à 310 € selon la dent",
        "de": "Wurzelkanalbehandlung: 210 € bis 310 €, je nach Zahn",
        "en": "Root canal treatment: €210 to €310 depending on the tooth",
        "pt": "Tratamento de canal: de 210 € a 310 €, consoante o dente",
        "lb": "Wuerzelbehandlung: tëscht 210 € an 310 €, jee no Zant",
    },
    "couronne": {
        "fr": "Couronne céramique : sur devis (environ 850 €)",
        "de": "Keramikkrone: nach Kostenvoranschlag (ca. 850 €)",
        "en": "Ceramic crown: on quotation (approx. €850)",
        "pt": "Coroa de cerâmica: mediante orçamento (cerca de 850 €)",
        "lb": "Keramikkroun: op Devis (ongeféier 850 €)",
    },
    "blanchiment": {
        "fr": "Blanchiment : 400 € (non remboursé)",
        "de": "Zahnaufhellung (Bleaching): 400 € (wird nicht erstattet)",
        "en": "Teeth whitening: €400 (not reimbursed)",
        "pt": "Branqueamento: 400 € (não comparticipado)",
        "lb": "Bleaching: 400 € (gëtt net rembourséiert)",
    },
}

# Montants attendus dans infos_cabinet.md pour chaque acte (contrôle de cohérence).
MONTANTS_ATTENDUS = {
    "consultation": ["65"], "detartrage": ["75"], "radio_panoramique": ["60"], "extraction_simple": ["80"],
    "extraction_dent_sagesse": ["140"], "traitement_canal": ["210", "310"], "couronne": ["850"],
    "blanchiment": ["400"],
}

JOURS = {
    "fr": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"],
    "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "pt": ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"],
    "lb": ["Méindeg", "Dënschdeg", "Mëttwoch", "Donneschdeg", "Freideg", "Samschdeg", "Sonndeg"],
}
MOIS = {
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
           "novembre", "décembre"],
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
           "November", "Dezember"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"],
    "pt": ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
           "novembro", "dezembro"],
    "lb": ["Januar", "Februar", "Mäerz", "Abrëll", "Mee", "Juni", "Juli", "August", "September", "Oktober",
           "November", "Dezember"],
}


def formater_date(d: date, langue: str, jour_semaine: bool = True) -> str:
    mois = MOIS[langue][d.month - 1]
    jour = JOURS[langue][d.weekday()]
    if langue == "fr":
        numero = "1er" if d.day == 1 else str(d.day)
        texte = f"{numero} {mois} {d.year}"
        return f"{jour} {texte}" if jour_semaine else texte
    if langue in ("de", "lb"):
        texte = f"{d.day}. {mois} {d.year}"
        return f"{jour}, {texte}" if jour_semaine else texte
    if langue == "pt":
        texte = f"{d.day} de {mois} de {d.year}"
        return f"{jour}, {texte}" if jour_semaine else texte
    texte = f"{d.day} {mois} {d.year}"
    return f"{jour} {texte}" if jour_semaine else texte


def formater_heure(h: datetime, langue: str) -> str:
    if langue in ("fr", "pt"):
        return f"{h.hour}h{h.minute:02d}" if h.minute else f"{h.hour}h"
    if langue == "de":
        return f"{h.hour}:{h.minute:02d} Uhr"
    if langue == "lb":
        return f"{h.hour}:{h.minute:02d} Auer"
    return f"{h.hour}:{h.minute:02d}"


def verifier_coherence(chemin_infos: Path) -> list[str]:
    """Liste les écarts entre ce module et infos_cabinet.md (liste vide = cohérent)."""
    texte = chemin_infos.read_text(encoding="utf-8")
    ecarts = []
    for valeur, libelle in ((TELEPHONE, "téléphone"), (ADRESSE, "adresse")):
        if valeur not in texte:
            ecarts.append(f"{libelle} « {valeur} » absent de {chemin_infos.name}")
    montants = set(re.findall(r"(\d+)\s?€", texte))
    for acte, attendus in MONTANTS_ATTENDUS.items():
        for m in attendus:
            if m not in montants:
                ecarts.append(f"montant {m} € ({acte}) absent de {chemin_infos.name}")
        for langue, ligne in TARIFS[acte].items():
            if not all(m in ligne for m in attendus):
                ecarts.append(f"ligne de tarif {acte}/{langue} incohérente : {ligne}")
    return ecarts
