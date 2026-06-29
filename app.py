import streamlit as st
import pandas as pd
from datetime import datetime, date
import urllib.parse

# Configuration de la page pour smartphone
st.set_page_config(page_title="OphtaClinique Togo", page_icon="👁️", layout="centered")

# ==========================================
# SIMULAZIONE DATABASE (SESSION STATE)
# ==========================================
if "patients" not in st.session_state:
    st.session_state.patients = [
        {"id": 1, "nom": "Koffi Mensah", "tel": "+22890123456", "email": "koffi@gmail.com", "ass": "INAM (80%)", "taux": 0.80},
        {"id": 2, "nom": "Amavi Adjo", "tel": "+22891887766", "email": "amavi@yahoo.fr", "ass": "Aucune (100% Patient)", "taux": 0.0},
        {"id": 3, "nom": "Koffi Mensah (Doublon)", "tel": "+22899999999", "email": "koffi.errone@gmail.com", "ass": "INAM (80%)", "taux": 0.80}, # Doppione simulato per il test
        {"id": 4, "nom": "Folly Kodjo", "tel": "+22892112233", "email": "folly.k@outlook.com", "ass": "Ascoma (70%)", "taux": 0.70}
    ]

if "consultations" not in st.session_state:
    st.session_state.consultations = [
        {"id": 1, "patient": "Koffi Mensah", "tel": "+22890123456", "assurance": "INAM (80%)", "date": date(2026, 5, 10), "acte": "Consultation Simple", "diagnostic": "Myopie", "prescription": "Lunettes", "total": 5000, "part_patient": 1000, "part_assurance": 4000, "statut": "PAYÉ"},
        {"id": 2, "patient": "Amavi Adjo", "tel": "+22891887766", "assurance": "Aucune (100% Patient)", "date": date(2026, 5, 15), "acte": "Fond d'œil", "diagnostic": "Suivi diabète", "prescription": "RAS", "total": 8000, "part_patient": 8000, "part_assurance": 0, "statut": "PAYÉ"}
    ]

TARIFS = {
    "Consultation Simple": 5000,
    "Fond d'œil": 8000,
    "Examen de Réfraction (Lunettes)": 4000
}

# ==========================================
# INTERFACCIA GRAFICA
# ==========================================
st.title("👁️ OphtaClinique - Togo")
st.write("Mise à jour : Correction de numéros et Suppression des doublons")

tab1, tab2, tab3, tab4 = st.tabs(["📱 Accueil", "🩺 Médecin", "💰 Caisse", "📊 Direction"])

# ------------------------------------------
# TAB 1: ACCUEIL
# ------------------------------------------
with tab1:
    st.header("Enregistrement Patient")
    with st.form("new_patient_form"):
        nom = st.text_input("Nom et Prénom du Patient *")
        tel = st.text_input("Numéro de Téléphone (ex: +22890XXXXXX) *")
        email = st.text_input("Adresse E-mail (Optionnel)")
        ass = st.selectbox("Assurance / Prise en charge", ["Aucune (100% Patient)", "INAM (80%)", "Ascoma (70%)"])
        
        submitted = st.form_submit_button("Enregistrer le Patient")
        
        if submitted:
            if not nom or not tel:
                st.error("⚠️ Veuillez remplir les champs obligatoires.")
            else:
                tel_clean = tel.replace(" ", "")
                email_clean = email.strip().lower()
                
                # Controllo doppioni sul momento
                doublon_tel = any(p["tel"] == tel_clean for p in st.session_state.patients)
                
                if doublon_tel:
                    st.error(f"❌ Un patient avec le numéro {tel} existe déjà !")
                else:
                    taux = 0.0
                    if "INAM" in ass: taux = 0.80
                    elif "Ascoma" in ass: taux = 0.70
                    
                    new_id = len(st.session_state.patients) + 1
                    st.session_state.patients.append({
                        "id": new_id, "nom": nom, "tel": tel_clean, "email": email_clean, "ass": ass, "taux": taux
                    })
                    st.success(f"✔️ {nom} enregistré avec succès !")

