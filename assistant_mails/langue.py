"""Détection de la langue par marqueurs lexicaux (sans LLM).

Première lecture et contre-vérification du LLM, notamment pour distinguer le
luxembourgeois de l'allemand, que les modèles confondent volontiers.
Poids : 0,5-1 = mot fréquent mais partagé entre langues, 3 = mot très caractéristique.
"""

from __future__ import annotations

import re

from .modeles import LANGUES

_MARQUEURS: dict[str, dict[str, float]] = {
    "fr": {
        "le": 1, "la": 1, "les": 1, "des": 1, "du": 1, "une": 1, "et": 1, "est": 1, "je": 2, "vous": 2,
        "nous": 1.5, "pour": 1.5, "pas": 1.5, "ne": 1.5, "mon": 1.5, "ma": 1, "mes": 1, "votre": 2,
        "vos": 2, "qui": 1, "avec": 1.5, "sur": 1, "dans": 1.5, "au": 1, "aux": 1.5, "ce": 1,
        "cette": 1.5, "il": 1, "elle": 1.5, "suis": 2, "avez": 2, "ai": 1, "sont": 1.5, "mais": 1.5,
        "très": 1.5, "plus": 1, "bien": 1, "aussi": 1.5, "depuis": 2, "encore": 2, "merci": 0.5,
        "bonjour": 3, "bonsoir": 3, "madame": 2, "monsieur": 2, "cordialement": 3, "salutations": 2,
        "facture": 2, "pourriez": 3, "pouvez": 3, "voudrais": 3, "souhaite": 2, "c'est": 2,
        "est-ce": 2, "n'est": 2, "s'il": 2, "plaît": 2, "semaine": 2, "dernière": 2, "dernier": 2,
        "aujourd'hui": 3, "demain": 2, "hier": 2, "dent": 2, "dents": 2, "douleur": 3, "renvoyer": 3,
        "envoyer": 2, "prix": 2, "combien": 3, "coûte": 3, "remboursé": 2, "besoin": 2, "mari": 2,
        "fille": 2, "fils": 2, "enfant": 2, "après": 1.5, "chez": 2, "moi": 1.5, "été": 1.5,
        "être": 1.5, "avoir": 1.5, "faire": 1.5, "peux": 2, "veux": 2, "j'ai": 2, "rendez": 1,
    },
    "de": {
        "der": 1, "die": 1, "das": 1, "und": 1.5, "ist": 1.5, "ich": 2, "sie": 1, "nicht": 2, "ein": 1,
        "eine": 1.5, "einen": 2, "mit": 1.5, "für": 2, "auf": 1.5, "bitte": 2, "danke": 2, "guten": 3,
        "tag": 1, "termin": 2, "rechnung": 1, "können": 3, "könnten": 3, "kann": 0.5, "mein": 2,
        "meine": 2, "meinen": 3, "meiner": 3, "meines": 3, "ihr": 1, "ihre": 2, "ihren": 3, "ihnen": 3,
        "wir": 2, "haben": 2, "habe": 3, "hatte": 2, "sehr": 2, "grüße": 3, "grüßen": 3, "gruß": 3,
        "freundlichen": 3, "leider": 3, "schmerzen": 3, "zahn": 2, "zähne": 3, "heute": 2,
        "gestern": 2, "woche": 2, "auch": 1.5, "aber": 1.5, "oder": 1.5, "nur": 1.5, "warum": 2,
        "von": 1.5, "bei": 1, "vom": 1.5, "zum": 1.5, "zur": 2, "dem": 1, "sich": 1.5, "geehrte": 3,
        "geehrter": 3, "möchte": 3, "würde": 3, "wäre": 2, "jetzt": 2, "wieder": 2, "verschieben": 2,
        "absagen": 3, "tochter": 3, "sohn": 3, "frau": 2, "seit": 2, "wahrnehmen": 3, "zahnarzt": 3,
        "wann": 1, "mir": 1, "dir": 0.5, "nein": 2, "hallo": 1,
    },
    "en": {
        "the": 2, "and": 2, "is": 1, "i": 1, "you": 2, "my": 2, "your": 2, "to": 1, "of": 1, "for": 1,
        "with": 1.5, "it": 1, "this": 2, "that": 1.5, "please": 3, "thanks": 3, "thank": 3, "hello": 2,
        "hi": 1, "dear": 2, "regards": 3, "best": 1, "appointment": 3, "invoice": 3, "would": 3,
        "could": 3, "can": 1, "will": 2, "be": 1, "have": 2, "has": 2, "was": 1, "were": 2, "am": 1,
        "are": 2, "not": 1, "sorry": 3, "missed": 3, "like": 1.5, "need": 2, "last": 1, "week": 2,
        "tooth": 3, "teeth": 3, "pain": 1, "charged": 3, "book": 2, "sick": 2, "also": 1.5, "i'd": 3,
        "i'm": 3, "don't": 3, "what": 2, "when": 2, "how": 2, "much": 2, "there": 2, "about": 2,
        "yesterday": 3, "today": 3, "tomorrow": 3, "from": 1,
    },
    "pt": {
        "os": 1, "do": 1, "da": 1, "dos": 1, "em": 1, "na": 1, "uma": 2, "é": 1, "não": 3, "eu": 2,
        "você": 3, "meu": 2, "minha": 3, "para": 1.5, "com": 2, "por": 1, "obrigado": 3,
        "obrigada": 3, "bom": 2, "dia": 1, "boa": 2, "tarde": 2, "consulta": 2, "fatura": 3, "dente": 3,
        "dentes": 3, "dor": 3, "estou": 3, "tenho": 3, "está": 3, "muito": 3, "muita": 3, "também": 3,
        "já": 2, "ainda": 3, "depois": 3, "hoje": 3, "ontem": 3, "febre": 3, "inchada": 3,
        "inchado": 3, "ao": 2, "pelo": 2, "pela": 2, "queria": 3, "gostaria": 3, "olá": 3,
        "cumprimentos": 3, "atenciosamente": 3, "marcação": 3, "siso": 3, "tirei": 3, "isso": 2,
        "foi": 2, "bochecha": 3, "senhor": 2, "senhora": 2, "marcar": 2, "desmarcar": 3, "filha": 3,
        "filho": 3, "marido": 3, "pode": 2, "podem": 2, "posso": 3, "semana": 1,
    },
    "lb": {
        "ech": 3, "mir": 1, "dir": 1.5, "mer": 1, "dat": 2, "ass": 2, "net": 2, "eng": 2, "engem": 3,
        "enger": 3, "mat": 2, "fir": 3, "vun": 3, "vum": 3, "vu": 2, "op": 1.5, "och": 3, "awer": 3,
        "wann": 1, "wéi": 3, "wat": 2, "kënnt": 3, "kéint": 3, "kënnen": 3, "ginn": 2, "gëtt": 3,
        "hunn": 3, "hutt": 3, "sinn": 1.5, "sidd": 3, "mäin": 3, "mäi": 3, "meng": 3, "menger": 3,
        "mengem": 3, "är": 2, "ären": 3, "äre": 3, "ärer": 3, "moien": 3, "äddi": 3, "gréiss": 3,
        "léif": 3, "léiwen": 3, "duechter": 3, "jong": 2, "kand": 2, "zant": 3, "zänn": 3,
        "schécken": 3, "schéckt": 3, "geschéckt": 3, "maachen": 3, "gemaach": 3, "muer": 3,
        "gëschter": 3, "woch": 2, "dës": 3, "dësen": 3, "dëser": 3, "déi": 3, "deen": 2, "eis": 2,
        "iech": 3, "iwwer": 3, "ze": 2, "gären": 3, "gär": 3, "elo": 3, "nee": 2, "firwat": 3, "wou": 2,
        "péng": 3, "wgl": 3, "noriicht": 3, "haut": 1, "merci": 0.5, "rechnung": 0.5,
        "zänndokter": 3, "weess": 3, "wëll": 3, "kéinten": 3, "géif": 3, "mol": 2, "lescht": 3,
        "leschte": 3, "kann": 0.5,
    },
}

