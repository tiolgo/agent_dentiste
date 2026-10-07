"""Lecture déterministe d'un e-mail (sans LLM).

Toujours exécutée, elle sert à trois choses :
1. le pré-tri instantané (les urgences possibles sont traitées en premier) ;
2. les signaux de sécurité (urgence, manipulation) que le LLM ne peut pas faire baisser ;
3. une analyse complète de secours si le LLM est indisponible ou répond mal.
"""

from __future__ import annotations

import re
from datetime import date

from .dates import reperer_dates
from .detecteurs import Signaux, detecter
from .langue import detecter_langue, nombre_de_mots
from .modeles import Analyse, Mail
from .normalisation import replier

_FACTURE = re.compile(
    r"\b(factures?|duplicatas?|rechnung\w*|invoices?|receipts?|faturas?|recibos?|quittances?|"
    r"note d'honoraires|honorarnote)\b")
_DEMANDE_ENVOI = re.compile(
    r"\b(renvoy\w*|envoy\w*|transmett\w*|recevoir|besoin|copie|duplicata|perdu|retrouve plus|"
    r"schick\w*|send\w*|zusend\w*|brauche|benotige|kopie|verloren|resend|need|copy|lost|"
    r"can'?t find|enviar|envie|mandar|mande|preciso|copia|perdi|schecken|brauch)\b|\?")
_TOUTES_FACTURES = re.compile(
    r"\b(toutes (mes|les) factures|all (my |the )?invoices|alle (meine )?rechnungen|"
    r"todas as (minhas )?faturas|all meng rechnungen)\b")
_NUMERO_FACTURE = re.compile(r"\b([Ff]-?\d{4}-\d{3,5})\b")
_FACTURATION = re.compile(
    r"\b(serai[- ]je factur\w*|sera factur\w*|vais[- ]je payer|dois[- ]je payer|frais d'annulation|"
    r"penalites?|paiement|virement|trop paye|paye deux fois|charged|charge me|fees?|paid|payment|"
    r"bezahl\w*|gebuhr\w*|berechnet|in rechnung gestellt|zahlung|uberweisung|cobrad\w*|cobrar|"
    r"pagamento|bezuel\w*)\b")
_ATTESTATION = re.compile(
    r"\b(attestation|certificat|justificatif|bescheinigung|bestatigung|attest|certificate|"
    r"proof of (attendance|presence|visit)|note for (my )?(employer|work|school)|atestado|declaracao|"
    r"comprovativ\w*|attestatioun|bestategung)\b")
_ATTESTATION_MEDICALE = re.compile(
    r"\b(certificat medical|arret de travail|arbeitsunfahigkeit\w*|krankmeldung|krankschreibung|"
    r"sick note|medical certificate|atestado medico|baixa medica|certificat de maladie)\b")
_RDV = re.compile(
    r"\b(rendez[- ]vous|rdv|termin\w*|appointments?|appt|consultas?|marcacao|check-?up|kontrolltermin)\b")
