"""Détecteurs déterministes (sans LLM), en cinq langues.

- signes d'urgence et question médicale ;
- tentative de manipulation de l'IA, demande de données en masse, usurpation d'organisme ;
- publicité, message automatique.

Ils sont volontairement larges : pour l'urgence et la sécurité, le système retient
toujours le plus prudent entre ces détecteurs et le LLM. Tous les motifs portent sur le
texte « replié » (minuscules, sans accents, apostrophes droites).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .normalisation import adresses_citees, replier


def _c(*motifs: str) -> list[re.Pattern]:
    return [re.compile(m) for m in motifs]


# ======================================================================
# Urgence
# ======================================================================

SIGNES_FORTS: dict[str, list[re.Pattern]] = {
    "fièvre": _c(
        r"\bfievre", r"\bfebril", r"\bfieber", r"\bfever", r"\bfebre\b", r"\bfeiwer",
        r"\b3[89]([.,]\d)? ?(°|degres|grad|degrees|graus)"),
    "gonflement": _c(
        r"\bgonfl", r"\benfl(e|ee|ure)s?\b", r"\b(oe|œ)deme", r"\bgeschwoll", r"\bschwellung",
        r"\bangeschwoll", r"\bdick(e|er|en)? (backe|wange)", r"\bswell", r"\bswollen", r"\binchad",
        r"\binchac", r"\binchou", r"\bdeck(eg|t)? bak"),
    "saignement important": _c(
        r"\bsaign\w*\b.{0,30}\b(beaucoup|abondamment|sans arret|toujours|encore|depuis|enormement)",
        r"\b(ne|n') ?(s'arrete|arrete|cesse) pas de saigner", r"\bsaignements? (important|abondant|continu)",
        r"\bhemorrag", r"\bblut\w*\b.{0,30}\b(stark|immer noch|seit|ununterbrochen|nicht auf)",
        r"\bstarke blutung", r"\bhort nicht auf zu bluten",
        r"\b(won'?t|doesn'?t|does not|will not) stop bleeding",
        r"\bbleed\w*\b.{0,20}\b(a lot|heavily|for hours|since|still|non.?stop)", r"\bheavy bleeding",
        r"\bsangr\w*\b.{0,20}\b(muito|sem parar|ainda|desde)", r"\bnao para de sangrar",
        r"\bbludd\w*\b.{0,20}\b(staark|nach emmer|net op)"),
    "choc / dent cassée": _c(
        r"\b(suis|est|sommes|es|etait|etais) tombee?s?\b(?! malade)", r"\bune chute\b", r"\baccident\b",
        r"\bun choc\b", r"\bdents? (cassee|casse|fracturee|arrachee|expulsee|tombee|delogee)s?\b",
        r"\bcasse (une|la|sa|ma|deux) dents?", r"\bunfall", r"\bgesturzt", r"\bhingefallen",
        r"\bzahn\w* (ist |sind )?(abgebrochen|ausgeschlagen|rausgefallen|herausgefallen)",
        r"\b(fell|fallen)\b(?! ill| sick| asleep)", r"\bknocked out", r"\bbroken (front )?tooth",
        r"\btooth (broke|is broken|has broken|came out|fell out|got knocked)", r"\bchipped",
        r"\bacidente", r"\bcai\b", r"\bcaiu\b", r"\bdente (partido|partiu|caiu|quebrado|quebrou)",
        r"\b(parti|quebrei) (um|o) dente", r"\bgefall\b", r"\bofgebrach", r"\berausgefall"),
    "difficulté à respirer / avaler": _c(
        r"\b(du mal|difficultes?|peine|impossible|n'arrive pas|n'arrive plus|ne peux pas|ne peux plus) "
        r"(a |pour )?(respirer|avaler|deglutir|ouvrir la bouche)",
        r"\batemnot", r"\b(schwer|kaum) (atmen|schlucken)", r"\bkann (nicht|kaum) (mehr )?(atmen|schlucken)",
        r"\bschluckbeschwerden", r"\bmund nicht (mehr )?(auf|offnen)",
        r"\b(hard|difficult|trouble|struggling|can'?t|cannot|unable) (to )?(breath|swallow|open my mouth)",
        r"\b(dificuldade|custa) (em |a |para )?(respirar|engolir|abrir a boca)",
        r"\bnao consigo (respirar|engolir|abrir a boca)", r"\b(kann|ka) (net|kaum) (ootmen|schlecken)"),
    "douleur intense": _c(
        r"\bdouleurs? (tres |trop |vraiment )?(forte|intense|insupportable|atroce|terrible|enorme|horrible|violente|aigue)s?",
        r"\b(tres|trop|horriblement|terriblement|tellement) mal\b", r"\bmal (de chien|insupportable|atroce)",
        r"\bne (dors|dort|dormons) plus", r"\binsupportable",
        r"\b(starke|stark|heftige|unertragliche|extreme|schlimme|furchtbare|hollische)n? (zahn)?schmerz",
        r"\bunertraglich",
        r"\b(severe|unbearable|excruciating|terrible|extreme|intense|awful|horrible) (tooth ?)?(pain|ache)",
        r"\b(a lot of|so much) pain", r"\bkilling me", r"\bmuita dor",
        r"\bdor\w* (forte|insuportave|terrive|intensa|horrive)", r"\binsuportave",
        r"\b(staark|vill|schlemm|enorm) peng", r"\bpeng\w*\b.{0,15}\b(net auszehalen|schlemm|staark)"),
    "infection / abcès": _c(
        r"\babces", r"\bpus\b", r"\binfect", r"\babszess", r"\beiter", r"\babscess", r"\babcesso",
        r"\binfec", r"\beeter"),
    "réaction allergique": _c(
        r"\breaction allergique", r"\burticaire", r"\ballergische reaktion", r"\bnesselsucht",
        r"\ballergic reaction", r"\bhives\b", r"\breacao alergica", r"\ballergesch reaktioun"),
    "prise excessive de médicaments": _c(
        r"\bj'ai pris (\d+|plusieurs|beaucoup|trop)\b.{0,25}\b(comprimes|cachets|gelules|doliprane|dafalgan|ibuprofene|paracetamol|medicaments)",
        r"\btrop de (medicaments|comprimes|cachets)", r"\b(overdose|surdosage|uberdosis|sobredosagem|iwwerdosis)",
        r"\b(took|taken) (\d+|too many|a lot of)\b.{0,15}\b(pills|tablets|painkillers)",
        r"\b(\d+|zu viele) tabletten (genommen|eingenommen)",
        r"\btomei (\d+|muitos|demasiados)\b.{0,15}\b(comprimidos|medicamentos)"),
}

SIGNES_FAIBLES: dict[str, list[re.Pattern]] = {
    "engourdissement": _c(
        r"\bje ne sens plus\b", r"\bengourdi", r"\bfourmill", r"\btaub\b", r"\bkribbel", r"\bgefuhllos",
        r"\bnumb", r"\btingling", r"\bdormente", r"\bformigue"),
    "mention d'urgence": _c(
        r"\burgen(t|te|ce|ces|tes)\b", r"\bau plus vite\b", r"\bdringend", r"\bnotfall", r"\bemergency",
        r"\burgently\b", r"\basap\b", r"\burgencia", r"\bnoutfall", r"\bdrengend"),
}

# Contexte anatomique ou douleur : confirme qu'un signe fort concerne bien la bouche / un soin.
CONTEXTE_MEDICAL = re.compile(
    r"\b(dents?|gencives?|joues?|machoire|bouche|levres?|visage|douleurs?|mal (a|au|aux)|"
    r"zahn\w*|zahne|backe|wange|kiefer|mund|lippe|gesicht|schmerz\w*|"
    r"tooth|teeth|gums?|cheek|jaw|mouth|lips?|face|pain|ache|aching|hurts?|"
    r"dentes?|gengivas?|bochecha|maxilar|boca|labio|rosto|dor|doi|"
    r"zant|zann|zannfleesch|bak|mond|gesiicht|peng|deet wei)\b")

SYMPTOMES = re.compile(
    r"\b(douleurs?|douloureu\w*|j'ai (tres |trop |un peu |encore |toujours )?mal|"
    r"mal (a|au|aux) (la |les |une |ma |mes )?(dent|dents|gencive|gencives|machoire|joue|bouche)|"
    r"gene|sensibles?|sensibilite|saign\w*|dent qui bouge|carie|abces|gonfl\w*|fievre|irrit\w*|"
    r"aphtes?|brulure|lancin\w*|elanc\w*|"
    r"schmerz\w*|tut weh|weh\b|empfindlich\w*|blut\w*|zahnfleisch\w*|entzund\w*|wackel\w*|geschwoll\w*|"
    r"pain\w*|hurts?|hurting|aches?|aching|sore|sensitiv\w*|bleed\w*|gums?|loose tooth|cavity|swell\w*|"
    r"dor(es)?|doi|sensivel|sensibilidade|sangr\w*|gengivas?|dente mole|inflama\w*|incomodo|"
    r"desconforto|inchad\w*|febre|peng|deet wei|empfindlech|bludd\w*|zannfleesch)\b")

QUESTIONS_MEDICALES = re.compile(
    r"(est[- ]ce (que c'est )?normal|c'est normal|normal\s*\?|is (it|this|that) normal|\be normal\b|"
    r"ist (das|es) normal|ass (dat|et) normal|puis[- ]je prendre|dois[- ]je prendre|peut[- ]on prendre|"
    r"(puis[- ]je|je peux|peut[- ]on|pourrai[- ]je|est-ce que je (peux|pourrai)) (manger|boire|fumer|prendre|me brosser|faire du sport)|"
    r"can i (take|eat|drink|brush|smoke)|should i (take|worry|be worried)|"
    r"posso (tomar|comer|beber|fumar|escovar)|darf ich\b.{0,30}\b(nehmen|essen|trinken|rauchen)|"
    r"kann ich\b.{0,30}\b(nehmen|essen|trinken|rauchen)|(darf|kann) ech\b.{0,30}\b(huelen|iessen|drenken|femmen)|"
    r"que (dois-je|faut-il) faire|what should i do|o que (devo|posso) fazer|was soll ich (tun|machen)|"
    r"wat soll ech maachen|est-ce grave|is it serious|\be grave\b|ist das schlimm|ass dat schlemm|"
    r"inquiet\w*|worried|preocupad\w*|besorgt|suergen)")

MEDICAMENTS = re.compile(
    r"\b(ibuprof\w*|paracetamol|doliprane|dafalgan|efferalgan|advil|nurofen|aspirine?|"
    r"antibiotique\w*|antibiotic\w*|antibiotikum|antibiotika|antibiotico\w*|amoxicilline?|augmentin|"
    r"antalgique\w*|anti-?inflammatoire\w*|schmerzmittel|schmerztablette\w*|painkiller\w*|"
    r"analgesico\w*|bain de bouche|mouthwash|mundspulung)\b")

APRES_SOIN = re.compile(
    r"\b(apres|depuis) (mon|ma|le|la|l'|mes|les) ?(extraction|traitement|soin|operation|intervention|"
    r"detartrage|plombage|couronne|implant|devitalisation)|"
    r"\bnach (der|dem|meiner|meinem) (behandlung|extraktion|op|operation|wurzelbehandlung)|"
    r"\bafter (my|the) (extraction|treatment|procedure|filling|surgery|root canal|crown)|"
    r"\bdepois d[ao] (extracao|tratamento|cirurgia|desvitalizacao)|"
    r"\bno (meu )?tratamento|\bno der (behandlung|extraktioun|operatioun)|"
    r"\b(tirei|arranquei|extrai)\b")


# ======================================================================
# Sécurité : manipulation, données en masse, usurpation
# ======================================================================

INJECTION = _c(
    r"\b(ignore[zr]?|oublie[zr]?|ne tiens? pas compte|ne tenez pas compte)\b.{0,40}\b(instructions?|consignes?|regles|directives|prompt)",
    r"\b(ignore|disregard|forget|override)\b.{0,40}\b(instructions?|prompts?|rules|guidelines|directives)",
    r"\b(ignorier\w*|vergiss\w*|missachte\w*)\b.{0,40}\b(anweisungen|anleitungen|regeln|vorgaben)",
    r"\b(ignor[ae]\w*|esquec\w*|desconsider\w*)\b.{0,40}\b(instruc\w*|regras)",
    r"\b(ignoreier\w*|vergiess\w*)\b.{0,40}\b(instruktiounen|uweisungen)",
    r"\b(message|instruction|note|commande|ordre) (du |de |d'un )?(systeme|system|administrateur|admin)\b",
    r"\bsystem(e)? (message|prompt|instruction|override)\b", r"\bsysteme interne\b",
    r"\b(tu es|vous etes) (maintenant|desormais)\b", r"\byou are now\b", r"\bact as (an?|the)\b",
    r"\bnew instructions?\b", r"\bnouvelles? (instructions?|consignes?)\b",
    r"\bmode (developpeur|developer|admin|debug|maintenance)\b", r"\bjailbreak",
    r"<\|?(im_start|im_end|system|assistant)\|?>", r"\[/?(inst|system)\]", r"#{2,}\s*(instruction|system)",
    r"\b(en tant qu'|as an?)\s*(ia|ai|assistant|intelligence artificielle|language model|modele de langage)\b",
    r"\b(assistant|ia|chatbot|robot|llm|gpt|modele)\b.{0,30}\b(doit|devez|must|should|soll|deve)\b.{0,30}\b(envoyer|transmettre|send|senden|enviar)",
)

DONNEES_EN_MASSE = _c(
    r"\b(liste|listing|fichier|export\w*|extraction|base de donnees|ensemble|totalite)\b.{0,40}\b(patients?|clients?|dossiers)\b",
    r"\btous (les|vos) (patients|dossiers|clients)\b",
    r"\b(toutes|tous) (les|vos) (factures|donnees|fiches)\b.{0,40}\b(patients|clients)\b",
    r"\b(list|export|database|dump)\b.{0,30}\b(patients?|customers?|records)\b",
    r"\ball (of )?(your |the )?(patients|records|patient data|patient files)\b",
    r"\b(patientenliste|patientendaten|alle (ihre |ihrer )?patienten|patientenakten)\b",
    r"\b(lista|listagem|base de dados)\b.{0,30}\b(pacientes|clientes)\b", r"\btodos os (pacientes|clientes)\b",
    r"\blescht vun (all|den|de) patienten\b", r"\ball (d')?patienten\b",
)

DEMANDE_DONNEES = re.compile(
    r"\b(envoye[zr]?|transmett\w*|communique[zr]?|fourni[sr]\w*|send|provide|forward|share|senden|schicken|"
    r"ubermitteln|envi[ae]\w*|mand[ae]\w*|scheckt)\b.{0,80}\b(liste|donnees|fichiers?|factures|dossiers|data|"
    r"records|list|daten|dados|lista|faturas|mot de passe|password|passwort|senha|identifiants|credentials|"
    r"iban|rib|coordonnees bancaires)\b|https?://|\bcliquez\b|\bclick here\b|\bklicken sie\b|\bclique aqui\b")

# Organismes souvent usurpés, et domaines officiels correspondants.
_JETONS_AUTORITE = {
    "cns", "ccss", "secu", "cmcm", "caisse", "impots", "acd", "gouv", "gouvernement", "police",
    "ministere", "sante", "doctena", "dentagest", "luxtrust", "spuerkeess", "bcee", "bgl", "bil",
    "raiffeisen", "banque", "bank",
}
_JETONS_LEURRE = {
    "secure", "securise", "securite", "verification", "verify", "update", "maj", "remboursement",
    "refund", "login", "account", "compte", "alert", "alerte", "online", "portal", "portail", "audit",
    "confirm", "confirmation", "validation", "support", "admin",
}
_DOMAINES_OFFICIELS = (
    "cns.lu", "secu.lu", "ccss.lu", "cmcm.lu", "public.lu", "etat.lu", "gouvernement.lu", "sante.lu",
    "doctena.com", "doctena.lu", "luxtrust.lu", "spuerkeess.lu", "bgl.lu", "bil.com", "raiffeisen.lu",
)


def analyser_expediteur(adresse: str) -> list[str]:
    """Raisons de penser que l'expéditeur usurpe un organisme (liste vide sinon)."""
    if "@" not in adresse:
        return ["adresse d'expéditeur invalide"]
    local, _, domaine = adresse.rpartition("@")
    if any(domaine == d or domaine.endswith("." + d) for d in _DOMAINES_OFFICIELS):
        return []
    jetons = set(re.split(r"[^a-z0-9]+", local + "." + domaine.rsplit(".", 1)[0]))
    autorites = sorted(jetons & _JETONS_AUTORITE)
    if not autorites:
        return []
    raisons = [f"se présente comme « {', '.join(a.upper() for a in autorites)} » mais écrit depuis "
               f"un domaine non officiel ({domaine})"]
    leurres = sorted(jetons & _JETONS_LEURRE)
    if leurres:
        raisons.append(f"domaine construit pour inspirer confiance ({', '.join(leurres)})")
    return raisons


