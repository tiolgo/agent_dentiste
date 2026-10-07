"""Préparation d'un e-mail entrant : adresse, texte lisible, historique cité, empreinte."""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from email.utils import parseaddr

from .modeles import Mail

_RE_ADRESSE = re.compile(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+", re.UNICODE)
_RE_HTML = re.compile(r"<\s*(html|body|div|p|br|span|table|td)\b", re.I)
_RE_BLOC_HTML = re.compile(r"<\s*(br|/p|/div|/tr|/li|/h\d)\s*/?>", re.I)
_RE_BALISE = re.compile(r"<[^>]+>")
_RE_SCRIPT = re.compile(r"<\s*(script|style)\b.*?</\s*\1\s*>", re.I | re.S)

# Début de l'historique cité (« Le 3 oct. 2026, X a écrit : », « -----Original Message----- »...)
_ENTETES_CITATION = [
    re.compile(r"^\s*(le|on|am|em|den|de|el)\b.{3,160}\b(a [ée]crit|wrote|schrieb|escreveu|huet geschriwwen|geschriwwen)\s*:?\s*$", re.I),
    re.compile(r"^\s*-{2,}\s*(original message|message d'origine|message original|ursprüngliche nachricht|"
               r"mensagem original|message transféré|forwarded message|weitergeleitete nachricht)", re.I),
    re.compile(r"^\s*_{8,}\s*$"),
]
_ENTETE_DE = re.compile(r"^\s*\**\s*(de|from|von|envoyé par|enviado por)\s*\**\s*:", re.I)
_ENTETE_SUITE = re.compile(r"^\s*\**\s*(objet|subject|betreff|assunto|envoyé|sent|gesendet|enviado|à|to|an|para|date|datum|data)\s*\**\s*:", re.I)


def normaliser_adresse(brut: str) -> tuple[str, str]:
    """« Anne Muller <Anne.Muller@PT.lu> » -> ("anne.muller@pt.lu", "Anne Muller")."""
    nom, adresse = parseaddr(brut or "")
    adresse = adresse.strip().lower()
    if not _RE_ADRESSE.fullmatch(adresse):
        trouve = _RE_ADRESSE.search(brut or "")
        adresse = trouve.group(0).lower() if trouve else (brut or "").strip().lower()
    return adresse, nom.strip()


def adresses_citees(texte: str) -> list[str]:
    return sorted({a.lower() for a in _RE_ADRESSE.findall(texte or "")})


def html_vers_texte(contenu: str) -> str:
    contenu = _RE_SCRIPT.sub(" ", contenu)
    contenu = _RE_BLOC_HTML.sub("\n", contenu)
    contenu = _RE_BALISE.sub(" ", contenu)
    return html.unescape(contenu)


def nettoyer(texte: str) -> str:
    texte = unicodedata.normalize("NFC", texte or "")
    if _RE_HTML.search(texte):
        texte = html_vers_texte(texte)
    texte = texte.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    lignes = [ligne.rstrip() for ligne in texte.split("\n")]
    texte = "\n".join(lignes)
    return re.sub(r"\n{3,}", "\n\n", texte).strip()


def separer_citation(texte: str) -> tuple[str, str]:
    """Sépare le message nouveau de l'historique cité (réponses, transferts)."""
    lignes = texte.split("\n")
    for i, ligne in enumerate(lignes):
        coupe = (ligne.lstrip().startswith(">")
                 or any(r.match(ligne) for r in _ENTETES_CITATION)
                 or (_ENTETE_DE.match(ligne)
                     and any(_ENTETE_SUITE.match(l) for l in lignes[i + 1:i + 5])))
        if coupe and i > 0:
            nouveau = "\n".join(lignes[:i]).strip()
            if nouveau:
                return nouveau, "\n".join(lignes[i:]).strip()
    return texte, ""


def replier(texte: str) -> str:
    """Minuscules sans accents, en conservant la longueur (positions alignées sur le texte NFC)."""
    sortie = []
    for c in texte:
        if c in "’‘`´":
            sortie.append("'")
            continue
        if c in "–—‑":
            sortie.append("-")
            continue
        if c == " ":
            sortie.append(" ")
            continue
        base = "".join(x for x in unicodedata.normalize("NFKD", c) if not unicodedata.combining(x)).lower()
        if len(base) == 1:
            sortie.append(base)
        else:
            bas = c.lower()
            sortie.append(bas if len(bas) == 1 else c)
    return "".join(sortie)


def empreinte(expediteur: str, sujet: str, corps: str) -> str:
    brut = f"{expediteur}\n{sujet}\n{corps}".encode("utf-8")
    return hashlib.sha256(brut).hexdigest()


def preparer_mail(expediteur_brut: str, sujet: str | None, corps: str | None,
                  source_id: str | None = None, repondre_a: str | None = None) -> Mail:
    adresse, nom = normaliser_adresse(expediteur_brut or "")
    sujet = nettoyer(sujet or "").replace("\n", " ")
    corps = corps or ""
    texte_complet = nettoyer(corps)
    nouveau, cite = separer_citation(texte_complet)
    reponse_a = normaliser_adresse(repondre_a)[0] if repondre_a else ""
    return Mail(
        expediteur=adresse,
        sujet=sujet,
        corps=corps,
        source_id=source_id,
        expediteur_brut=expediteur_brut or "",
        nom_affiche=nom,
        repondre_a=reponse_a,
        texte=nouveau,
        texte_cite=cite,
        empreinte=empreinte(adresse, sujet, corps),
    )