_RDV_ACTIONS = {
    "annuler": re.compile(
        r"\b(annul\w*|decommand\w*|absagen|abzusagen|abgesagt|stornier\w*|cancel\w*|desmarcar|"
        r"cancelar|ofsoen|ofgesot|annuleier\w*)\b"),
    "deplacer": re.compile(
        r"\b(deplacer|reporter|decaler|changer (de |la )?(date|heure|horaire)|avancer|verschieben|verlegen|"
        r"umbuchen|reschedule|postpone|move (my|the)|change (the|my) (date|time|appointment)|remarcar|adiar|"
        r"alterar|verleeen|verschiben)\b|\bne (pourrai|peux|pourrais) pas (venir|etre (present|la))|"
        r"\bnicht wahrnehmen|\bcan'?t make it|\bwon'?t be able to (come|make|attend)|"
        r"\bcannot (come|attend|make)|\bnao (vou |poderei |posso )?(poder )?(ir|comparecer)|"
        r"\b(kann|ka) net kommen"),
    "retard": re.compile(
        r"\b(en retard|aurai (\d+ minutes? de |un peu de |du )?retard|running late|"
        r"(be|am|i'?m|i'?ll be|will be)\b.{0,25}\blate|verspat\w*|(\d+ minuten|etwas) spater|atrasad[oa]|atraso|"
        r"ze spet|mei spet)\b"),
    "rdv_manque": re.compile(
        r"\b(rate|pas pu venir|pas venue?|missed|forgot|didn'?t (come|make it|show up)|verpasst|versaumt|"
        r"nicht (gekommen|erschienen)|faltei|esqueci|nao (fui|compareci|pude ir)|vergiess\w*|net komm\w*)\b"),
    "confirmer": re.compile(
        r"\b(confirm\w*|bestatig\w*|confirmar|confirmo|bestategen|toujours (prevu|maintenu)|still on)\b"),
    "prendre": re.compile(
        r"\b(prendre (un )?(nouveau )?(rendez-vous|rdv)|reserver|fixer (un )?(rendez-vous|rdv)|"
        r"(un |nouveau )(rendez-vous|rdv|controle)|termin (vereinbaren|buchen|bekommen|machen)|"
        r"(einen |neuen )termin|book\w*|schedule (a|an)|make an appointment|new (appointment|check-?up)|"
        r"marcar (uma |nova )?consulta|nova consulta|agendar|rendez-vous (huelen|maachen|fixeieren)|"
        r"(en )?neie(n)? (rendez-vous|termin))\b"),
}
_TARIF = re.compile(
    r"\b(combien|prix|tarifs?|cout\w*|devis|rembours\w*|wie ?viel|kostet|kosten|preis\w*|erstatt\w*|"
    r"kostenvoranschlag|how much|costs?|price\w*|quote|quotation|reimburs\w*|covered|quanto|custa|"
    r"preco|precos|custo|orcamento|reembols\w*|comparticip\w*|wei vill|kascht|praisser|rembourseier\w*)\b")
_REMBOURSEMENT = re.compile(
    r"\b(rembours\w*|pris en charge|prise en charge|erstatt\w*|ubernimmt|ubernommen|reimburs\w*|"
    r"covered|reembols\w*|comparticip\w*|rembourseier\w*)\b")