# ======================================================================
# Publicité, messages automatiques
# ======================================================================

PUBLICITE = _c(
    r"\boffres?\b", r"\bpromo", r"\bremises?\b", r"\breductions?\b", r"-\s?\d{1,2}\s?%",
    r"\d{1,2}\s?% (de )?(reduction|remise|off|rabatt|desconto)", r"\bsoldes\b", r"\bcommandez\b",
    r"\bnewsletter", r"\b(se )?desabonner|desinscri|unsubscribe|abmelden", r"\bwebinai?re?s?\b",
    r"\bdiscount", r"\bspecial offer", r"\blimited time", r"\bangebot", r"\brabatt", r"\boferta",
    r"\bdesconto", r"\bpromocao", r"\bexclusi(f|ve|vement)\b", r"\breservee? aux (cabinets|professionnels)",
    r"\bjusqu'(a|au) (vendredi|lundi|dimanche|samedi|la fin)", r"\b(achetez|buy now|order now|jetzt bestellen|compre ja)\b",
    r"\b(gamme|catalogue|tarifs? prefer\w*|prix (cass|imbattable))\b",
)
_PUBLICITE_EXPEDITEUR = re.compile(r"(^|[._-])(promo|promotions?|marketing|newsletter|news|offers?|deals|sales|commercial)([._@-]|$)")

