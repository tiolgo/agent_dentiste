"""Attestation PDF et cohérence des informations du cabinet."""

import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from assistant_mails.attestation_pdf import generer_attestation
from assistant_mails.connaissances import verifier_coherence
from assistant_mails.modeles import RendezVous

from tests.donnees_test import PATIENTS, RACINE, REF


class Attestation(unittest.TestCase):
    def setUp(self):
        self.dossier = Path(tempfile.mkdtemp())
        self.rdv = RendezVous(7, 5, datetime(2026, 9, 28, 15, 0), 60, "effectué", "Dr Sofia Almeida")

    def tearDown(self):
        shutil.rmtree(self.dossier, ignore_errors=True)

    def test_pdf_valide_et_minimal(self):
        for langue in ("fr", "de", "en", "pt", "lb"):
            with self.subTest(langue=langue):
                chemin = generer_attestation(self.dossier / f"att-{langue}.pdf", PATIENTS[4], self.rdv, langue, REF)
                brut = chemin.read_bytes()
                self.assertTrue(brut.startswith(b"%PDF-1.4"))
                self.assertTrue(brut.rstrip().endswith(b"%%EOF"))
                for interdit in (b"canal", b"Almeida", b"1968"):        # ni soin, ni praticien, ni naissance
                    self.assertNotIn(interdit, brut)

    @unittest.skipUnless(shutil.which("pdftotext"), "pdftotext absent")
    def test_texte_lisible(self):
        chemin = generer_attestation(self.dossier / "att.pdf", PATIENTS[4], self.rdv, "fr", REF)
        texte = subprocess.run(["pdftotext", str(chemin), "-"], capture_output=True, text=True, check=True).stdout
        self.assertIn("ATTESTATION DE PRÉSENCE", texte)
        self.assertIn("Claire Dupont", texte)
        self.assertIn("28 septembre 2026, de 15h à 16h", texte)


class InformationsCabinet(unittest.TestCase):
    def test_tarifs_coherents_avec_infos_cabinet(self):
        self.assertEqual(verifier_coherence(RACINE / "infos_cabinet.md"), [])


if __name__ == "__main__":
    unittest.main()