ACTES_MOTIFS: dict[str, re.Pattern] = {
    "consultation": re.compile(r"\b(consultation|controle|check-?up|bilan|untersuchung|kontroll\w*|vorsorge|consulta|controlo|revisao|konsultatioun)\b"),
    "detartrage": re.compile(r"\b(detartrage|tartre|nettoyage|zahnstein\w*|zahnreinigung|scal(e|ing)|cleaning|tartar|destartariza\w*|limpeza|zannsteen)\b"),
    "radio_panoramique": re.compile(r"\b(radio\w*|panoramique|rontgen\w*|panorama\w*|x-?rays?|radiograf\w*|panoramica)\b"),
    "extraction_simple": re.compile(r"\b(extraction|arracher|enlever une dent|extrakt\w*|zahn ziehen|ziehen|extract\w*|pull(ed)? (a|my) tooth|extracao|arrancar)\b"),
    "extraction_dent_sagesse": re.compile(r"\b(dents? de sagesse|weisheitszahn\w*|wisdom (tooth|teeth)|dente do siso|siso|weisheetszant|weisheetszann)\b"),
    "traitement_canal": re.compile(r"\b(canal|devitalis\w*|wurzel\w*|root canal|endodont\w*|desvitaliza\w*|wuerzel\w*)\b"),
    "couronne": re.compile(r"\b(couronnes?|krone\w*|crowns?|coroas?|kroun\w*)\b"),
    "blanchiment": re.compile(r"\b(blanchi\w*|bleaching|aufhell\w*|whiten\w*|branquea\w*|bleechen)\b"),
    "autre_acte": re.compile(r"\b(implants?|bridges?|bruck\w*|facettes?|veneers?|proth\w*|appareil\w*|orthodon\w*|zahnspange|braces|aparelho|dentier|gebiss|dentures?|plombage|composite|fullung|filling|obtura\w*|inlay|onlay|gouttiere)\b"),
}
INFOS_MOTIFS: dict[str, re.Pattern] = {
    "horaires": re.compile(r"\b(horaires?|heures? d'ouverture|ouverts?|fermes?|fermeture|offnungszeit\w*|geoffnet|geschlossen|opening hours|open on|are you open|horario\w*|aberto|fechado|effnungszaiten)\b"),
    "adresse": re.compile(r"\b(votre adresse|ou (se trouve|etes)[- ]vous|comment (venir|acceder|se rendre)|acces (au|a votre) cabinet|anfahrt|wo (ist|befindet)|your address|where are you|located|directions?|morada|endereco|onde fica|wou ass|wou sidd)\b"),
    "autre_info": re.compile(r"\b(parking|stationnement|se garer|parkplatz|parken|estacionamento|langues?|sprachen|languages?|linguas?|accessible|fauteuil roulant|rollstuhl|wheelchair|ascenseur|aufzug|lift|elevador)\b"),
    "telephone": re.compile(r"\b(numero de telephone|votre telephone|telefonnummer|phone number|numero de telefone|telefonsnummer)\b"),
    "rdv_en_ligne": re.compile(r"\b(doctena|en ligne|online)\b"),
    "urgences": re.compile(r"\b(service de garde|dentiste de garde|week-?end|le dimanche|la nuit|notdienst|bereitschaftsdienst|on-?call|out of hours|after hours|bereetschaft)\b"),
    "annulation": re.compile(r"\b(delai d'annulation|conditions d'annulation|cancellation policy|stornobedingungen|politica de cancelamento)\b"),
}
_PROFESSIONNEL = re.compile(
    r"\b(cher confrere|chere consoeur|chers confreres|liebe kollegin|lieber kollege|dear colleague|caro colega|"
    r"cara colega|laboratoire (de prothese|dentaire)|prothesiste|dentallabor|zahntechnik\w*|dental lab\w*|"
    r"laboratorio dentario|bon de livraison|lieferschein|delivery note)\b")
_INTERROGATION = re.compile(r"\?|\b(quels?|quelles?|est-ce que|pouvez-vous|welche|wann|wo|what|which|where|quais?|onde|wéini|wou|wat)\b")
_RECLAMATION = re.compile(
    r"\b(inadmissible|inacceptable|scandal\w*|honteux|pas (du tout )?satisfaite?|mecontente?|plainte|"
    r"reclamation|decue?|deplorable|unverschamt|beschwerde|unzufrieden|enttauscht|unakzeptabel|complaint|"
    r"unacceptable|disappointed|dissatisfied|outrageous|reclamacao|insatisfeit[oa]|inaceitavel|vergonha|"
    r"reklamatioun|net zefridden)\b")
_ADMINISTRATIF = re.compile(
    r"\b(changement d'adresse|nouvelle adresse|nouveau numero|changer (mon|mes|d') ?(adresse|coordonnees|numero|e-?mail)|"
    r"mettre a jour (mon|mes)|dossier medical|neue adresse|adressanderung|patientenakte|change (my|of) address|"
    r"new (address|email|phone number)|update my (details|address|email)|medical records?|medical file|"
    r"mudanca de (morada|endereco)|nova morada|processo clinico|nei adress)\b|"
    r"\b(chang\w*|nouvelle?|new|neue?n?|nova|novo|nei)\b.{0,20}\b(mutuelle|assurance|krankenkasse|versicherung|"
    r"insurance|seguro)\b|"
    r"\b(copie|envoyer|recevoir|transmettre|copy|send|kopie|schicken|copia|enviar)\b.{0,30}\b(radios?|radiographies|rontgen\w*|x-?rays?|dossier|akte|records|processo)\b")