AUTOMATIQUE_SUJET = re.compile(
    r"^\s*(re\s*:\s*)?(reponse automatique|automatic reply|auto[- ]?reply|out of (the )?office|"
    r"absen(ce|t|te) (du|de) bureau|abwesenheitsnotiz|automatische antwort|resposta automatica|"
    r"ausencia do escritorio|undeliverable|undelivered|"
    r"delivery status notification|non remis|unzustellbar|mail delivery failed|accuse de reception|"
    r"read receipt|lu ?:|gelesen ?:)")
AUTOMATIQUE_EXPEDITEUR = re.compile(r"^(mailer-daemon|postmaster|no-?reply|ne-?pas-?repondre|donotreply|do-not-reply|notifications?|bounce)@")


# ======================================================================
# Synthèse
# ======================================================================

@dataclass
class Signaux:
    signes_forts: list[str] = field(default_factory=list)
    signes_faibles: list[str] = field(default_factory=list)
    contexte_medical: bool = False
    question_medicale: bool = False
    injection: list[str] = field(default_factory=list)
    donnees_en_masse: list[str] = field(default_factory=list)
    usurpation: list[str] = field(default_factory=list)
    demande_donnees: bool = False
    score_publicite: int = 0
    automatique: bool = False
    autres_adresses: list[str] = field(default_factory=list)

    @property
    def urgence(self) -> str:
        if self.signes_forts and (self.contexte_medical or self.question_medicale):
            return "probable" if len(self.signes_forts) >= 2 else "possible"
        if "mention d'urgence" in self.signes_faibles and self.question_medicale:
            return "possible"
        if self.signes_forts or ("engourdissement" in self.signes_faibles and self.contexte_medical):
            return "signal"
        return "aucune"

    @property
    def suspicion(self) -> str:
        if self.injection or self.donnees_en_masse:
            return "certain"
        if self.usurpation and self.demande_donnees:
            return "certain"
        if self.usurpation:
            return "possible"
        return "aucun"

    def raisons_suspicion(self) -> list[str]:
        raisons = []
        if self.injection:
            raisons.append("consignes adressées à l'IA / au « système » cachées dans le message")
        if self.donnees_en_masse:
            raisons.append("demande de données de patients en masse")
        raisons.extend(self.usurpation)
        if self.usurpation and self.demande_donnees:
            raisons.append("demande d'envoi de données ou lien à suivre")
        return raisons


