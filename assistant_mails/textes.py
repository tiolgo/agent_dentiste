"""Textes de réponse pré-validés, en cinq langues.

Ce sont les SEULS textes qui peuvent partir chez un patient : le LLM n'en écrit aucun.
Ils ne contiennent ni conseil médical, ni contenu de dossier (motif, soins). Les seules
données variables sont des dates, heures et numéros de facture, insérés par le code après
contrôle d'autorisation.

Les versions luxembourgeoise et portugaise doivent être relues une fois par un locuteur
natif avant la mise en service (voir README).
"""

from __future__ import annotations

A_COMPLETER = "[[À COMPLÉTER PAR LE SECRÉTARIAT : {raison}]]"

TEXTES: dict[str, dict[str, str]] = {
    "salutation_nom": {
        "fr": "Bonjour {nom},", "de": "Guten Tag {nom},", "en": "Dear {nom},",
        "pt": "Bom dia, {nom},", "lb": "Moien {nom},",
    },
    "salutation": {
        "fr": "Bonjour,", "de": "Guten Tag,", "en": "Hello,", "pt": "Bom dia,", "lb": "Moien,",
    },
    "intro": {
        "fr": "Merci pour votre message.",
        "de": "vielen Dank für Ihre Nachricht.",
        "en": "Thank you for your message.",
        "pt": "Agradecemos a sua mensagem.",
        "lb": "Merci fir Är Noriicht.",
    },
    # ------------------------------------------------------------------ urgence
    "urgence": {
        "fr": "Votre message a été transmis en priorité à l'équipe soignante. Nous ne pouvons pas donner d'avis "
              "médical par e-mail : afin qu'un praticien puisse évaluer votre situation au plus vite, merci "
              "d'appeler le cabinet dès maintenant au {tel} ({horaires}).{rappel}\n\n"
              "En dehors de ces horaires, contactez le service de garde des médecins-dentistes. En cas d'urgence "
              "vitale, appelez immédiatement le 112.",
        "de": "Ihre Nachricht wurde vorrangig an unser Behandlungsteam weitergeleitet. Per E-Mail können wir "
              "keine medizinische Auskunft geben: Damit Ihre Situation so schnell wie möglich zahnärztlich "
              "beurteilt werden kann, rufen Sie bitte jetzt gleich in der Praxis an: {tel} ({horaires}).{rappel}\n\n"
              "Außerhalb dieser Zeiten wenden Sie sich bitte an den zahnärztlichen Bereitschaftsdienst (service "
              "de garde des médecins-dentistes). In einem lebensbedrohlichen Notfall rufen Sie sofort die 112 an.",
        "en": "Your message has been passed on to our dental team as a priority. We cannot give medical advice "
              "by email: so that a dentist can assess your situation as quickly as possible, please call the "
              "practice now on {tel} ({horaires}).{rappel}\n\n"
              "Outside these hours, please contact the on-call dental service (service de garde des "
              "médecins-dentistes). In a life-threatening emergency, call 112 immediately.",
        "pt": "A sua mensagem foi transmitida com prioridade à nossa equipa clínica. Não podemos dar pareceres "
              "médicos por e-mail: para que um médico dentista possa avaliar a sua situação o mais rapidamente "
              "possível, ligue agora para o consultório: {tel} ({horaires}).{rappel}\n\n"
              "Fora deste horário, contacte o serviço de urgência dos médicos dentistas (service de garde des "
              "médecins-dentistes). Em caso de emergência com risco de vida, ligue imediatamente para o 112.",
        "lb": "Är Noriicht gouf prioritär un eis Equipe weidergeleet. Per E-Mail kënne mir kee medizinesche Rot "
              "ginn: Fir datt en Zänndokter Är Situatioun esou séier wéi méiglech beurteele kann, rufft w.e.g. "
              "elo direkt an der Praxis un: {tel} ({horaires}).{rappel}\n\n"
              "Ausserhalb vun dësen Zäiten, wennt Iech w.e.g. un de Bereetschaftsdéngscht vun den Zänndokteren "
              "(service de garde des médecins-dentistes). Bei engem liewensgeféierlechen Noutfall rufft direkt "
              "den 112 un.",
    },
    "urgence_rappel": {
        "fr": " Nous allons également essayer de vous joindre par téléphone.",
        "de": " Wir werden außerdem versuchen, Sie telefonisch zu erreichen.",
        "en": " We will also try to reach you by phone.",
        "pt": " Vamos também tentar entrar em contacto consigo por telefone.",
        "lb": " Mir probéieren och, Iech telefonesch ze erreechen.",
    },
    "question_medicale": {
        "fr": "Concernant votre question médicale : nous ne donnons pas d'avis médical par e-mail. Votre question "
              "a été transmise à l'équipe soignante, qui reviendra vers vous. Vous pouvez également nous appeler "
              "au {tel} ({horaires}). Si votre situation vous inquiète ou évolue, n'attendez pas pour nous "
              "appeler ; en dehors des heures d'ouverture, contactez le service de garde des médecins-dentistes "
              "et, en cas d'urgence vitale, le 112.",
        "de": "Zu Ihrer medizinischen Frage: Per E-Mail geben wir keine medizinische Auskunft. Ihre Frage wurde "
              "an unser Behandlungsteam weitergeleitet, das sich bei Ihnen melden wird. Sie können uns auch "
              "telefonisch erreichen: {tel} ({horaires}). Wenn Sie beunruhigt sind oder sich etwas verändert, "
              "rufen Sie uns bitte umgehend an; außerhalb der Öffnungszeiten wenden Sie sich an den "
              "zahnärztlichen Bereitschaftsdienst, in einem lebensbedrohlichen Notfall an die 112.",
        "en": "Regarding your medical question: we do not give medical advice by email. Your question has been "
              "passed on to our dental team, who will get back to you. You can also call us on {tel} "
              "({horaires}). If you are worried or anything changes, please call us without waiting; outside "
              "opening hours, contact the on-call dental service, and in a life-threatening emergency, call 112.",
        "pt": "Quanto à sua questão de saúde: não damos pareceres médicos por e-mail. A sua questão foi "
              "transmitida à nossa equipa clínica, que entrará em contacto consigo. Também pode ligar-nos para o "
              "{tel} ({horaires}). Se a situação lhe causar preocupação ou se alterar, ligue-nos sem esperar; "
              "fora do horário de funcionamento, contacte o serviço de urgência dos médicos dentistas e, em caso "
              "de emergência com risco de vida, o 112.",
        "lb": "Wat Är medizinesch Fro ugeet: Per E-Mail gi mir kee medizinesche Rot. Är Fro gouf un eis Equipe "
              "weidergeleet, déi sech bei Iech mellt. Dir kënnt eis och telefonesch erreechen: {tel} "
              "({horaires}). Wann Dir Iech Suerge maacht oder sech eppes ännert, rufft eis w.e.g. direkt un; "
              "ausserhalb vun den Ëffnungszäiten wennt Iech un de Bereetschaftsdéngscht vun den Zänndokteren, a "
              "bei engem liewensgeféierlechen Noutfall un den 112.",
    },
    # ------------------------------------------------------------------ documents
    "facture_jointe": {
        "fr": "Veuillez trouver ci-joint le duplicata de votre facture n° {numero} du {date}.",
        "de": "Anbei erhalten Sie ein Duplikat Ihrer Rechnung Nr. {numero} vom {date}.",
        "en": "Please find attached a copy of your invoice no. {numero} dated {date}.",
        "pt": "Junto enviamos a segunda via da sua fatura n.º {numero}, de {date}.",
        "lb": "Am Unhang fannt Dir en Duplikat vun Ärer Rechnung Nr. {numero} vum {date}.",
    },
    "factures_jointes": {
        "fr": "Veuillez trouver ci-joint les duplicatas des factures suivantes : {liste}.",
        "de": "Anbei erhalten Sie Duplikate der folgenden Rechnungen: {liste}.",
        "en": "Please find attached copies of the following invoices: {liste}.",
        "pt": "Junto enviamos a segunda via das seguintes faturas: {liste}.",
        "lb": "Am Unhang fannt Dir Duplikater vun dëse Rechnungen: {liste}.",
    },
    "facture_element": {
        "fr": "n° {numero} du {date}", "de": "Nr. {numero} vom {date}", "en": "no. {numero} dated {date}",
        "pt": "n.º {numero}, de {date}", "lb": "Nr. {numero} vum {date}",
    },
    "facture_a_verifier": {
        "fr": "Nous avons bien reçu votre demande de facture.",
        "de": "Wir haben Ihre Anfrage nach einer Rechnung erhalten.",
        "en": "We have received your request for an invoice.",
        "pt": "Recebemos o seu pedido de fatura.",
        "lb": "Mir hunn Är Ufro fir eng Rechnung kritt.",
    },
    "attestation_jointe": {
        "fr": "Veuillez trouver ci-joint l'attestation de présence pour votre rendez-vous du {date}.",
        "de": "Anbei erhalten Sie die Anwesenheitsbescheinigung für Ihren Termin am {date}.",
        "en": "Please find attached the certificate of attendance for your appointment on {date}.",
        "pt": "Junto enviamos a declaração de presença relativa à sua consulta de {date}.",
        "lb": "Am Unhang fannt Dir d'Attestatioun iwwer Är Presenz beim Rendez-vous vum {date}.",
    },
    "attestation_a_verifier": {
        "fr": "Nous avons bien reçu votre demande d'attestation.",
        "de": "Wir haben Ihre Anfrage nach einer Bescheinigung erhalten.",
        "en": "We have received your request for a certificate.",
        "pt": "Recebemos o seu pedido de declaração.",
        "lb": "Mir hunn Är Ufro fir eng Attestatioun kritt.",
    },
    "attestation_medicale": {
        "fr": "Votre demande de certificat a été transmise au praticien, seul habilité à l'établir ; nous "
              "revenons vers vous rapidement.",
        "de": "Ihre Anfrage nach einem ärztlichen Attest wurde an unser zahnärztliches Team weitergeleitet, das "
              "allein ein solches Attest ausstellen kann; wir melden uns in Kürze bei Ihnen.",
        "en": "Your request for a medical certificate has been passed on to the dentist, who alone can issue "
              "it; we will get back to you shortly.",
        "pt": "O seu pedido de atestado foi transmitido ao médico dentista, o único habilitado a emiti-lo; "
              "entraremos em contacto consigo brevemente.",
        "lb": "Är Ufro fir en Attest gouf un den Zänndokter weidergeleet, deen et eleng ausstelle kann; mir "
              "mellen eis geschwënn bei Iech.",
    },
    "doc_refus_tiers": {
        "fr": "Pour protéger la confidentialité des données de chaque patient, nous ne pouvons transmettre une "
              "facture ou une attestation qu'au patient concerné, à l'adresse e-mail enregistrée dans son "
              "dossier. La personne concernée peut donc nous écrire directement depuis cette adresse, ou nous "
              "appeler au {tel} ({horaires}).",
        "de": "Zum Schutz der Daten jeder Patientin und jedes Patienten können wir Rechnungen und "
              "Bescheinigungen nur an die betroffene Person selbst senden, und zwar an die in ihrer Akte "
              "hinterlegte E-Mail-Adresse. Die betroffene Person kann uns gerne direkt von dieser Adresse aus "
              "schreiben oder uns unter {tel} ({horaires}) anrufen.",
        "en": "To protect the confidentiality of each patient's data, we can only send an invoice or a "
              "certificate to the patient concerned, at the email address registered in their file. The person "
              "concerned is welcome to write to us directly from that address, or to call us on {tel} "
              "({horaires}).",
        "pt": "Para proteger a confidencialidade dos dados de cada paciente, só podemos enviar uma fatura ou uma "
              "declaração ao próprio paciente, para o endereço de e-mail registado no seu processo. A pessoa em "
              "causa pode escrever-nos diretamente a partir desse endereço ou ligar-nos para o {tel} "
              "({horaires}).",
        "lb": "Fir d'Vertraulechkeet vun den Donnéeë vun all Patient ze schützen, kënne mir eng Rechnung oder eng "
              "Attestatioun just dem betraffene Patient selwer schécken, an zwar un d'E-Mail-Adress, déi a "
              "sengem Dossier registréiert ass. Déi betraffe Persoun kann eis gären direkt vun där Adress aus "
              "schreiwen oder eis op {tel} ({horaires}) uruffen.",
    },
    "doc_refus_adresse": {
        "fr": "Pour protéger la confidentialité de vos données, nous envoyons les factures et attestations "
              "uniquement à l'adresse e-mail enregistrée dans le dossier du patient, et votre message nous "
              "parvient d'une adresse que nous ne pouvons pas rattacher à un dossier. Merci de nous écrire depuis "
              "l'adresse e-mail enregistrée dans votre dossier, ou de nous appeler au {tel} ({horaires}) pour "
              "vérifier ou mettre à jour vos coordonnées.",
        "de": "Zum Schutz Ihrer Daten senden wir Rechnungen und Bescheinigungen ausschließlich an die in der "
              "Patientenakte hinterlegte E-Mail-Adresse. Ihre Nachricht kommt jedoch von einer Adresse, die wir "
              "keiner Akte zuordnen können. Bitte schreiben Sie uns von der in Ihrer Akte hinterlegten "
              "E-Mail-Adresse aus oder rufen Sie uns unter {tel} ({horaires}) an, um Ihre Kontaktdaten zu "
              "überprüfen oder zu aktualisieren.",
        "en": "To protect your data, we only send invoices and certificates to the email address registered in "
              "the patient's file, and your message comes from an address we cannot link to a file. Please write "
              "to us from the email address registered in your file, or call us on {tel} ({horaires}) to check "
              "or update your contact details.",
        "pt": "Para proteger os seus dados, só enviamos faturas e declarações para o endereço de e-mail registado "
              "no processo do paciente, e a sua mensagem chega-nos de um endereço que não conseguimos associar a "
              "nenhum processo. Por favor, escreva-nos a partir do endereço de e-mail registado no seu processo, "
              "ou ligue-nos para o {tel} ({horaires}) para verificar ou atualizar os seus contactos.",
        "lb": "Fir Är Donnéeën ze schützen, schécke mir Rechnungen an Attestatiounen just un d'E-Mail-Adress, déi "
              "am Dossier vum Patient registréiert ass, an Är Noriicht kënnt vun enger Adress, déi mir kengem "
              "Dossier kënnen zouuerdnen. Schreift eis w.e.g. vun der E-Mail-Adress aus, déi an Ärem Dossier "
              "registréiert ass, oder rufft eis op {tel} ({horaires}) un, fir Är Kontaktdonnéeën ze iwwerpréiwen "
              "oder ze aktualiséieren.",
    },
    "doc_refus_mineur": {
        "fr": "Pour protéger la confidentialité des données de nos jeunes patients, les documents concernant un "
              "enfant mineur sont envoyés uniquement à l'adresse e-mail du représentant légal enregistrée dans "
              "son dossier. Afin de vérifier et d'enregistrer vos coordonnées, merci de nous appeler au {tel} "
              "({horaires}) ou de passer à l'accueil du cabinet ; nous pourrons ensuite donner suite à votre "
              "demande.",
        "de": "Zum Schutz der Daten unserer jungen Patientinnen und Patienten senden wir Unterlagen, die ein "
              "minderjähriges Kind betreffen, ausschließlich an die E-Mail-Adresse des gesetzlichen Vertreters, "
              "die in der Akte des Kindes hinterlegt ist. Damit wir Ihre Kontaktdaten überprüfen und hinterlegen "
              "können, rufen Sie uns bitte unter {tel} ({horaires}) an oder kommen Sie am Empfang vorbei; danach "
              "können wir Ihre Anfrage bearbeiten.",
        "en": "To protect the confidentiality of our young patients' data, documents concerning a minor are only "
              "sent to the email address of the legal guardian registered in the child's file. So that we can "
              "check and register your contact details, please call us on {tel} ({horaires}) or come by the "
              "reception desk; we will then be able to process your request.",
        "pt": "Para proteger a confidencialidade dos dados dos nossos pacientes mais novos, os documentos "
              "relativos a um menor são enviados apenas para o endereço de e-mail do representante legal "
              "registado no processo da criança. Para podermos verificar e registar os seus contactos, ligue-nos "
              "para o {tel} ({horaires}) ou dirija-se à receção do consultório; poderemos depois dar seguimento "
              "ao seu pedido.",
        "lb": "Fir d'Vertraulechkeet vun den Donnéeë vun eise jonke Patienten ze schützen, schécke mir "
              "Dokumenter, déi e mannerjäregt Kand betreffen, just un d'E-Mail-Adress vum gesetzleche Vertrieder, "
              "déi am Dossier vum Kand registréiert ass. Fir datt mir Är Kontaktdonnéeën iwwerpréiwen a "
              "registréiere kënnen, rufft eis w.e.g. op {tel} ({horaires}) un oder kommt bei eis op "
              "d'Receptioun; duerno kënne mir Är Ufro bearbechten.",
    },
    "doc_redirection": {
        "fr": "Pour des raisons de confidentialité, nous envoyons les documents uniquement à l'adresse e-mail "
              "enregistrée dans votre dossier, c'est-à-dire celle à laquelle nous répondons ; vous pourrez "
              "ensuite les transférer vous-même si besoin.",
        "de": "Aus Datenschutzgründen senden wir Unterlagen ausschließlich an die in Ihrer Akte hinterlegte "
              "E-Mail-Adresse, also an die Adresse, an die wir antworten; Sie können sie anschließend bei Bedarf "
              "selbst weiterleiten.",
        "en": "For confidentiality reasons, we only send documents to the email address registered in your file, "
              "which is the one we are replying to; you can then forward them yourself if needed.",
        "pt": "Por razões de confidencialidade, só enviamos documentos para o endereço de e-mail registado no seu "
              "processo, ou seja, aquele a que estamos a responder; poderá depois reencaminhá-los, se necessário.",
        "lb": "Aus Grënn vun der Vertraulechkeet schécke mir Dokumenter just un d'E-Mail-Adress, déi an Ärem "
              "Dossier registréiert ass, also déi, op déi mir äntweren; Dir kënnt se duerno selwer "
              "weiderschécken, wann néideg.",
    },
    # ------------------------------------------------------------------ rendez-vous
    "rdv_deplacer": {
        "fr": "Nous avons bien noté que vous ne pourrez pas vous présenter à votre rendez-vous du {date} à "
              "{heure}. Pour convenir d'un nouveau rendez-vous, pourriez-vous nous indiquer vos disponibilités "
              "(jours et horaires) en réponse à ce message ? Vous pouvez aussi nous appeler au {tel} ({horaires}).",
        "de": "Wir haben zur Kenntnis genommen, dass Sie Ihren Termin am {date} um {heure} nicht wahrnehmen "
              "können. Damit wir einen neuen Termin vereinbaren können, teilen Sie uns bitte in Ihrer Antwort "
              "mit, an welchen Tagen und zu welchen Uhrzeiten Sie verfügbar sind. Sie können uns auch telefonisch "
              "erreichen: {tel} ({horaires}).",
        "en": "We have noted that you will not be able to attend your appointment on {date} at {heure}. To "
              "arrange a new appointment, could you let us know when you are available (days and times) by "
              "replying to this message? You can also call us on {tel} ({horaires}).",
        "pt": "Tomámos nota de que não poderá comparecer à sua consulta de {date}, às {heure}. Para marcarmos uma "
              "nova consulta, pode indicar-nos a sua disponibilidade (dias e horários) em resposta a esta "
              "mensagem? Também pode ligar-nos para o {tel} ({horaires}).",
        "lb": "Mir hunn notéiert, datt Dir net op Äre Rendez-vous vum {date} um {heure} komme kënnt. Fir en "
              "neie Rendez-vous ze fixéieren, kënnt Dir eis w.e.g. an Ärer Äntwert soen, wéini Dir disponibel "
              "sidd (Deeg an Auerzäiten)? Dir kënnt eis och telefonesch erreechen: {tel} ({horaires}).",
    },
    "rdv_annuler": {
        "fr": "Nous avons bien pris note de votre demande d'annulation de votre rendez-vous du {date} à {heure}. "
              "Si vous souhaitez reprendre rendez-vous, vous pouvez le faire {doctena} ou par téléphone au {tel} "
              "({horaires}).",
        "de": "Wir haben die Absage Ihres Termins am {date} um {heure} zur Kenntnis genommen. Wenn Sie einen "
              "neuen Termin vereinbaren möchten, können Sie dies {doctena} oder telefonisch unter {tel} "
              "({horaires}) tun.",
        "en": "We have noted your request to cancel your appointment on {date} at {heure}. If you would like to "
              "book a new appointment, you can do so {doctena} or by phone on {tel} ({horaires}).",
        "pt": "Tomámos nota do seu pedido de cancelamento da consulta de {date}, às {heure}. Se quiser marcar "
              "nova consulta, pode fazê-lo {doctena} ou por telefone, através do {tel} ({horaires}).",
        "lb": "Mir hunn Är Ofso fir de Rendez-vous vum {date} um {heure} notéiert. Wann Dir en neie Rendez-vous "
              "wëllt huelen, kënnt Dir dat {doctena} oder telefonesch op {tel} ({horaires}) maachen.",
    },
    "rdv_confirmer": {
        "fr": "Nous vous confirmons votre rendez-vous du {date} à {heure}.",
        "de": "Gerne bestätigen wir Ihren Termin am {date} um {heure}.",
        "en": "We confirm your appointment on {date} at {heure}.",
        "pt": "Confirmamos a sua consulta de {date}, às {heure}.",
        "lb": "Mir confirméieren Iech Äre Rendez-vous vum {date} um {heure}.",
    },
    "rdv_retard": {
        "fr": "Merci de nous avoir prévenus.",
        "de": "Vielen Dank, dass Sie uns Bescheid gegeben haben.",
        "en": "Thank you for letting us know.",
        "pt": "Agradecemos o aviso.",
        "lb": "Merci, datt Dir eis Bescheed gesot hutt.",
    },
    "rdv_manque": {
        "fr": "Nous avons bien noté que vous n'avez pas pu venir à votre rendez-vous du {date}.",
        "de": "Wir haben zur Kenntnis genommen, dass Sie Ihren Termin am {date} nicht wahrnehmen konnten.",
        "en": "We have noted that you were unable to attend your appointment on {date}.",
        "pt": "Tomámos nota de que não pôde comparecer à sua consulta de {date}.",
        "lb": "Mir hunn notéiert, datt Dir net op Äre Rendez-vous vum {date} komme konnt.",
    },
    "rdv_manque_sans_date": {
        "fr": "Nous avons bien noté que vous n'avez pas pu venir à votre rendez-vous.",
        "de": "Wir haben zur Kenntnis genommen, dass Sie Ihren Termin nicht wahrnehmen konnten.",
        "en": "We have noted that you were unable to attend your appointment.",
        "pt": "Tomámos nota de que não pôde comparecer à sua consulta.",
        "lb": "Mir hunn notéiert, datt Dir net op Äre Rendez-vous komme konnt.",
    },
    "rdv_a_verifier": {
        "fr": "Nous avons bien reçu votre demande concernant votre rendez-vous.",
        "de": "Wir haben Ihre Anfrage zu Ihrem Termin erhalten.",
        "en": "We have received your request regarding your appointment.",
        "pt": "Recebemos o seu pedido relativo à sua consulta.",
        "lb": "Mir hunn Är Ufro iwwer Äre Rendez-vous kritt.",
    },
    "rdv_neutre": {
        "fr": "Nous avons bien reçu votre demande concernant un rendez-vous. Afin de protéger la confidentialité "
              "des données de nos patients, nous ne communiquons ni ne modifions de rendez-vous par e-mail "
              "lorsque la demande ne provient pas de l'adresse enregistrée dans le dossier. Merci de nous appeler "
              "au {tel} ({horaires}) : nous traiterons votre demande avec plaisir.",
        "de": "Wir haben Ihre Anfrage zu einem Termin erhalten. Zum Schutz der Daten unserer Patientinnen und "
              "Patienten geben wir per E-Mail keine Termine bekannt und ändern auch keine, wenn die Anfrage nicht "
              "von der in der Akte hinterlegten Adresse kommt. Bitte rufen Sie uns unter {tel} ({horaires}) an – "
              "wir kümmern uns gerne um Ihr Anliegen.",
        "en": "We have received your request regarding an appointment. To protect our patients' data, we do not "
              "share or change appointments by email when the request does not come from the address registered "
              "in the file. Please call us on {tel} ({horaires}) and we will be happy to help.",
        "pt": "Recebemos o seu pedido relativo a uma consulta. Para proteger os dados dos nossos pacientes, não "
              "comunicamos nem alteramos consultas por e-mail quando o pedido não vem do endereço registado no "
              "processo. Por favor, ligue-nos para o {tel} ({horaires}): teremos todo o gosto em ajudar.",
        "lb": "Mir hunn Är Ufro iwwer e Rendez-vous kritt. Fir d'Donnéeë vun eise Patienten ze schützen, ginn a "
              "verännere mir per E-Mail keng Rendez-vousen, wann d'Ufro net vun der Adress kënnt, déi am Dossier "
              "registréiert ass. Rufft eis w.e.g. op {tel} ({horaires}) un – mir hëllefen Iech gären.",
    },
    "rdv_prendre": {
        "fr": "Pour prendre rendez-vous, vous pouvez réserver directement {doctena} ou nous appeler au {tel} "
              "({horaires}).",
        "de": "Einen Termin können Sie direkt {doctena} buchen oder telefonisch unter {tel} ({horaires}) "
              "vereinbaren.",
        "en": "To book an appointment, you can book directly {doctena} or call us on {tel} ({horaires}).",
        "pt": "Para marcar uma consulta, pode fazê-lo diretamente {doctena} ou ligar-nos para o {tel} "
              "({horaires}).",
        "lb": "Fir e Rendez-vous ze huelen, kënnt Dir direkt {doctena} reservéieren oder eis op {tel} "
              "({horaires}) uruffen.",
    },
    # ------------------------------------------------------------------ facturation, tarifs, infos
    "facturation": {
        "fr": "Concernant votre question sur la facturation :",
        "de": "Zu Ihrer Frage zur Abrechnung:",
        "en": "Regarding your question about billing:",
        "pt": "Quanto à sua questão sobre a faturação:",
        "lb": "Wat Är Fro iwwer d'Rechnung ugeet:",
    },
    "tarif": {
        "fr": "Voici nos tarifs indicatifs (honoraires conventionnés CNS) :\n{lignes}\nLes montants exacts "
              "dépendent de l'acte réalisé ; les devis sont établis par le praticien après consultation.",
        "de": "Hier unsere Richtpreise (CNS-Vertragshonorare):\n{lignes}\nDie genauen Beträge hängen von der "
              "tatsächlich erbrachten Leistung ab; Kostenvoranschläge werden nach einer Untersuchung vom Zahnarzt "
              "erstellt.",
        "en": "Here are our indicative fees (CNS agreed rates):\n{lignes}\nExact amounts depend on the treatment "
              "actually carried out; quotes are drawn up by the dentist after a consultation.",
        "pt": "Eis os nossos preços indicativos (honorários convencionados com a CNS):\n{lignes}\nOs montantes "
              "exatos dependem do ato realizado; os orçamentos são elaborados pelo médico dentista após a "
              "consulta.",
        "lb": "Hei eis Richtpräisser (Konventiounstariffer vun der CNS):\n{lignes}\nDéi genee Montanten hänken "
              "dovun of, wat konkret gemaach gëtt; en Devis gëtt no enger Konsultatioun vum Zänndokter erstallt.",
    },
    "tarif_autre_acte": {
        "fr": "Pour les autres actes, le tarif dépend de votre situation : un devis est établi par le praticien "
              "après consultation.",
        "de": "Bei anderen Behandlungen hängt der Preis von Ihrer Situation ab: Ein Kostenvoranschlag wird nach "
              "einer Untersuchung vom Zahnarzt erstellt.",
        "en": "For other treatments, the fee depends on your situation: a quote is drawn up by the dentist after "
              "a consultation.",
        "pt": "Para outros atos, o preço depende da sua situação: o orçamento é elaborado pelo médico dentista "
              "após a consulta.",
        "lb": "Bei anere Behandlungen hänkt de Präis vun Ärer Situatioun of: En Devis gëtt no enger Konsultatioun "
              "vum Zänndokter erstallt.",
    },
    "remboursement": {
        "fr": "Les actes conventionnés sont partiellement remboursés par la CNS : vous réglez au cabinet puis vous "
              "vous faites rembourser, ou vous bénéficiez du tiers payant selon votre situation. Une mutuelle "
              "complémentaire (CMCM, etc.) peut compléter ce remboursement. Le cabinet ne peut pas vous indiquer "
              "le montant exact de votre remboursement.",
        "de": "Vertragsleistungen werden von der CNS teilweise erstattet: Sie bezahlen in der Praxis und lassen "
              "sich den Betrag anschließend erstatten, oder Sie profitieren je nach Ihrer Situation vom Tiers "
              "payant (Direktabrechnung). Eine Zusatzversicherung (CMCM usw.) kann die Erstattung ergänzen. Den "
              "genauen Erstattungsbetrag kann Ihnen die Praxis nicht nennen.",
        "en": "Treatments covered by the CNS agreement are partially reimbursed by the CNS: you pay at the "
              "practice and are then reimbursed, or you may benefit from direct billing (tiers payant) depending "
              "on your situation. A complementary insurance (CMCM, etc.) may top up the reimbursement. The "
              "practice cannot tell you the exact amount you will be reimbursed.",
        "pt": "Os atos convencionados são parcialmente reembolsados pela CNS: paga no consultório e depois pede o "
              "reembolso, ou beneficia do sistema de terceiro pagador (tiers payant), consoante a sua situação. "
              "Um seguro complementar (CMCM, etc.) pode completar o reembolso. O consultório não pode indicar o "
              "montante exato do seu reembolso.",
        "lb": "Konventionéiert Akten ginn deelweis vun der CNS rembourséiert: Dir bezuelt an der Praxis a loosst "
              "Iech duerno rembourséieren, oder Dir profitéiert, jee no Ärer Situatioun, vum Tiers payant. Eng "
              "Zousazversécherung (CMCM asw.) kann de Rembours ergänzen. D'Praxis kann Iech de genaue Betrag vun "
              "Ärem Rembours net soen.",
    },
    "info_horaires": {
        "fr": "Le cabinet est joignable par téléphone au {tel}, {horaires}.",
        "de": "Die Praxis ist telefonisch unter {tel} erreichbar: {horaires}.",
        "en": "The practice can be reached by phone on {tel}, {horaires}.",
        "pt": "O consultório pode ser contactado por telefone através do {tel}, {horaires}.",
        "lb": "D'Praxis ass telefonesch op {tel} ze erreechen, {horaires}.",
    },
    "info_adresse": {
        "fr": "Notre adresse : {adresse}.", "de": "Unsere Adresse: {adresse}.", "en": "Our address: {adresse}.",
        "pt": "A nossa morada: {adresse}.", "lb": "Eis Adress: {adresse}.",
    },
    "info_telephone": {
        "fr": "Notre numéro de téléphone : {tel} ({horaires}).",
        "de": "Unsere Telefonnummer: {tel} ({horaires}).",
        "en": "Our phone number: {tel} ({horaires}).",
        "pt": "O nosso número de telefone: {tel} ({horaires}).",
        "lb": "Eis Telefonsnummer: {tel} ({horaires}).",
    },
    "info_rdv_en_ligne": {
        "fr": "Vous pouvez prendre rendez-vous {doctena}.",
        "de": "Termine können Sie {doctena} buchen.",
        "en": "You can book an appointment {doctena}.",
        "pt": "Pode marcar consulta {doctena}.",
        "lb": "Dir kënnt e Rendez-vous {doctena} huelen.",
    },
    "info_urgences": {
        "fr": "En dehors des heures d'ouverture, vous pouvez contacter le service de garde des "
              "médecins-dentistes ; en cas d'urgence vitale, appelez le 112.",
        "de": "Außerhalb der Öffnungszeiten erreichen Sie den zahnärztlichen Bereitschaftsdienst (service de "
              "garde des médecins-dentistes); in einem lebensbedrohlichen Notfall rufen Sie die 112 an.",
        "en": "Outside opening hours, you can contact the on-call dental service (service de garde des "
              "médecins-dentistes); in a life-threatening emergency, call 112.",
        "pt": "Fora do horário de funcionamento, pode contactar o serviço de urgência dos médicos dentistas "
              "(service de garde des médecins-dentistes); em caso de emergência com risco de vida, ligue 112.",
        "lb": "Ausserhalb vun den Ëffnungszäiten kënnt Dir Iech un de Bereetschaftsdéngscht vun den "
              "Zänndokteren (service de garde des médecins-dentistes) wenden; bei engem liewensgeféierlechen "
              "Noutfall rufft den 112 un.",
    },
    "info_annulation": {
        "fr": "En cas d'annulation, merci de nous prévenir au moins 24 h à l'avance, par téléphone ou via Doctena.",
        "de": "Bitte sagen Sie Termine mindestens 24 Stunden im Voraus ab, telefonisch oder über Doctena.",
        "en": "If you need to cancel, please let us know at least 24 hours in advance, by phone or via Doctena.",
        "pt": "Em caso de cancelamento, pedimos que nos avise com pelo menos 24 horas de antecedência, por "
              "telefone ou através da Doctena.",
        "lb": "Wann Dir e Rendez-vous ofsot, gitt eis w.e.g. mindestens 24 Stonnen am Viraus Bescheed, "
              "telefonesch oder iwwer Doctena.",
    },
    "info_autre": {
        "fr": "Concernant votre question pratique :", "de": "Zu Ihrer Frage:", "en": "Regarding your question:",
        "pt": "Quanto à sua questão:", "lb": "Wat Är Fro ugeet:",
    },
    # ------------------------------------------------------------------ divers
    "reclamation": {
        "fr": "Nous avons bien reçu votre message et regrettons la situation que vous décrivez. Il a été transmis "
              "à la direction du cabinet, qui reviendra vers vous personnellement.",
        "de": "Wir haben Ihre Nachricht erhalten und bedauern die von Ihnen geschilderte Situation. Sie wurde an "
              "die Praxisleitung weitergeleitet, die sich persönlich bei Ihnen melden wird.",
        "en": "We have received your message and are sorry about the situation you describe. It has been passed "
              "on to the practice management, who will get back to you personally.",
        "pt": "Recebemos a sua mensagem e lamentamos a situação que descreve. Foi transmitida à direção do "
              "consultório, que entrará pessoalmente em contacto consigo.",
        "lb": "Mir hunn Är Noriicht kritt an et deet eis leed, wat Dir beschreift. Si gouf un d'Direktioun vun der "
              "Praxis weidergeleet, déi sech perséinlech bei Iech mellt.",
    },
    "administratif": {
        "fr": "Nous avons bien reçu votre demande, qui sera traitée par le secrétariat.",
        "de": "Wir haben Ihre Anfrage erhalten; das Sekretariat wird sie bearbeiten.",
        "en": "We have received your request, which will be handled by our front desk team.",
        "pt": "Recebemos o seu pedido, que será tratado pelo secretariado.",
        "lb": "Mir hunn Är Ufro kritt; de Sekretariat këmmert sech drëm.",
    },
    "autre": {
        "fr": "Nous avons bien reçu votre message et y donnerons suite rapidement.",
        "de": "Wir haben Ihre Nachricht erhalten und melden uns in Kürze.",
        "en": "We have received your message and will get back to you shortly.",
        "pt": "Recebemos a sua mensagem e daremos seguimento brevemente.",
        "lb": "Mir hunn Är Noriicht kritt a mellen eis geschwënn.",
    },
    "conclusion": {
        "fr": "Nous restons à votre disposition pour toute question.",
        "de": "Für Rückfragen stehen wir Ihnen gerne zur Verfügung.",
        "en": "Please do not hesitate to contact us if you have any questions.",
        "pt": "Estamos ao seu dispor para qualquer esclarecimento.",
        "lb": "Fir weider Froe stinn mir Iech gär zur Verfügung.",
    },
    "signature": {
        "fr": "Bien cordialement,\n\nLe secrétariat\n{cabinet}\n{tel}",
        "de": "Mit freundlichen Grüßen\n\nIhr Praxisteam\n{cabinet}\n{tel}",
        "en": "Kind regards,\n\nThe front desk team\n{cabinet}\n{tel}",
        "pt": "Com os melhores cumprimentos,\n\nO secretariado\n{cabinet}\n{tel}",
        "lb": "Mat beschte Gréiss\n\nD'Sekretariat\n{cabinet}\n{tel}",
    },
}