_LIBELLES_RESUME = {
    "demande_facture": "demande de facture", "demande_attestation": "demande d'attestation",
    "rendez_vous": "rendez-vous", "question_tarif": "question de tarif", "question_facturation": "question de facturation",
    "question_medicale": "question médicale", "information_pratique": "information pratique",
    "administratif": "démarche administrative", "reclamation": "réclamation", "professionnel": "message professionnel",
    "publicite": "publicité", "message_automatique": "message automatique", "remerciement": "remerciement",
    "autre": "demande non reconnue",
}
# « Quel soin m'avez-vous fait ? » : demande du contenu du dossier, jamais traitée par e-mail (règle 4).
CONTENU_DOSSIER = re.compile(
    r"\b(quels?|quelles?) (soins?|traitements?|actes?|interventions?)\b.{0,30}\b(j'ai|ai-je|m'a|m'avez|on m'a|recu)|"
    r"\bque m'avez-vous fait|\bwhat (treatment|procedure|was done)\b|\bwhich (treatment|procedure)\b|"
    r"\bwelche behandlung\w*\b.{0,30}\b(hatte|habe|bekommen|gemacht|wurde)|"
    r"\bque (tratamento|tratamentos)\b.{0,30}\b(me fizeram|fiz|fizeram)|"
    r"\bwat fir eng behandlung\b|\b(copie|copy|kopie|copia)\b.{0,30}\b(dossier|akte|records?|file|processo)\b")
_MERCI = re.compile(r"\b(merci|thanks|thank you|danke|vielen dank|obrigad[oa]|merci villmools)\b")
_RELATIONS = (
    ("conjoint", re.compile(
        r"\b(mon|ma) (mari|epoux|epouse|femme|conjointe?|compagnon|compagne|partenaire)\b|"
        r"\bmy (husband|wife|partner|spouse)\b|\b(mein|meine|meinen|meinem|meiner|meines) "
        r"(mann|mannes|ehemann\w*|frau|ehefrau|partner\w*)\b|\b(meu|minha) (marido|mulher|esposa|esposo|"
        r"companheir[oa])\b|\b(mai|meng|menger|mengem) (mann|fra|partner\w*)\b")),
    ("enfant", re.compile(
        r"\b(mon|ma|mes|notre|nos) (fils|fille|filles|enfants?|petite?|bebe|garcon)\b|"
        r"\bmy (son|daughter|child|kid|kids|children|boy|girl)\b|\b(mein|meine|meinen|meinem|meiner|meines|"
        r"unser\w*) (sohn\w*|tochter|kind\w*|kinder)\b|\b(meu|minha|meus|minhas|nosso|nossa) (filh[oa]s?|"
        r"crianca|menin[oa])\b|\b(mai|meng|menger|mengem|eis\w*) (jong|duechter|kand|kanner|meedchen)\b")),
    ("parent", re.compile(
        r"\b(mon|ma) (pere|mere|maman|papa)\b|\bmy (father|mother|mom|mum|dad)\b|"
        r"\b(mein|meine|meinen|meinem|meiner|meines) (vater\w*|mutter)\b|\b(meu|minha) (pai|mae)\b|"
        r"\b(mai|meng|menger|mengem) (papp|mamm)\b")),
)
_PRENOM_APRES = re.compile(r"[ \t]*,?[ \t]*([A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+(?:-[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+)?)")
_FORMULE = re.compile(
    r"^(merci|cordialement|bien a vous|salutations|bonne journee|bien cordialement|best|regards|kind regards|"
    r"best regards|thanks|thank you|cheers|mit freundlichen grussen|mfg|viele grusse|lg|beste grusse|danke|"
    r"obrigad[oa]|cumprimentos|atenciosamente|com os melhores cumprimentos|mat beschte greiss|"
    r"merci villmools|schei?ne gruss|greiss|bises|a bientot)\W*$")
