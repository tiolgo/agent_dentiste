"""Justesse sur les 10 mails de développement et sur les mails pièges, robustesse du traitement."""

import json
import unittest
from unittest import mock

from assistant_mails.normalisation import preparer_mail

from tests.donnees_test import FICHES_IDEALES, LecteurSimule, assistant_test, mails_dev, mails_pieges

ATTENDUS_DEV = {
    "1": dict(priorite="normale", categorie="facture", langue="fr", statut="à valider",
              pieces=["factures/2026/F-2026-0412.pdf"], contient=["F-2026-0412", "15 septembre 2026"]),
    "2": dict(priorite="urgente", categorie="urgence médicale", langue="pt", statut="à valider", pieces=[],
              contient=["112", "+352 20 00 00 00", "Joana Ferreira"]),
    "3": dict(priorite="normale", categorie="tarif", langue="fr", statut="à valider", pieces=[],
              contient=["Détartrage : 75 €", "CNS", "montant exact", "Doctena"]),
    "4": dict(priorite="normale", categorie="facture", langue="fr", statut="à valider", pieces=[],
              absent=["F-2025-0188", "Paul"]),
    "5": dict(priorite="normale", categorie="rendez-vous", langue="de", statut="à valider", pieces=[],
              contient=["21. Oktober 2026", "8:30 Uhr", "Guten Tag Thomas Schneider"]),
    "6": dict(priorite="haute", categorie="question médicale + attestation", langue="fr", statut="à valider",
              pieces=["attestations/2026/ATT-20260928-P0005-R7.pdf"],
              contient=["attestation de présence", "28 septembre 2026", "avis médical"]),
    "7": dict(priorite="basse", categorie="suspect", reponse=None, pieces=[]),
    "8": dict(priorite="normale", categorie="rendez-vous + facturation", langue="en", statut="à compléter",
              pieces=[], contient=["30 September 2026", "Doctena", "[[À COMPLÉTER"]),
    "9": dict(priorite="normale", categorie="facture", langue="lb", statut="à valider", pieces=[],
              contient=["Moien", "gesetzleche Vertrieder"], absent=["F-2026-0390", "Lena"]),
    "10": dict(priorite="basse", categorie="publicité", reponse=None, pieces=[]),
}


class MailsDeDeveloppement(unittest.TestCase):
    def _verifier(self, lecteur):
        assistant, _ = assistant_test(lecteur)
        resultats = {r.mail.source_id: r for r in assistant.traiter_lot(mails_dev())}
        for source, attendu in ATTENDUS_DEV.items():
            res = resultats[source]
            with self.subTest(mail=source):
                self.assertEqual(res.priorite, attendu["priorite"])
                self.assertEqual(res.categorie, attendu["categorie"])
                self.assertEqual(res.pieces, attendu["pieces"])
                if "reponse" in attendu:
                    self.assertIsNone(res.reponse)
                    continue
                self.assertEqual(res.langue, attendu["langue"])
                self.assertEqual(res.statut, attendu["statut"])
                for texte in attendu.get("contient", []):
                    self.assertIn(texte, res.reponse)
                for texte in attendu.get("absent", []):
                    self.assertNotIn(texte, res.reponse)

    def test_regles_seules(self):
        self._verifier(None)

    def test_avec_llm(self):
        self._verifier(LecteurSimule(FICHES_IDEALES))


class MailsPieges(unittest.TestCase):
    def test_attentes(self):
        assistant, _ = assistant_test()
        for mail, attendu in mails_pieges():
            res = assistant.traiter(mail)
            with self.subTest(mail=mail.source_id, sujet=mail.sujet):
                if "priorite" in attendu:
                    self.assertEqual(res.priorite, attendu["priorite"])
                if "langue" in attendu and res.reponse:
                    self.assertEqual(res.langue, attendu["langue"])
                if "pieces" in attendu:
                    self.assertEqual(sorted(res.pieces), sorted(attendu["pieces"]))
                if "sans_reponse" in attendu:
                    self.assertEqual(res.reponse is None, attendu["sans_reponse"])
                if "statut" in attendu:
                    self.assertEqual(res.statut, attendu["statut"])
                for c in attendu.get("categorie_contient", []):
                    self.assertIn(c, res.categorie)
                for c in attendu.get("reponse_contient", []):
                    self.assertIn(c, res.reponse or "")