# Langues NON prises en charge par les textes de réponse : reconnues pour ne pas être confondues avec une
# langue prise en charge (un modèle a lu un e-mail italien comme de l'allemand).
_MARQUEURS_AUTRES: dict[str, dict[str, float]] = {
    "it": {"buongiorno": 3, "grazie": 3, "vorrei": 3, "sapere": 2, "quanto": 2, "costa": 1, "denti": 3, "dente": 1,
           "sono": 2, "della": 2, "questo": 2, "perché": 3, "molto": 2, "appuntamento": 3, "fattura": 3, "salve": 2,
           "cordiali": 3, "saluti": 3, "gentile": 2, "pulizia": 3, "mio": 1, "mia": 1, "il": 0.5, "di": 0.5,
           "che": 1, "non": 1, "ho": 2, "posso": 1},
    "es": {"hola": 3, "buenos": 3, "días": 3, "gracias": 3, "quisiera": 3, "cuánto": 3, "cuesta": 3, "cita": 3,
           "factura": 3, "dientes": 3, "muela": 3, "saludos": 3, "usted": 3, "favor": 1, "tengo": 2, "mucho": 2,
           "estoy": 1, "puedo": 2, "el": 0.5, "los": 1, "las": 1, "y": 0.5, "pero": 2},
    "nl": {"goedendag": 3, "goedemorgen": 3, "bedankt": 3, "dank": 1, "graag": 3, "afspraak": 3, "factuur": 3,
           "tand": 3, "tanden": 3, "kies": 2, "pijn": 3, "vriendelijke": 3, "groet": 3, "alstublieft": 3, "ik": 2,
           "het": 2, "een": 1, "niet": 2, "mijn": 3, "wij": 2, "jullie": 3, "kunt": 3, "u": 1},
}