# ------------------------------------------
# TAB 2: MÉDECIN
# ------------------------------------------
with tab2:
    st.header("Espace Consultation")
    search_query = st.text_input("🔍 Rechercher un patient (Nom, Tel, E-mail) :")
    
    if search_query:
        q = search_query.lower()
        patients_filtres = [p for p in st.session_state.patients if q in p["nom"].lower() or q in p["tel"] or q in p["email"].lower()]
    else:
        patients_filtres = st.session_state.patients

    if not patients_filtres:
        st.warning("❌ Aucun patient trouvé.")
        patient_sel = None
    else:
        choix_patients = {f"{p['nom']} ({p['tel']})": p for p in patients_filtres}
        option_choisie = st.selectbox("Sélectionner le patient :", list(choix_patients.keys()))
        patient_sel = choix_patients[option_choisie]

    if patient_sel:
        st.info(f"📋 Dossier attivo : **{patient_sel['nom']}**")
        acte = st.selectbox("Acte Médical / Examen", list(TARIFS.keys()))
        diagnostic = st.text_area("Diagnostic")
        prescription = st.text_input("Prescription")
        
        if st.button("Valider la Consultation 🔒"):
            montant_total = TARIFS[acte]
            part_assurance = montant_total * patient_sel["taux"]
            part_patient = montant_total - part_assurance
            
            st.session_state.consultations.append({
                "id": len(st.session_state.consultations) + 1,
                "patient": patient_sel["nom"],
                "tel": patient_sel["tel"],
                "assurance": patient_sel["ass"],
                "date": date.today(),
                "acte": acte,
                "diagnostic": diagnostic,
                "prescription": prescription,
                "total": montant_total,
                "part_patient": part_patient,
                "part_assurance": part_assurance,
                "statut": "En attente de paiement"
            })
            st.success("🔒 Envoyé à la caisse.")

# ------------------------------------------
# TAB 3: CAISSE (Con modifica numero manuale)
# ------------------------------------------
with tab3:
    st.header("Caisse de la Clinique")
    en_attente = [c for c in st.session_state.consultations if c["statut"] == "En attente de paiement"]
    
    if not en_attente:
        st.write("💰 Aucune facture en attente.")
    else:
        for c in en_attente:
            st.write(f"**Patient :** {c['patient']} ({c['assurance']})")
            st.warning(f"👉 **À PERCEVOIR : {int(c['part_patient'])} FCFA**")
            
            if st.button(f"Encaisser {int(c['part_patient'])} FCFA", key=f"btn_{c['id']}"):
                c["statut"] = "PAYÉ"
                st.success("🎟️ COMPTABILISÉ.")
                st.rerun()
                
    st.write("---")
    st.subheader("Derniers reçus (Envoi WhatsApp)")
    payes_recents = [c for c in st.session_state.consultations if c["statut"] == "PAYÉ"]
    
    for p in payes_recents[-2:]:
        st.write(f"🟢 **{p['patient']}**")
        
        # SULUZIONE AL PROBLEMA 2: Campo di testo per correggere il numero prima di inviare
        numero_wa_corrige = st.text_input(
            f"Vérifier/Modifier le numéro WhatsApp pour {p['patient']}", 
            value=p['tel'], 
            key=f"input_tel_{p['id']}"
        )
        
        texte_recu = (
            f"*OPHTACLINIQUE TOGO*\n"
            f"Reçu de paiement officiel\n"
            f"Date: {p['date'].strftime('%d/%m/%Y')}\n"
            f"Patient: {p['patient']}\n"
            f"Montant payé: {int(p['part_patient'])} FCFA\n"
            f"Merci !"
        )
        texte_code = urllib.parse.quote(texte_recu)
        
        # Il link usa il numero modificato manualmente, pulito da eventuali spazi di digitazione
        link_wa_final = f"https://wa.me/{numero_wa_corrige.replace(' ', '')}?text={texte_code}"
        
        st.link_button("📲 Envoyer via WhatsApp", link_wa_final, key=f"lnk_{p['id']}")

# ------------------------------------------
# TAB 4: DIRECTION (Con eliminazione doppioni)
# ------------------------------------------
with tab4:
    st.header("Contrôle Directeur")
    
    # SOLUZIONE AL PROBLEMA 1: Gestione ed eliminazione dei pazienti (Doppioni)
    st.subheader("🔧 Nettoyage de la Base de Données (Doublons)")
    st.write("Sélectionnez un patient enregistré par erreur ou en double pour le supprimer définitivement.")
    
    if st.session_state.patients:
        # Creiamo un dizionario per mappare la stringa visibile all'oggetto paziente reale
        liste_suppression = {f"ID {p['id']} : {p['nom']} ({p['tel']})": p for p in st.session_state.patients}
        patient_a_supprimer_str = st.selectbox("Choisir le patient à éliminer :", list(liste_suppression.keys()))
        
        patient_target = liste_suppression[patient_a_supprimer_str]
        
        if st.button(f"🔴 Supprimer définitivement : {patient_target['nom']}", key="btn_delete"):
            # Rimuoviamo il paziente dalla lista usando una list comprehension
            st.session_state.patients = [p for p in st.session_state.patients if p["id"] != patient_target["id"]]
            st.success(f"🗑️ Le patient '{patient_target['nom']}' a été supprimé du système !")
            st.rerun()
    else:
        st.write("Aucun patient dans la base de données.")
        
    st.write("---")
    st.subheader("Vue globale des consultations")
    if st.session_state.consultations:
        df = pd.DataFrame(st.session_state.consultations)
        st.dataframe(df[['date', 'patient', 'assurance', 'total', 'part_patient', 'statut']])