_NOM_PROPRE = re.compile(r"[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'-]+(?:\s+[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'-]+){0,3}")


_SIGNATURE_EN_LIGNE = re.compile(
    r"(?:merci|cordialement|salutations|thanks|thank you|regards|best|danke|grüße|gruß|obrigad[oa]|cumprimentos|"
    r"gréiss|bises|bien à vous)[,.!]?\s+([A-ZÀ-ÖØ-Þ][\wÀ-ÿ'-]+(?:\s+[A-ZÀ-ÖØ-Þ][\wÀ-ÿ'-]+){0,2})\s*\.?\s*$",
    re.IGNORECASE)
_TIERS_CIVILITE = re.compile(
    r"\b(?:de|du|pour|of|for|von|für|para|vun|fir)\s+(?:M\.|Mme|Mlle|Mr\.?|Mrs\.?|Ms\.?|Monsieur|Madame|Herrn?|Frau|"
    r"Sr\.?|Sra\.?|Senhor|Senhora)\s+([A-ZÀ-ÖØ-Þ][\wÀ-ÿ'-]+)(?:\s+([A-ZÀ-ÖØ-Þ][\wÀ-ÿ'-]+))?")


def nom_en_signature(texte: str) -> str:
    lignes = [l.strip() for l in texte.split("\n") if l.strip()]
    for ligne in reversed(lignes[-4:]):
        if _FORMULE.match(replier(ligne)):
            continue
        if len(ligne) <= 40 and _NOM_PROPRE.fullmatch(ligne):
            return ligne
        fin = _SIGNATURE_EN_LIGNE.search(ligne)
        if fin and fin.group(1)[0].isupper():
            return fin.group(1)
        break
    return ""


def _personne_concernee(texte: str, plie: str) -> tuple[str, str]:
    """Relation (« mon mari », « menger Duechter »...) et prénom qui la suit, s'il y en a un."""
    for relation, motif in _RELATIONS:
        prenom_trouve = None
        for m in motif.finditer(plie):
            suite = _PRENOM_APRES.match(texte, m.end())
            if suite:
                prenom_trouve = suite.group(1)
                break
            prenom_trouve = prenom_trouve or ""
        if prenom_trouve is not None:
            return relation, prenom_trouve
    return "", ""


