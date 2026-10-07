"""Génération d'une attestation de présence en PDF (bibliothèque standard uniquement).

L'attestation ne contient que le nom du patient, la date et l'heure de présence : jamais le
motif ni le praticien (une attestation destinée à un employeur ne doit rien révéler des soins).
Elle est préparée pour relecture : le secrétariat la vérifie, la signe et la tamponne.
"""

from __future__ import annotations

import textwrap
from datetime import date, datetime, timedelta
from pathlib import Path

from .connaissances import ADRESSE, NOM_CABINET, TELEPHONE, formater_date, formater_heure
from .modeles import Patient, RendezVous

_TEXTES = {
    "fr": {
        "titre": "ATTESTATION DE PRÉSENCE",
        "corps": "Le {cabinet} atteste la présence de {nom} au cabinet le {date}, de {debut} à {fin}.",
        "usage": "Attestation délivrée sur demande, pour servir et valoir ce que de droit.",
        "lieu": "Fait à Luxembourg, le {emission}.",
        "signature": "Pour le cabinet (signature et cachet) :",
    },
    "de": {
        "titre": "ANWESENHEITSBESCHEINIGUNG",
        "corps": "Die Zahnarztpraxis {cabinet} bestätigt die Anwesenheit von {nom} in der Praxis am {date} "
                 "von {debut} bis {fin}.",
        "usage": "Diese Bescheinigung wird auf Anfrage ausgestellt.",
        "lieu": "Luxemburg, den {emission}.",
        "signature": "Für die Praxis (Unterschrift und Stempel):",
    },
    "en": {
        "titre": "CERTIFICATE OF ATTENDANCE",
        "corps": "{cabinet} certifies that {nom} attended the practice on {date}, from {debut} to {fin}.",
        "usage": "This certificate is issued upon request.",
        "lieu": "Luxembourg, {emission}.",
        "signature": "For the practice (signature and stamp):",
    },
}


def _echapper(texte: str) -> bytes:
    brut = texte.encode("cp1252", errors="replace")
    return brut.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _pdf(elements: list[tuple[str, float, float, float, str]], traits: list[tuple[float, float, float, float]],
         titre: str) -> bytes:
    """PDF d'une page A4. elements : (police F1|F2, taille, x, y, texte) ; traits : (x1, y1, x2, y2)."""
    flux = b"BT\n"
    for police, taille, x, y, texte in elements:
        flux += f"/{police} {taille} Tf 1 0 0 1 {x:.1f} {y:.1f} Tm (".encode() + _echapper(texte) + b") Tj\n"
    flux += b"ET\n0.6 w\n"
    for x1, y1, x2, y2 in traits:
        flux += f"{x1:.1f} {y1:.1f} m {x2:.1f} {y2:.1f} l S\n".encode()
    horodatage = datetime.now().strftime("D:%Y%m%d%H%M%S")
    objets = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(flux)).encode() + b" >>\nstream\n" + flux + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
        b"<< /Title (" + _echapper(titre) + b") /Producer (assistant_mails) /CreationDate ("
        + horodatage.encode() + b") >>",
    ]
    sortie = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    positions = []
    for numero, objet in enumerate(objets, start=1):
        positions.append(len(sortie))
        sortie += f"{numero} 0 obj\n".encode() + objet + b"\nendobj\n"
    debut_xref = len(sortie)
    sortie += f"xref\n0 {len(objets) + 1}\n0000000000 65535 f \n".encode()
    for position in positions:
        sortie += f"{position:010d} 00000 n \n".encode()
    sortie += (f"trailer\n<< /Size {len(objets) + 1} /Root 1 0 R /Info {len(objets)} 0 R >>\n"
               f"startxref\n{debut_xref}\n%%EOF\n").encode()
    return sortie


def generer_attestation(chemin: Path, patient: Patient, rdv: RendezVous, langue: str, emission: date) -> Path:
    langue = langue if langue in _TEXTES else "fr"          # pt / lb : attestation en français
    t = _TEXTES[langue]
    fin = rdv.debut + timedelta(minutes=rdv.duree_min)
    corps = t["corps"].format(cabinet=NOM_CABINET, nom=patient.nom_complet,
                              date=formater_date(rdv.debut.date(), langue),
                              debut=formater_heure(rdv.debut, langue), fin=formater_heure(fin, langue))
    y = 770.0
    elements = [("F2", 14, 70, y, NOM_CABINET),
                ("F1", 10, 70, y - 16, f"{ADRESSE} — Tél. {TELEPHONE}"),
                ("F2", 16, 70, y - 90, t["titre"])]
    y -= 140
    for ligne in textwrap.wrap(corps, 82):
        elements.append(("F1", 11, 70, y, ligne))
        y -= 17
    y -= 12
    elements.append(("F1", 11, 70, y, t["usage"]))
    y -= 45
    elements.append(("F1", 11, 70, y, t["lieu"].format(emission=formater_date(emission, langue, False))))
    y -= 45
    elements.append(("F1", 11, 70, y, t["signature"]))
    traits = [(70, 740, 525, 740), (70, y - 50, 300, y - 50)]
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(_pdf(elements, traits, t["titre"]))
    return chemin
