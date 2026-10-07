"""Décisions métier — 100 % code, aucune part de LLM.

À partir de l'analyse (ce que dit le mail) et du dossier (ce que sait le cabinet), décide :
- qui écrit, et de qui parle le mail ;
- quels documents peuvent être joints (autorisation.verifier, règle 3) ;
- quels blocs de texte pré-validés composent la réponse, et dans quelle langue ;
- la priorité, la catégorie, ce qui reste à compléter, et les notes pour le secrétariat.

Aucune donnée du dossier n'entre dans la réponse sans autorisation : chaque bloc qui en
contient (date de rendez-vous, numéro de facture) porte l'identifiant du dossier concerné,
et les garde-fous revérifient l'autorisation avant l'écriture du brouillon.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from . import autorisation
from .connaissances import TARIFS
from .analyse_regles import CONTENU_DOSSIER
from .modeles import LANGUES, Analyse, DateFloue, Facture, Mail, Patient, RendezVous
from .normalisation import replier

LIBELLES = {
    "question_medicale": "question médicale", "demande_facture": "facture", "demande_attestation": "attestation",
    "rendez_vous": "rendez-vous", "question_facturation": "facturation", "question_tarif": "tarif",
    "information_pratique": "information", "reclamation": "réclamation", "administratif": "administratif",
    "professionnel": "professionnel", "publicite": "publicité", "message_automatique": "message automatique",
    "remerciement": "remerciement", "autre": "autre",
}
ORDRE_CATEGORIES = list(LIBELLES)
ORDRE_ACTIONS = ["annuler", "deplacer", "confirmer", "retard", "rdv_manque", "prendre", "indetermine"]
SANS_REPONSE = {
    "publicite": ("publicité", "Démarchage commercial : aucune réponse nécessaire (à transmettre au praticien "
                               "s'il peut l'intéresser, sinon à archiver)."),
    "message_automatique": ("message automatique", "Message automatique (absence, notification, accusé de "
                                                   "réception) : aucune réponse nécessaire."),
    "remerciement": ("remerciement", "Simple remerciement : aucune réponse nécessaire."),
    "professionnel": ("professionnel", "Message d'un professionnel ou d'un organisme : à transmettre au praticien "
                                       "concerné ou à traiter par le cabinet (aucune réponse automatique)."),
}
PERSONNES_TIERCES = ("conjoint", "enfant", "parent", "autre_personne")
LIBELLES_PERSONNE = {"conjoint": "conjoint(e)", "enfant": "enfant", "parent": "parent",
                     "autre_personne": "autre personne"}


@dataclass
class Bloc:
    cle: str
    params: dict = field(default_factory=dict)
    patient_id: int | None = None      # dossier dont ce bloc expose des données (date, n° de facture)
    tarif: bool = False                # tarifs généraux : vocabulaire de soins autorisé
    a_completer: str | None = None     # raison, si le secrétariat doit compléter ce paragraphe


@dataclass
class PieceJointe:
    type: str                          # "facture" | "attestation"
    patient_id: int
    chemin: str
    libelle: str
    rdv: RendezVous | None = None


@dataclass
class Decision:
    destinataire: str
    langue: str = "fr"
    langue_raison: str = ""
    intentions: list[str] = field(default_factory=list)
    categorie: str = ""
    priorite: str = "normale"
    sans_reponse: bool = False
    nom_salutation: str | None = None
    blocs: list[Bloc] = field(default_factory=list)
    pieces: list[PieceJointe] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    drapeaux: list[str] = field(default_factory=list)
    patient_expediteur: Patient | None = None
    personne_concernee: Patient | None = None
    alerte: str | None = None

    @property
    def a_completer(self) -> bool:
        return any(b.a_completer for b in self.blocs)


# ----------------------------------------------------------------------
# Sélection dans le dossier
# ----------------------------------------------------------------------

def decouper_nom(nom_complet: str) -> tuple[str, str]:
    morceaux = (nom_complet or "").split()
    if not morceaux:
        return "", ""
    return morceaux[0], " ".join(morceaux[1:])


def choisir_factures(factures: list[Facture], a: Analyse, ref: date) -> tuple[list[Facture], str]:
    """Factures correspondant à la demande, et explication éventuelle pour la note."""
    if not factures:
        return [], ""
    if a.facture_numero:
        return [f for f in factures if f.numero.upper() == a.facture_numero], ""
    passees = [f for f in factures if f.date_facture <= ref] or factures
    if a.toutes_factures:
        retenues = [f for f in passees if not a.periode_annee or f.date_facture.year == a.periode_annee]
        return retenues, ""
    jours = [d for d in a.dates if d.jour]
    exactes = [f for f in passees if any(d.correspond(f.date_facture) for d in jours)]
    if exactes:
        return exactes, ""
    if a.periode_mois or a.periode_annee:
        retenues = [f for f in passees
                    if (not a.periode_mois or f.date_facture.month == a.periode_mois)
                    and (not a.periode_annee or f.date_facture.year == a.periode_annee)]
        if a.periode_mois and not a.periode_annee and retenues:
            annee = max(f.date_facture.year for f in retenues)       # « de septembre » : le plus récent
            retenues = [f for f in retenues if f.date_facture.year == annee]
        return retenues, ""
    if len(passees) > 1:
        return passees[:1], (f"Aucune période précisée et {len(passees)} factures au dossier : la plus récente "
                             "a été jointe — vérifier que c'est la bonne.")
    return passees[:1], ""


def selectionner_rdv(rdvs: list[RendezVous], a: Analyse, ref: date, sens: str) -> list[RendezVous]:
    """Rendez-vous visés par le mail. sens = "futur" (à déplacer...) ou "passe" (attestation, absence)."""
    if sens == "futur":
        pool = [r for r in rdvs if r.debut.date() >= ref and r.statut == "prévu"]
    else:
        pool = [r for r in rdvs if r.debut.date() <= ref]
    jours = [d for d in a.dates if d.jour]
    if jours:
        exacts = [r for r in pool if any(d.correspond(r.debut.date()) for d in jours)]
        if not exacts:   # année absente ou erronée : on tolère jour + mois
            exacts = [r for r in pool if any(DateFloue(d.jour, d.mois).correspond(r.debut.date()) for d in jours)]
        if exacts:
            return exacts
    if a.plage:
        dans = [r for r in pool if a.plage[0] <= r.debut.date() <= a.plage[1]]
        if dans:
            return dans
    if jours or a.plage:
        return []
    if sens == "futur":
        return pool
    return pool[-1:]


# ----------------------------------------------------------------------
# Décideur
# ----------------------------------------------------------------------

class _Decideur:
    def __init__(self, mail: Mail, a: Analyse, dossier, ref: date):
        self.mail, self.a, self.dossier, self.ref = mail, a, dossier, ref
        self.d = Decision(destinataire=mail.expediteur, intentions=list(a.intentions) or ["autre"])
        self.exp: Patient | None = None
        self.concerne: Patient | None = None
        self.urgent = a.urgence in ("possible", "probable")
        self.suspect = a.suspect
        self.refus_ajoute = False
        self.imminent = False
        self.prendre_rdv = False

    def verdict(self, patient: Patient | None) -> autorisation.Verdict:
        return autorisation.verifier(self.mail, patient, self.dossier, self.ref)

    # ------------------------------------------------------------ point d'entrée
    def executer(self) -> Decision:
        d, a = self.d, self.a
        self.exp = self.dossier.patient_par_email(self.mail.expediteur)
        d.patient_expediteur = self.exp
        if self.exp:
            for i in ("publicite", "professionnel"):     # un patient connu n'est ni un démarcheur ni un confrère
                if i in d.intentions and len(d.intentions) > 1:
                    d.intentions.remove(i)
        self.concerne = self._identifier_concerne()
        d.personne_concernee = self.concerne
        d.langue, d.langue_raison = self._choisir_langue()
        self._noter_contexte()

        if not self.urgent:
            if self.suspect == "certain":
                raisons = "; ".join(a.raisons_suspect or ["voir le message"])
                if self.exp:
                    consigne = (f"MESSAGE SUSPECT ({raisons}), envoyé depuis l'adresse d'un patient (boîte mail "
                                "peut-être piratée) : aucune réponse automatique, rien à envoyer. Traiter "
                                "manuellement après avoir vérifié par téléphone, au numéro du dossier.")
                else:
                    consigne = (f"MESSAGE SUSPECT ({raisons}) : ne pas répondre, ne rien envoyer, ne cliquer sur "
                                "aucun lien. Le signaler au responsable informatique puis le supprimer.")
                return self._sans_reponse("suspect", "basse", consigne)
            for intention, (categorie, note) in SANS_REPONSE.items():
                if intention in d.intentions and set(d.intentions) <= set(SANS_REPONSE):
                    return self._sans_reponse(categorie, "normale" if intention == "professionnel" else "basse", note)

        d.nom_salutation = self.exp.nom_complet if self.exp else None
        if self.urgent:
            self._urgence()
            if self.suspect == "certain":       # message suspect mais signes d'urgence : consigne de sécurité seule
                d.notes.append("Message suspect contenant des signes d'urgence : seule la consigne d'appeler le "
                               "cabinet / le 112 est proposée, sans aucune donnée.")
                return self._finaliser()
        else:
            d.blocs.append(Bloc("intro"))
        if self.suspect == "possible":
            d.drapeaux.append("suspect_possible")
            d.notes.append("⚠ Message jugé potentiellement suspect (" + "; ".join(a.raisons_suspect or ["?"])
                           + ") : aucun document n'est joint ; vérifier l'expéditeur avant de répondre.")

        intentions = d.intentions
        if "demande_facture" in intentions:
            self._facture()
        if "demande_attestation" in intentions:
            self._attestation()
        if "rendez_vous" in intentions:
            self._rendez_vous()
        if "question_facturation" in intentions:
            self._facturation()
        if "question_tarif" in intentions:
            self._tarif()
        if "information_pratique" in intentions:
            self._infos()
        if (a.question_medicale or "question_medicale" in intentions) and not self.urgent:
            self._question_medicale()
        if "reclamation" in intentions:
            d.blocs.append(Bloc("reclamation"))
            d.actions.append("Réclamation : transmettre au Dr Reuter.")
        contenu_dossier = bool(CONTENU_DOSSIER.search(replier(self.mail.texte)))
        if contenu_dossier:      # règle 4 : avertissement quelle que soit la façon dont la demande a été classée
            d.drapeaux.append("demande_contenu_dossier")
            d.notes.append("⚠ Demande portant sur le contenu du dossier (soins, radiographies, copie du dossier) : "
                           "ne rien en écrire dans l'e-mail ; à faire valider par le praticien, remise en main propre "
                           "ou envoi sécurisé après vérification d'identité.")
        if "administratif" in intentions:
            d.blocs.append(Bloc("administratif", a_completer="traiter la demande administrative (voir le message)"))
            if not contenu_dossier:
                d.notes.append("Ne modifier aucune coordonnée (adresse e-mail notamment) sans vérification d'identité "
                               "par téléphone, au numéro enregistré dans le dossier.")
        if (self.prendre_rdv and not self.urgent
                and not any(b.cle in ("rdv_prendre", "info_rdv_en_ligne") for b in d.blocs)):
            d.blocs.append(Bloc("rdv_prendre"))
        if not [b for b in d.blocs if b.cle not in ("intro",)]:
            d.blocs.append(Bloc("autre", a_completer="réponse à rédiger : demande non reconnue automatiquement"))
        return self._finaliser()

    # ------------------------------------------------------------ identification
    def _identifier_concerne(self) -> Patient | None:
        a, d = self.a, self.d
        if a.personne_concernee not in PERSONNES_TIERCES:
            if self.exp:
                return self.exp
            prenom, nom = decouper_nom(a.nom_signature)
            candidats = self.dossier.chercher_par_nom(prenom, nom) if prenom and nom else []
            if len(candidats) == 1:
                p = candidats[0]
                d.drapeaux.append("identite_non_verifiee")
                d.notes.append(f"Expéditeur inconnu, mais un dossier au nom signé ({p.nom_complet}, n° {p.id}) existe "
                               "avec une autre adresse e-mail : vérifier l'identité par téléphone avant tout envoi.")
                return p
            return None
        prenom, nom = a.prenom_concerne, a.nom_concerne
        if prenom and not nom and " " in prenom:
            prenom, nom = decouper_nom(prenom)
        relation = LIBELLES_PERSONNE.get(a.personne_concernee, a.personne_concernee)
        if not prenom and not nom:
            d.notes.append(f"La demande concerne un tiers ({relation}) non nommé : dossier non identifié.")
            return None
        familles = [nom] if nom else [x for x in ((self.exp.nom if self.exp else ""),
                                                  decouper_nom(a.nom_signature)[1]) if x]
        candidats: list[Patient] = []
        for famille in familles:
            candidats = self.dossier.chercher_par_nom(prenom, famille)
            if candidats:
                break
        if len(candidats) == 1:
            p = candidats[0]
            age = f", {p.age(self.ref)} ans" + (" — MINEUR" if p.est_mineur(self.ref) else "")
            d.notes.append(f"La demande concerne un tiers ({relation}) : {p.nom_complet} (dossier n° {p.id}{age}).")
            return p
        if len(candidats) > 1:
            d.notes.append(f"La demande concerne un tiers ({relation}) « {prenom} {nom} » : plusieurs dossiers "
                           "possibles, aucun retenu.")
        else:
            d.notes.append(f"La demande concerne un tiers ({relation}) « {(prenom + ' ' + nom).strip()} » : "
                           "aucun dossier correspondant trouvé.")
        return None

    def _choisir_langue(self) -> tuple[str, str]:
        if self.a.langue in LANGUES:
            return self.a.langue, "langue du message"
        for p in (self.exp, self.concerne):
            if p and p.langue in LANGUES:
                self.d.drapeaux.append("langue_incertaine")
                return p.langue, "langue du dossier (langue du message non reconnue)"
        self.d.drapeaux.append("langue_incertaine")
        nom = {"it": "italien", "es": "espagnol", "nl": "néerlandais"}.get(self.a.langue or "", "")
        self.d.actions.append(f"Message en {nom}, langue non prise en charge" if nom else
                              "Langue du message non reconnue")
        self.d.actions[-1] += " : réponse préparée en français, à adapter si nécessaire."
        return "fr", "français par défaut (langue du message non prise en charge)"

    def _noter_contexte(self) -> None:
        d = self.d
        if self.exp:
            d.notes.insert(0, f"Expéditeur : {self.exp.nom_complet} (dossier n° {self.exp.id}), adresse enregistrée.")
            if self.exp.langue != d.langue and d.langue_raison == "langue du message":
                d.notes.append(f"Langue enregistrée au dossier : {self.exp.langue} ; réponse rédigée dans la langue "
                               f"du message ({d.langue}).")
        else:
            d.notes.insert(0, "Expéditeur inconnu : aucune fiche patient avec cette adresse e-mail.")
        if self.mail.repondre_a and self.mail.repondre_a != self.mail.expediteur:
            d.drapeaux.append("repondre_a_different")
            d.notes.append(f"⚠ L'en-tête « Répondre à » ({self.mail.repondre_a}) diffère de l'expéditeur : répondre "
                           f"uniquement à {self.mail.expediteur}.")

    # ------------------------------------------------------------ urgence
    def _urgence(self) -> None:
        d, a = self.d, self.a
        autorise = self.concerne is not None and self.verdict(self.concerne).autorise
        telephone = self.concerne.telephone if self.concerne else None
        d.blocs.append(Bloc("urgence", {"rappel": bool(autorise and telephone)}))
        signes = ", ".join(a.signes_urgence) or "voir le message"
        action = f"URGENCE POSSIBLE ({signes}) : prévenir immédiatement un praticien"
        if telephone:
            action += f" et rappeler {self.concerne.nom_complet} au {telephone} (numéro du dossier)"
        d.actions.insert(0, action + ".")
        praticien = self._dernier_praticien()
        if praticien:
            d.notes.append(f"Dernier rendez-vous effectué : {praticien}.")
        d.drapeaux.append("urgence")
        d.alerte = f"Urgence possible — {self.mail.expediteur} — « {self.mail.sujet} » — signes : {signes}"

    def _dernier_praticien(self) -> str:
        if not self.concerne:
            return ""
        effectues = [r for r in self.dossier.rendez_vous(self.concerne.id)
                     if r.statut == "effectué" and r.debut.date() <= self.ref]
        if not effectues:
            return ""
        r = effectues[-1]
        return f"{r.praticien}, le {r.debut:%d/%m/%Y}"

    # ------------------------------------------------------------ documents
    def _refuser_document(self, cible: Patient | None, verdict: autorisation.Verdict, nature: str) -> None:
        d, a = self.d, self.a
        if not self.refus_ajoute and "repondre_a_different" in d.drapeaux and cible is not None and cible == self.exp:
            cle = "facture_a_verifier" if nature == "facture" else "attestation_a_verifier"
            d.blocs.append(Bloc(cle, a_completer="en-tête « Répondre à » suspect : confirmer la demande par "
                                                 "téléphone avant d'envoyer le document"))
            self.refus_ajoute = True
        if not self.refus_ajoute:
            mineur = (cible is not None and cible.est_mineur(self.ref)) or a.personne_concernee == "enfant"
            if mineur:
                cle = "doc_refus_mineur"
            elif cible is not None and self.exp is not None and cible.id == self.exp.id:
                cle = "doc_refus_adresse"
            elif self.exp is None and a.personne_concernee not in PERSONNES_TIERCES:
                cle = "doc_refus_adresse"
            else:
                cle = "doc_refus_tiers"
            d.blocs.append(Bloc(cle))
            self.refus_ajoute = True
        if "document_refuse" not in d.drapeaux:
            d.drapeaux.append("document_refuse")
        qui = (f"{cible.nom_complet} (dossier n° {cible.id}{', mineur' if cible.est_mineur(self.ref) else ''})"
               if cible else "personne non identifiée")
        d.notes.append(f"{nature.capitalize()} NON jointe : {verdict.raison}. Personne concernée : {qui}.")
        if verdict.adresses_autorisees:
            d.notes.append("Seule(s) adresse(s) autorisée(s) pour ce dossier : " + ", ".join(verdict.adresses_autorisees)
                           + ". Si nécessaire, envoyer le document par un message séparé à cette adresse.")

    def _facture(self) -> None:
        d, a = self.d, self.a
        cible = self.concerne
        if a.facture_numero:
            f = self.dossier.facture(a.facture_numero)
            if f is None:
                d.notes.append(f"Le numéro de facture cité ({a.facture_numero}) n'existe pas dans le logiciel.")
            elif cible is None or f.patient_id != cible.id:
                if cible is not None:
                    d.drapeaux.append("facture_autre_dossier")
                    d.notes.append(f"⚠ La facture {f.numero} citée appartient à un autre dossier que celui de la "
                                   "personne concernée.")
                cible = self.dossier.patient(f.patient_id)
        verdict = self.verdict(cible)
        if not verdict.autorise:
            self._refuser_document(cible, verdict, "facture")
            if cible is not None:
                trouvees, _ = choisir_factures(self.dossier.factures(cible.id), a, self.ref)
                if trouvees:
                    d.notes.append("Facture(s) correspondant à la demande dans ce dossier : "
                                   + ", ".join(f"{f.numero} du {f.date_facture:%d/%m/%Y}" for f in trouvees) + ".")
            return
        factures, explication = choisir_factures(self.dossier.factures(cible.id), a, self.ref)
        if not factures:
            d.blocs.append(Bloc("facture_a_verifier", a_completer="aucune facture ne correspond à la demande dans le "
                                                                  "logiciel : vérifier et joindre la bonne facture"))
            d.notes.append("Aucune facture trouvée pour la période demandée.")
            return
        if self.suspect != "aucun":
            d.blocs.append(Bloc("facture_a_verifier", a_completer="message jugé potentiellement suspect : vérifier la "
                                                                  "demande avant de joindre la facture"))
            d.notes.append("Facture(s) identifiée(s) mais NON jointe(s) par prudence : "
                           + ", ".join(f.numero for f in factures) + ".")
            return
        for f in factures:
            d.pieces.append(PieceJointe("facture", cible.id, f.fichier_pdf,
                                        f"facture {f.numero} du {f.date_facture:%d/%m/%Y}"))
        if len(factures) == 1:
            d.blocs.append(Bloc("facture_jointe", {"numero": factures[0].numero, "date": factures[0].date_facture},
                                patient_id=cible.id))
        else:
            d.blocs.append(Bloc("factures_jointes", {"factures": [(f.numero, f.date_facture) for f in factures]},
                                patient_id=cible.id))
        if explication:
            d.notes.append(explication)
        if any(f.statut == "en attente" for f in factures):
            d.notes.append("Facture jointe encore en attente de paiement.")
        self._redirection()

    def _attestation(self) -> None:
        d, a = self.d, self.a
        if a.type_attestation == "medicale":
            d.blocs.append(Bloc("attestation_medicale"))
            d.actions.append("Transmettre la demande de certificat médical au praticien (le système ne prépare que "
                             "des attestations de présence).")
            return
        cible = self.concerne
        verdict = self.verdict(cible)
        if not verdict.autorise:
            self._refuser_document(cible, verdict, "attestation")
            return
        candidats = selectionner_rdv(self.dossier.rendez_vous(cible.id), a, self.ref, "passe")
        effectues = [r for r in candidats if r.statut == "effectué"]
        if len(effectues) == 1 and self.suspect == "aucun":
            r = effectues[0]
            chemin = f"attestations/{r.debut:%Y}/ATT-{r.debut:%Y%m%d}-P{cible.id:04d}-R{r.id}.pdf"
            d.pieces.append(PieceJointe("attestation", cible.id, chemin,
                                        f"attestation de présence du {r.debut:%d/%m/%Y}", rdv=r))
            d.blocs.append(Bloc("attestation_jointe", {"date": r.debut.date()}, patient_id=cible.id))
            d.actions.append("Vérifier, signer et tamponner l'attestation jointe avant l'envoi.")
            self._redirection()
            return
        a_venir = [r for r in selectionner_rdv(self.dossier.rendez_vous(cible.id), a, self.ref, "futur")
                   if any(d_.jour for d_ in a.dates)]
        if candidats and not effectues:
            statuts = ", ".join(f"{r.debut:%d/%m/%Y} : {r.statut}" for r in candidats)
            raison = f"aucun rendez-vous « effectué » à cette date ({statuts}) : pas d'attestation possible"
        elif not effectues and len(a_venir) == 1:
            raison = (f"le rendez-vous du {a_venir[0].debut:%d/%m/%Y} n'a pas encore eu lieu : l'attestation ne "
                      "pourra être établie qu'après")
        elif len(effectues) > 1:
            raison = "plusieurs rendez-vous possibles : préciser la date"
        elif self.suspect != "aucun":
            raison = "message jugé potentiellement suspect : vérifier avant d'établir l'attestation"
        else:
            raison = "aucun rendez-vous effectué ne correspond à la date indiquée"
        d.blocs.append(Bloc("attestation_a_verifier", a_completer=raison))
        d.notes.append(f"Attestation non préparée : {raison}.")

    def _redirection(self) -> None:
        adresse = self.a.envoi_autre_adresse
        if adresse and adresse != self.mail.expediteur:
            if not any(b.cle == "doc_redirection" for b in self.d.blocs):
                self.d.blocs.append(Bloc("doc_redirection"))
            self.d.notes.append(f"Demande d'envoi vers une autre adresse ({adresse}) : refusée, le document part "
                                "uniquement à l'adresse enregistrée.")

    # ------------------------------------------------------------ rendez-vous
    def _rendez_vous(self) -> None:
        d, a = self.d, self.a
        actions = [x for x in a.actions_rdv if x in ORDRE_ACTIONS] or ["indetermine"]
        if "deplacer" in actions and "annuler" in actions:
            actions.remove("annuler")                   # déplacer implique de libérer l'ancien créneau
        cible = self.concerne
        verdict = self.verdict(cible)
        autorise = verdict.autorise and self.suspect == "aucun"
        neutre_ajoute = False
        for action in sorted(set(actions), key=ORDRE_ACTIONS.index):
            if action == "prendre":
                self.prendre_rdv = True          # bloc ajouté en fin de réponse (après facturation, tarifs...)
                continue
            if action == "retard":
                d.blocs.append(Bloc("rdv_retard", a_completer="indiquer si le rendez-vous peut être maintenu"))
                self.imminent = True
                continue
            if action == "indetermine":
                if autorise:
                    d.blocs.append(Bloc("rdv_a_verifier", a_completer="demande de rendez-vous à préciser"))
                elif not neutre_ajoute:
                    d.blocs.append(Bloc("rdv_neutre"))
                    neutre_ajoute = True
                    d.notes.append(f"Demande de rendez-vous : aucun détail communiqué ({verdict.raison}).")
                continue
            if action == "rdv_manque":
                absents = []
                if autorise:
                    absents = [r for r in selectionner_rdv(self.dossier.rendez_vous(cible.id), a, self.ref, "passe")
                               if r.statut == "absent"]
                if len(absents) == 1:
                    r = absents[0]
                    d.blocs.append(Bloc("rdv_manque", {"date": r.debut.date()}, patient_id=cible.id))
                    d.notes.append(f"Rendez-vous manqué : {r.debut:%d/%m/%Y %H:%M} ({r.praticien}), marqué « absent » "
                                   "dans l'agenda.")
                else:
                    d.blocs.append(Bloc("rdv_manque_sans_date"))
                continue
            # déplacer, annuler, confirmer : il faut pouvoir parler du rendez-vous
            if not autorise:
                if not neutre_ajoute:
                    d.blocs.append(Bloc("rdv_neutre"))
                    neutre_ajoute = True
                d.notes.append(f"Demande de rendez-vous ({action}) : aucun détail communiqué ({verdict.raison}).")
                continue
            candidats = selectionner_rdv(self.dossier.rendez_vous(cible.id), a, self.ref, "futur")
            if len(candidats) != 1:
                raison = ("aucun rendez-vous à venir ne correspond à la demande" if not candidats
                          else "plusieurs rendez-vous à venir : préciser lequel")
                d.blocs.append(Bloc("rdv_a_verifier", a_completer=raison))
                d.notes.append(f"Rendez-vous non identifié ({action}) : {raison}.")
                continue
            r = candidats[0]
            d.blocs.append(Bloc(f"rdv_{action}", {"date": r.debut.date(), "heure": r.debut}, patient_id=cible.id))
            d.notes.append(f"Rendez-vous concerné : {r.debut:%d/%m/%Y à %H:%M}, durée {r.duree_min} min, {r.praticien} "
                           f"(n° {r.id}).")
            if action == "deplacer":
                d.actions.append(f"Proposer un nouveau créneau de {r.duree_min} min avec {r.praticien}, puis libérer "
                                 "l'ancien dans l'agenda (et Doctena).")
            elif action == "annuler":
                d.actions.append("Annuler le rendez-vous dans l'agenda (et Doctena) avant d'envoyer la réponse.")
            delai = (r.debut.date() - self.ref).days
            if delai <= 1 and action in ("deplacer", "annuler"):
                d.notes.append("Moins de 24 h avant le rendez-vous (le cabinet demande de prévenir 24 h à l'avance) : "
                               "à voir avec le praticien.")
            if delai <= 2:
                self.imminent = True

    # ------------------------------------------------------------ questions
    def _facturation(self) -> None:
        if "rdv_manque" in self.a.actions_rdv:
            raison = ("indiquer si le rendez-vous manqué sera facturé : cette règle ne figure pas dans les "
                      "informations du cabinet")
        else:
            raison = "répondre à la question de facturation (information non disponible automatiquement)"
        self.d.blocs.append(Bloc("facturation", a_completer=raison))

    def _tarif(self) -> None:
        d, a = self.d, self.a
        connus = [x for x in a.actes_tarif if x in TARIFS]
        if connus:
            d.blocs.append(Bloc("tarif", {"actes": connus}, tarif=True))
        if "autre_acte" in a.actes_tarif:
            d.blocs.append(Bloc("tarif_autre_acte", tarif=True))
            d.notes.append("Tarif demandé pour un acte absent de la grille : réponse générique (devis après "
                           "consultation).")
        if not a.actes_tarif and not a.question_remboursement:
            d.blocs.append(Bloc("tarif", {"actes": list(TARIFS)}, tarif=True))
        if a.question_remboursement:
            d.blocs.append(Bloc("remboursement", tarif=True))
        if self.exp is None:
            self.prendre_rdv = True              # futur patient : comment prendre rendez-vous

    def _infos(self) -> None:
        d = self.d
        correspondance = {"horaires": "info_horaires", "adresse": "info_adresse", "telephone": "info_telephone",
                          "rdv_en_ligne": "info_rdv_en_ligne", "urgences": "info_urgences",
                          "annulation": "info_annulation"}
        deja = {b.cle for b in d.blocs}
        for info in self.a.infos_demandees or ["autre_info"]:
            cle = correspondance.get(info)
            if cle and cle not in deja:
                d.blocs.append(Bloc(cle))
                deja.add(cle)
            elif not cle:
                d.blocs.append(Bloc("info_autre", a_completer="information absente de la fiche du cabinet : à "
                                                              "compléter (ne rien inventer)"))

    def _question_medicale(self) -> None:
        self.d.blocs.append(Bloc("question_medicale"))
        praticien = self._dernier_praticien()
        self.d.actions.append("Transmettre la question médicale à l'équipe soignante"
                              + (f" (dernier rendez-vous : {praticien})" if praticien else "")
                              + " ; aucune réponse médicale par e-mail.")

    # ------------------------------------------------------------ fin
    def _sans_reponse(self, categorie: str, priorite: str, note: str) -> Decision:
        d = self.d
        d.sans_reponse, d.categorie, d.priorite = True, categorie, priorite
        d.blocs, d.pieces = [], []
        d.notes.insert(0, note)
        if categorie == "suspect":
            d.drapeaux.append("suspect")
        return d

    def _finaliser(self) -> Decision:
        d, a = self.d, self.a
        intentions = sorted(set(d.intentions), key=ORDRE_CATEGORIES.index)
        libelles = [LIBELLES[i] for i in intentions]
        if self.urgent:
            libelles = ["urgence médicale"] + [l for l in libelles if l != "question médicale"]
        if self.suspect == "certain":
            libelles = ["suspect"] + libelles
        d.categorie = " + ".join(libelles)
        if self.urgent:
            d.priorite = "urgente"
        elif (a.urgence == "signal" or "question_medicale" in intentions or "reclamation" in intentions
              or self.imminent):
            d.priorite = "haute"
        elif set(intentions) <= {"publicite", "message_automatique", "remerciement"}:
            d.priorite = "basse"
        else:
            d.priorite = "normale"
        if a.urgence == "signal":
            d.notes.append(f"Mot d'alerte repéré ({', '.join(a.signes_urgence)}) sans contexte médical confirmé : "
                           "vérifier qu'il ne s'agit pas d'une urgence.")
        return d


def decider(mail: Mail, analyse: Analyse, dossier, ref: date) -> Decision:
    return _Decideur(mail, analyse, dossier, ref).executer()