_RE_MOT = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)
_RE_WEG = re.compile(r"\bw\.\s?e\.\s?g\.?|\bw\.e\.g\b", re.I)


def scores_langues(texte: str) -> dict[str, float]:
    bas = (texte or "").lower()
    scores = {langue: 0.0 for langue in LANGUES}
    for mot in _RE_MOT.findall(bas):
        mot = mot.replace("’", "'")
        variantes = {mot, *mot.split("'")}
        for langue, marqueurs in _MARQUEURS.items():
            scores[langue] += sum(marqueurs.get(v, 0.0) for v in variantes)
    # Indices orthographiques très discriminants
    scores["lb"] += 2.0 * min(bas.count("ë"), 6) + 3.0 * len(_RE_WEG.findall(bas))
    scores["pt"] += 2.0 * min(bas.count("ã") + bas.count("õ"), 5)
    scores["pt"] += 1.5 * min(len(re.findall(r"ção|ções", bas)), 4)
    scores["de"] += 1.5 * min(bas.count("ß"), 4)
    scores["fr"] += 1.0 * min(sum(bas.count(c) for c in "èêùœ"), 5)
    return scores


def _scores_autres(texte: str) -> dict[str, float]:
    mots = [m.replace("’", "'") for m in _RE_MOT.findall((texte or "").lower())]
    return {langue: sum(marqueurs.get(m, 0.0) for m in mots) for langue, marqueurs in _MARQUEURS_AUTRES.items()}


def nombre_de_mots(texte: str) -> int:
    return len(_RE_MOT.findall(texte or ""))


def detecter_langue(texte: str) -> tuple[str | None, float]:
    """Renvoie (code langue, confiance entre 0 et 1) ; (None, 0) si trop peu d'indices.

    Le code peut désigner une langue non prise en charge (it, es, nl) : la réponse partira alors en
    français, avec une consigne « à adapter » pour le secrétariat."""
    scores = scores_langues(texte)
    scores.update(_scores_autres(texte))
    classement = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    (premiere, s1), (_, s2) = classement[0], classement[1]
    if s1 < 3:
        return None, 0.0
    return premiere, round((s1 - s2) / s1, 2)