def _extraits(motifs: list[re.Pattern], texte: str) -> list[str]:
    trouves = []
    for motif in motifs:
        m = motif.search(texte)
        if m:
            trouves.append(m.group(0)[:80])
    return trouves


def detecter(expediteur: str, sujet: str, texte: str) -> Signaux:
    plie = replier(f"{sujet}\n{texte}")
    s = Signaux()
    s.signes_forts = [nom for nom, motifs in SIGNES_FORTS.items() if any(m.search(plie) for m in motifs)]
    s.signes_faibles = [nom for nom, motifs in SIGNES_FAIBLES.items() if any(m.search(plie) for m in motifs)]
    s.contexte_medical = bool(CONTEXTE_MEDICAL.search(plie))
    symptome = bool(SYMPTOMES.search(plie))
    question = bool(QUESTIONS_MEDICALES.search(plie))
    medicament = bool(MEDICAMENTS.search(plie))
    apres_soin = bool(APRES_SOIN.search(plie))
    s.question_medicale = ((symptome and (question or s.contexte_medical or medicament or apres_soin))
                           or (medicament and question) or (question and apres_soin))
    s.injection = _extraits(INJECTION, plie)
    s.donnees_en_masse = _extraits(DONNEES_EN_MASSE, plie)
    s.usurpation = analyser_expediteur(expediteur)
    s.demande_donnees = bool(DEMANDE_DONNEES.search(plie))
    s.score_publicite = sum(1 for m in PUBLICITE if m.search(plie))
    if _PUBLICITE_EXPEDITEUR.search(expediteur):
        s.score_publicite += 1
    s.automatique = bool(AUTOMATIQUE_SUJET.search(replier(sujet)) or AUTOMATIQUE_EXPEDITEUR.search(expediteur))
    s.autres_adresses = [a for a in adresses_citees(texte) if a != expediteur]
    return s