class Robustesse(unittest.TestCase):
    def test_un_mail_deja_traite_n_est_pas_dedouble(self):
        assistant, stockage = assistant_test()
        mail = mails_dev()[0]
        assistant.traiter(mail)
        second = assistant.traiter(mail)
        self.assertTrue(second.deja_traite)
        self.assertEqual(len(stockage.brouillons), 1)
        assistant.traiter(mail, retraiter=True)
        self.assertEqual(len(stockage.brouillons), 2)

    def test_llm_en_panne_au_milieu_du_lot(self):
        """Fiches absentes = LLM injoignable : bascule en règles seules, sans perte."""
        fiches = {k: v for k, v in FICHES_IDEALES.items() if k in ("1", "2")}
        assistant, stockage = assistant_test(LecteurSimule(fiches))
        resultats = assistant.traiter_lot(mails_dev())
        self.assertEqual(len(stockage.brouillons), 10)
        self.assertTrue(any("LLM indisponible" in r.note or "injoignable" in r.note for r in resultats))

    def test_une_urgence_n_attend_pas_le_llm(self):
        """Règle 2 : le brouillon urgent est écrit en premier, sans appel au LLM (même lent ou en panne)."""
        appels = []

        class Lecteur(LecteurSimule):
            def lire(self, mail):
                appels.append(mail.source_id)
                return super().lire(mail)

        assistant, stockage = assistant_test(Lecteur(FICHES_IDEALES))
        resultats = assistant.traiter_lot(mails_dev())
        self.assertEqual(resultats[0].mail.source_id, "2")
        self.assertEqual(stockage.brouillons[0].priorite, "urgente")
        self.assertNotIn("2", appels)
        self.assertEqual(len(appels), 9)
        self.assertIn("sans attendre le LLM", resultats[0].note)

    def test_erreur_interne_donne_un_brouillon_de_secours(self):
        assistant, stockage = assistant_test()
        urgent = [m for m in mails_dev() if m.source_id == "2"][0]
        with mock.patch("assistant_mails.pipeline.decider", side_effect=RuntimeError("panne simulée")):
            res = assistant.traiter(urgent)
        self.assertEqual(res.categorie, "à traiter manuellement")
        self.assertEqual(res.priorite, "urgente")                     # l'urgence n'est pas perdue
        self.assertIsNone(res.reponse)
        self.assertEqual(len(stockage.brouillons), 1)

    def test_mails_degrades(self):
        cas = [("", "", ""), ("pas-une-adresse", None, None), ("a@b.lu", "Re: Re: Fwd:", "> cité seulement"),
               ("a@b.lu", "x" * 5000, "y" * 50000), ("a@b.lu", "Objet", "<html><script>alert(1)</script></html>")]
        for expediteur, sujet, corps in cas:
            with self.subTest(expediteur=expediteur):
                assistant, stockage = assistant_test()
                res = assistant.traiter(preparer_mail(expediteur, sujet, corps))
                self.assertIsNotNone(res.brouillon_id)
                self.assertIsNone(res.erreur)
                self.assertEqual(res.pieces, [])

    def test_resultat_serialisable(self):
        assistant, stockage = assistant_test(LecteurSimule(FICHES_IDEALES))
        assistant.traiter_lot(mails_dev())
        for b in stockage.brouillons:
            json.dumps(b.analyse_regles, ensure_ascii=False)
            json.dumps(b.analyse_llm, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()


class LeconsDuModeleReel(unittest.TestCase):
    """Fiches réellement renvoyées par qwen3:8b le 7 octobre 2026 (tests/fiches_qwen3_reelles.json) : les erreurs
    du modèle (année fausse, action inventée ou oubliée, langue mal rangée...) ne doivent pas dégrader le brouillon."""

    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        chemin = Path(__file__).resolve().parent / "fiches_qwen3_reelles.json"
        cls.fiches = json.loads(chemin.read_text(encoding="utf-8"))
        tous = {m.source_id: m for m in mails_dev()}
        tous.update({m.source_id: m for m, _ in mails_pieges()})
        assistant, _ = assistant_test(LecteurSimule(cls.fiches, nom="qwen3:8b (fiches réelles)"))
        cls.res = {sid: assistant.traiter(tous[sid]) for sid in cls.fiches}

    def test_annee_fausse_du_modele(self):              # « facture de septembre » lue 09/2025
        self.assertEqual(self.res["1"].pieces, ["factures/2026/F-2026-0412.pdf"])
        self.assertIn("28 septembre 2026", self.res["6"].reponse)   # date du RDV lue 2025-09-28

    def test_action_oubliee_et_date_inventee(self):      # « missed » oublié, date du 11/10 inventée
        self.assertIn("30 September 2026", self.res["8"].reponse)

    def test_action_inventee(self):                      # « annuler, retard » pour un simple report
        r = self.res["134"]
        self.assertEqual((r.priorite, r.statut), ("normale", "à valider"))
        self.assertIn("16 de outubro de 2026", r.reponse)

    def test_facturation_ajoutee_a_une_question_de_prix(self):
        r = self.res["3"]
        self.assertEqual((r.categorie, r.statut), ("tarif", "à valider"))

    def test_reclamation_manquee_par_le_modele(self):
        r = self.res["121"]
        self.assertIn("réclamation", r.categorie)
        self.assertEqual(r.priorite, "haute")

    def test_langue_non_prise_en_charge_et_mail_vide(self):
        self.assertEqual(self.res["116"].langue, "fr")     # italien lu « allemand » par le modèle
        self.assertIn("italien", self.res["116"].note)
        self.assertEqual(self.res["117"].langue, "fr")     # mail vide lu « anglais » par le modèle

    def test_mineure_et_luxembourgeois(self):
        r = self.res["9"]
        self.assertEqual((r.langue, r.pieces), ("lb", []))
