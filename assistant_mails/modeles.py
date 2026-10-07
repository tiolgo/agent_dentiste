"""Objets métier partagés par tous les modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime

LANGUES = ("fr", "de", "en", "pt", "lb")

INTENTIONS = (
    "demande_facture",       # copie / duplicata d'une facture
    "demande_attestation",   # attestation de présence (ou certificat)
    "rendez_vous",           # prendre, déplacer, annuler, confirmer, retard, RDV manqué
    "question_tarif",        # prix, devis, remboursement
    "question_facturation",  # frais facturés, paiement, RDV manqué facturé...
    "question_medicale",     # symptôme, suite de soins, médicament
    "information_pratique",  # horaires, adresse, accès, urgences...
    "administratif",         # coordonnées, mutuelle, copie de dossier...
    "reclamation",
    "professionnel",         # confrère, laboratoire, fournisseur, organisme
    "publicite",
    "message_automatique",   # absence, accusé de réception, notification
    "remerciement",          # simple merci, aucune demande
    "autre",
)

ACTIONS_RDV = ("prendre", "deplacer", "annuler", "confirmer", "retard", "rdv_manque")

ACTES = (
    "consultation", "detartrage", "radio_panoramique", "extraction_simple",
    "extraction_dent_sagesse", "traitement_canal", "couronne", "blanchiment", "autre_acte",
)

INFOS = ("horaires", "adresse", "telephone", "rdv_en_ligne", "urgences", "annulation", "autre_info")

PERSONNES = ("expediteur", "conjoint", "enfant", "parent", "autre_personne", "inconnu")

# Niveaux d'urgence, du moins au plus grave. « signal » = un mot d'alerte isolé,
# sans contexte qui le confirme : remonte en priorité haute, pas en urgence.
NIVEAUX_URGENCE = ("aucune", "signal", "possible", "probable")
NIVEAUX_SUSPICION = ("aucun", "possible", "certain")


def rang_urgence(niveau: str) -> int:
    return NIVEAUX_URGENCE.index(niveau) if niveau in NIVEAUX_URGENCE else 0


def rang_suspicion(niveau: str) -> int:
    return NIVEAUX_SUSPICION.index(niveau) if niveau in NIVEAUX_SUSPICION else 0


@dataclass
class Mail:
    expediteur: str              # adresse normalisée (minuscules)
    sujet: str
    corps: str                   # corps brut, tel que reçu (stocké tel quel)
    source_id: str | None = None
    expediteur_brut: str = ""
    nom_affiche: str = ""
    repondre_a: str = ""         # en-tête Reply-To éventuel (adresse normalisée)
    texte: str = ""              # corps nettoyé, sans l'historique cité
    texte_cite: str = ""
    empreinte: str = ""


# ---------- Données du logiciel de cabinet (lecture seule) ----------

@dataclass(frozen=True)
class Patient:
    id: int
    nom: str
    prenom: str
    email: str | None
    telephone: str | None
    langue: str
    date_naissance: date

    @property
    def nom_complet(self) -> str:
        return f"{self.prenom} {self.nom}"

    def age(self, ref: date) -> int:
        n = self.date_naissance
        return ref.year - n.year - ((ref.month, ref.day) < (n.month, n.day))

    def est_mineur(self, ref: date) -> bool:
        return self.age(ref) < 18


@dataclass(frozen=True)
class Facture:
    numero: str
    patient_id: int
    date_facture: date
    statut: str
    fichier_pdf: str


@dataclass(frozen=True)
class RendezVous:
    """Rendez-vous SANS son motif : l'assistant ne lit jamais le motif (règle 4)."""
    id: int
    patient_id: int
    debut: datetime
    duree_min: int
    statut: str
    praticien: str


@dataclass(frozen=True)
class Representant:
    patient_id: int
    prenom: str
    nom: str
    email: str
    lien: str


# ---------- Résultat de la lecture d'un mail ----------

@dataclass(frozen=True)
class DateFloue:
    """Date telle qu'exprimée dans le mail : l'année ou le jour peuvent manquer."""
    jour: int | None
    mois: int | None
    annee: int | None = None

    def correspond(self, d: date) -> bool:
        return ((self.jour is None or self.jour == d.day)
                and (self.mois is None or self.mois == d.month)
                and (self.annee is None or self.annee == d.year))

    def __str__(self) -> str:
        j = f"{self.jour:02d}" if self.jour else "??"
        m = f"{self.mois:02d}" if self.mois else "??"
        a = str(self.annee) if self.annee else "????"
        return f"{j}/{m}/{a}"


@dataclass
class Analyse:
    source: str                                   # "regles", "llm" ou "regles+llm"
    langue: str | None = None
    langue_confiance: float = 0.0
    nb_mots: int = 0                              # longueur du texte lu (objet + message)
    indice_facturation: bool = False              # vocabulaire de facturation présent (payé, facturé, frais...)
    intentions: list[str] = field(default_factory=list)
    urgence: str = "aucune"
    signes_urgence: list[str] = field(default_factory=list)
    question_medicale: bool = False
    personne_concernee: str = "inconnu"
    prenom_concerne: str = ""
    nom_concerne: str = ""
    nom_signature: str = ""
    facture_numero: str = ""
    periode_mois: int = 0
    periode_annee: int = 0
    toutes_factures: bool = False
    dates: list[DateFloue] = field(default_factory=list)
    plage: tuple[date, date] | None = None        # ex. « la semaine dernière »
    heure_rdv: str = ""
    actions_rdv: list[str] = field(default_factory=list)   # voir ACTIONS_RDV
    type_attestation: str = "presence"            # presence | medicale
    actes_tarif: list[str] = field(default_factory=list)
    question_remboursement: bool = False
    infos_demandees: list[str] = field(default_factory=list)
    envoi_autre_adresse: str = ""
    questions_ouvertes: list[str] = field(default_factory=list)
    suspect: str = "aucun"
    raisons_suspect: list[str] = field(default_factory=list)
    resume: str = ""
    divergences: list[str] = field(default_factory=list)

    def vers_dict(self) -> dict:
        d = asdict(self)
        d["dates"] = [str(x) for x in self.dates]
        d["plage"] = [self.plage[0].isoformat(), self.plage[1].isoformat()] if self.plage else None
        return d