_RE_ADRESSE_OU_LIEN = re.compile(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+|https?://\S+")
_SUJET_REPONSE = re.compile(r"^\s*(re|aw|antw|res|tr|fw|fwd|wg)\s*:", re.I)


def analyser_regles(mail: Mail, ref: date) -> tuple[Analyse, Signaux]:
    texte = f"{mail.sujet}\n{mail.texte}"
    if _SUJET_REPONSE.match(mail.sujet):      # « Re: Votre rendez-vous » : l'objet est celui de l'ancien message
        texte = mail.texte
    texte = _RE_ADRESSE_OU_LIEN.sub(" ", texte)   # « remboursements@assur.lu » n'est pas une question de remboursement
    plie = replier(texte)
    signaux = detecter(mail.expediteur, mail.sujet, mail.texte)
    langue, confiance = detecter_langue(texte)
    a = Analyse(source="regles", langue=langue, langue_confiance=confiance, nb_mots=nombre_de_mots(texte))
    intentions: list[str] = []

    if signaux.automatique:
        intentions.append("message_automatique")
    if signaux.score_publicite >= 2:
        intentions.append("publicite")
    if _FACTURE.search(plie) and _DEMANDE_ENVOI.search(plie):
        intentions.append("demande_facture")
    if _ATTESTATION.search(plie):
        intentions.append("demande_attestation")
        if _ATTESTATION_MEDICALE.search(plie):
            a.type_attestation = "medicale"
    actions = [nom for nom, motif in _RDV_ACTIONS.items() if motif.search(plie)]
    if _RDV.search(plie) or set(actions) & {"annuler", "deplacer", "retard"}:
        if not _RDV.search(plie):
            actions = [x for x in actions if x not in ("confirmer", "rdv_manque")]
        a.actions_rdv = actions
        if actions:
            intentions.append("rendez_vous")
    if _TARIF.search(plie):
        intentions.append("question_tarif")
        a.actes_tarif = [acte for acte, motif in ACTES_MOTIFS.items() if motif.search(plie)]
        if "extraction_dent_sagesse" in a.actes_tarif and "extraction_simple" in a.actes_tarif:
            a.actes_tarif.remove("extraction_simple")
        a.question_remboursement = bool(_REMBOURSEMENT.search(plie))
    a.indice_facturation = bool(_FACTURATION.search(plie))
    if a.indice_facturation and "question_tarif" not in intentions:
        intentions.append("question_facturation")
        a.questions_ouvertes.append("Question sur la facturation ou un paiement (voir le message).")
    if signaux.question_medicale:
        intentions.append("question_medicale")
    infos = [nom for nom, motif in INFOS_MOTIFS.items() if motif.search(plie)]
    if infos and _INTERROGATION.search(plie):
        intentions.append("information_pratique")
        a.infos_demandees = infos
    if _RECLAMATION.search(plie):
        intentions.append("reclamation")
    if _PROFESSIONNEL.search(plie):
        intentions.append("professionnel")
    if _ADMINISTRATIF.search(plie) or CONTENU_DOSSIER.search(plie):
        intentions.append("administratif")
    if not intentions and _RDV.search(plie) and _INTERROGATION.search(plie):
        intentions.append("rendez_vous")          # question sur un rendez-vous, action non reconnue
    if not intentions and _MERCI.search(plie) and len(mail.texte) < 250 and "?" not in mail.texte:
        intentions.append("remerciement")
    a.intentions = intentions or ["autre"]

    relation, prenom = _personne_concernee(texte, plie)
    a.personne_concernee = relation or "expediteur"
    a.prenom_concerne = prenom
    civilite = _TIERS_CIVILITE.search(texte)
    if not relation and civilite:              # « les factures de M. Thomas Schneider »
        a.personne_concernee = "autre_personne"
        a.prenom_concerne, a.nom_concerne = ((civilite.group(1), civilite.group(2)) if civilite.group(2)
                                             else ("", civilite.group(1)))
    a.nom_signature = nom_en_signature(mail.texte)

    numero = _NUMERO_FACTURE.search(texte)
    a.facture_numero = numero.group(1).upper() if numero else ""
    a.toutes_factures = bool(_TOUTES_FACTURES.search(plie))

    reperes = reperer_dates(texte, ref)
    a.dates = reperes.dates
    a.plage = reperes.plage
    a.heure_rdv = reperes.heure
    if reperes.mois_seuls:
        a.periode_mois = reperes.mois_seuls[0].mois or 0
        a.periode_annee = reperes.mois_seuls[0].annee or 0
    if reperes.annee_indice and not a.periode_annee:
        a.periode_annee = reperes.annee_indice
    a.envoi_autre_adresse = signaux.autres_adresses[0] if signaux.autres_adresses else ""

    a.urgence = signaux.urgence
    a.signes_urgence = signaux.signes_forts + signaux.signes_faibles
    a.question_medicale = signaux.question_medicale
    a.suspect = signaux.suspicion
    a.raisons_suspect = signaux.raisons_suspicion()
    if a.suspect == "certain":
        a.resume = "Lecture par règles : message suspect (manipulation ou hameçonnage)."
    else:
        a.resume = "Lecture par règles : " + ", ".join(_LIBELLES_RESUME.get(i, i) for i in a.intentions) + "."
    return a, signaux
