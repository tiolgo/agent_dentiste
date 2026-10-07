"""Garde-fous : derniers contrôles, indépendants, juste avant l'écriture du brouillon.

Ils ne font confiance ni au LLM ni au code de décision :
- chaque pièce jointe, et chaque donnée de dossier citée dans la réponse, est ré-autorisée (règle 3) ;
- la réponse ne doit contenir aucune formulation de conseil médical (règle 1) ;
- hors blocs de tarifs généraux : aucun vocabulaire de soins, aucun numéro de dent (règle 4) ;
- aucune adresse e-mail ni numéro de téléphone autre que celui du cabinet ;
- aucun texte libre produit par le LLM ne doit s'y retrouver ;
- un message suspect ne reçoit ni réponse ni pièce jointe.
Si un contrôle échoue, le brouillon est remplacé par une version neutre « à compléter ».
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import date

from . import autorisation
from .connaissances import TELEPHONE
from .decision import Bloc, Decision
from .modeles import LANGUES, Analyse, Mail
from .normalisation import replier
from .redaction import Reponse

CONSEIL_MEDICAL = re.compile(
    r"\b(prene[zr]|take|nehmen sie|tome|huelt)\b.{0,40}\b(ibuprof\w*|paracetamol|doliprane|dafalgan|antibiot\w*|"
    r"aspirin\w*|antalgique\w*|schmerz\w*|painkiller\w*|analgesico\w*|comprime\w*|\w*tablett\w*|pills?|"
    r"tablets?|comprimidos?)"
    r"|\b(c'est|it'?s|it is|das ist|es ist|ass dat|isso e)\s+(tout a fait |completement |parfaitement |perfectly |"
    r"completely |quite |ganz |vollig |totalmente )?normale?\b"
    r"|\b(c'est|it'?s|es ist|isso e)\s+(sans gravite|pas grave|nothing serious|not serious|nicht schlimm|nada grave)\b"
    r"|\b(rincez|rinse|spulen sie|bocheche|gargarisez)\b|\b(poche de glace|de la glace|ice pack|kuhlen sie|gelo)\b"
    r"|\b(appliquez|aplique)\b|\b(bain de bouche|mouthwash|mundspulung)\b"
    r"|\b(ne vous inquietez pas|don'?t worry|keine sorge|nao se preocupe|maacht iech keng suergen)\b"
    r"|\b(cela va passer|ca va passer|it will pass|das geht vorbei|vai passar|dat geet riwwer)\b"
    r"|\b(diagnos\w*|dry socket|alveolite|alveolitis)\b")

VOCABULAIRE_SOINS = re.compile(
    r"\b(extractions?|traitements? de canal|devitalis\w*|couronnes?|detartrage|caries?|implants?|orthodon\w*|"
    r"plombages?|dents? de sagesse|controle annuel|post-extraction|"
    r"extraktion\w*|wurzel\w*|kronen?|zahnstein\w*|karies|kieferorthop\w*|weisheitsz\w*|zahnspange|"
    r"root canal|crowns?|scaling|cavit(y|ies)|orthodontic\w*|wisdom (tooth|teeth)|fillings?|braces|"
    r"extracao|tratamento de canal|coroas?|siso|ortodon\w*|desvitaliza\w*|"
    r"wuerzel\w*|kroun\w*|weisheetsz\w*)\b")
DENT_NUMEROTEE = re.compile(r"\b(dent|dente|zahn|tooth|zant)\s*(n[°o.]?\s*)?\d{1,2}\b")
ADRESSE_EMAIL = re.compile(r"[\w.+'-]+@[\w-]+(\.[\w-]+)+")
TELEPHONE_TEXTE = re.compile(r"\+?\d[\d .]{7,}\d")
_CHIFFRES_CABINET = re.sub(r"\D", "", TELEPHONE)


def controler(mail: Mail, decision: Decision, reponse: Reponse | None, dossier, ref: date,
              analyse_llm: Analyse | None = None) -> list[str]:
    problemes: list[str] = []
    if decision.langue not in LANGUES:
        problemes.append(f"langue de réponse non prise en charge ({decision.langue})")
    if "suspect" in decision.drapeaux and "urgence" not in decision.drapeaux and (decision.pieces or reponse):
        problemes.append("message suspect : ni réponse ni pièce jointe ne sont permises")

    # Règle 3 : chaque pièce jointe est revérifiée, indépendamment de la décision.
    for piece in decision.pieces:
        patient = dossier.patient(piece.patient_id)
        if piece.type == "facture":
            facture = dossier.facture_par_fichier(piece.chemin)
            if facture is None or facture.patient_id != piece.patient_id:
                problemes.append(f"pièce jointe {piece.chemin} : n'appartient pas au dossier annoncé")
        elif piece.type == "attestation":
            rdv = piece.rdv
            if rdv is None or rdv.patient_id != piece.patient_id or rdv.statut != "effectué":
                problemes.append(f"attestation {piece.chemin} : rendez-vous non effectué ou d'un autre dossier")
        else:
            problemes.append(f"type de pièce jointe inconnu : {piece.type}")
        verdict = autorisation.verifier(mail, patient, dossier, ref)
        if not verdict.autorise:
            problemes.append(f"pièce jointe {piece.chemin} : envoi non autorisé ({verdict.raison})")

    # Règle 3 (suite) : toute donnée de dossier citée dans le texte.
    for bloc in decision.blocs:
        if bloc.patient_id is not None:
            verdict = autorisation.verifier(mail, dossier.patient(bloc.patient_id), dossier, ref)
            if not verdict.autorise:
                problemes.append(f"le paragraphe « {bloc.cle} » cite un dossier pour lequel l'expéditeur n'est pas "
                                 f"autorisé ({verdict.raison})")
    if reponse is None:
        return problemes

    texte = replier(reponse.texte)
    conseil = CONSEIL_MEDICAL.search(texte)
    if conseil:
        problemes.append(f"formulation assimilable à un conseil médical : « {conseil.group(0)} »")
    for bloc, segment in reponse.segments:
        if bloc.tarif:
            continue                    # grille tarifaire générale : vocabulaire d'actes autorisé
        plie = replier(segment)
        soin = VOCABULAIRE_SOINS.search(plie) or DENT_NUMEROTEE.search(plie)
        if soin:
            problemes.append(f"vocabulaire de soins dans la réponse (« {soin.group(0)} ») : risque de divulgation du dossier")
    if ADRESSE_EMAIL.search(reponse.texte):
        problemes.append("une adresse e-mail figure dans la réponse")
    for numero in TELEPHONE_TEXTE.findall(reponse.texte):
        if re.sub(r"\D", "", numero) != _CHIFFRES_CABINET:
            problemes.append("un numéro de téléphone autre que celui du cabinet figure dans la réponse")
    if analyse_llm is not None:
        libres = [analyse_llm.resume, *analyse_llm.questions_ouvertes, *analyse_llm.raisons_suspect]
        if any(len(t) >= 25 and replier(t) in texte for t in libres):
            problemes.append("un texte rédigé par le LLM se retrouve dans la réponse")
    return problemes


def neutraliser(decision: Decision, problemes: list[str]) -> Decision:
    """Version sûre du brouillon : aucune donnée, aucune pièce jointe, à rédiger par le secrétariat."""
    blocs = [Bloc("urgence", {"rappel": False})] if "urgence" in decision.drapeaux else []
    blocs.append(Bloc("autre", a_completer="le brouillon automatique a été bloqué par un contrôle de sécurité : "
                                           "rédiger la réponse manuellement"))
    return replace(decision, blocs=blocs, pieces=[], nom_salutation=None,
                   drapeaux=decision.drapeaux + ["garde_fou"],
                   notes=decision.notes + ["Brouillon automatique bloqué par un garde-fou (détail ci-dessous)."])
