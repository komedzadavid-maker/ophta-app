import streamlit as st
import pandas as pd
from datetime import datetime

# Configurazione della pagina per smartphone
st.set_page_config(page_title="OphtaClinique Togo", page_icon="👁️", layout="centered")

# ==========================================
# SIMULAZIONE DATABASE (SESSION STATE)
# ==========================================
if "patients" not in st.session_state:
    st.session_state.patients = [
        {"id": 1, "nom": "Koffi Mensah", "tel": "+228 90 12 34 56", "ass": "INAM (80%)", "taux": 0.80},
        {"id": 2, "nom": "Amavi Adjo", "tel": "+228 91 88 77 66", "ass": "Aucune (100% Patient)", "taux": 0.0},
        {"id": 3, "nom": "Folly Kodjo", "tel": "+228 92 11 22 33", "ass": "Ascoma (70%)", "taux": 0.70}
    ]

if "consultations" not in st.session_state:
    st.session_state.consultations = []

TARIFS = {
    "Consultation Simple": 5000,
    "Fond d'œil": 8000,
    "Examen de Réfraction (Lunettes)": 4000
}

# ==========================================
# INTERFACCIA GRAFICA
# ==========================================
st.title("👁️ OphtaClinique - Système de Contrôle")
st.write("Antoine, voici le prototype de gestion financière anti-fraude pour ton cabinet.")

# Menu a Tab per simulare i vari ruoli della clinica
tab1, tab2, tab3, tab4 = st.tabs(["📱 Accueil", "🩺 Médecin", "💰 Caisse", "📊 Direction"])

# ------------------------------------------
# TAB 1: ACCUEIL (Registrazione)
# ------------------------------------------
with tab1:
    st.header("Enregistrement Patient")
    with st.form("new_patient_form"):
        nom = st.text_input("Nom et Prénom du Patient")
        tel = st.text_input("Numéro de Téléphone")
        ass = st.selectbox("Assurance / Prise en charge", ["Aucune (100% Patient)", "INAM (80%)", "Ascoma (70%)"])
        
        submitted = st.form_submit_button("Enregistrer le Patient")
        if submitted and nom:
            taux = 0.0
            if "INAM" in ass: taux = 0.80
            elif "Ascoma" in ass: taux = 0.70
            
            new_id = len(st.session_state.patients) + 1
            st.session_state.patients.append({"id": new_id, "nom": nom, "tel": tel, "ass": ass, "taux": taux})
            st.success(f"✔️ Patient {nom} enregistré avec succès !")

# ------------------------------------------
# TAB 2: MÉDECIN (Diagnosi e Blocco Prezzo)
# ------------------------------------------
with tab2:
    st.header("Espace Consultation")
    
    # Selezione del paziente registrato
    lista_nomi = {p["nom"]: p for p in st.session_state.patients}
    patient_sel = st.selectbox("Sélectionner le patient dans la salle d'attente", list(lista_nomi.keys()))
    
    if patient_sel:
        p_data = lista_nomi[patient_sel]
        st.info(f"📋 Patient: {p_data['nom']} | Couverture: {p_data['ass']}")
        
        acte = st.selectbox("Acte Médical / Examen", list(TARIFS.keys()))
        diagnostic = st.text_area("Diagnostic (ex: Cataracte, Myopie...)")
        prescription = st.text_input("Prescription (ex: Collyre X, Verres correcteurs...)")
        
        if st.button("Valider la Consultation 🔒"):
            montant_total = TARIFS[acte]
            part_assurance = montant_total * p_data["taux"]
            part_patient = montant_total - part_assurance
            
            st.session_state.consultations.append({
                "id": len(st.session_state.consultations) + 1,
                "patient": p_data["nom"],
                "assurance": p_data["ass"],
                "date": datetime.now().strftime("%d/%m/%Y"),
                "acte": acte,
                "diagnostic": diagnostic,
                "prescription": prescription,
                "total": montant_total,
                "part_patient": part_patient,
                "part_assurance": part_assurance,
                "statut": "En attente de paiement"
            })
            st.success("🔒 Envoyé alla caisse ! Le montant est bloqué par le système.")

# ------------------------------------------
# TAB 3: CAISSE (Incassement Bloccato)
# ------------------------------------------
with tab3:
    st.header("Caisse Hors-Ligne")
    
    en_attente = [c for c in st.session_state.consultations if c["statut"] == "En attente de paiement"]
    
    if not en_attente:
        st.write("💰 Aucune facture en attente. Tout est en ordre.")
    else:
        for c in en_attente:
            with st.container():
                st.write(f"**Patient :** {c['patient']} ({c['assurance']})")
                st.write(f"**Acte :** {c['acte']}")
                st.warning(f"👉 **À PERCEVOIR DU PATIENT : {int(c['part_patient'])} FCFA** (Part Assurance: {int(c['part_assurance'])} FCFA)")
                
                if st.button(f"Encaisser et Imprimer le Reçu (Patient: {c['patient']})", key=f"btn_{c['id']}"):
                    c["statut"] = "PAYÉ"
                    st.success("🎟️ REÇU IMPRIMÉ AUTOMATIQUEMENT !")
                    st.code(f"""
====================================
      REÇU DE CAISSE OFFICIEL
====================================
Date: {c['date']}
Patient: {c['patient']}
Montant Perçu: {int(c['part_patient'])} FCFA
Statut: ENCAISSÉ ET SÉCURISÉ
====================================
                    """)
                    st.rerun()

# ------------------------------------------
# TAB 4: DIRECTION (Controllo Totale)
# ------------------------------------------
with tab4:
    st.header("Tableau de Bord du Directeur")
    
    payes = [c for c in st.session_state.consultations if c["statut"] == "PAYÉ"]
    
    cash_reel = sum([c["part_patient"] for c in payes])
    dette_ass = sum([c["part_assurance"] for c in payes])
    
    col1, col2 = st.columns(2)
    col1.metric("💵 Cash Réel en Caisse", f"{int(cash_reel)} FCFA")
    col2.metric("🏦 À réclamer aux Assurances", f"{int(dette_ass)} FCFA")
    
    st.subheader("Historique et Dossiers Médicaux des Patients")
    if not st.session_state.consultations:
        st.write("Aucune activité enregistrée aujourd'hui.")
    else:
        for c in st.session_state.consultations:
            status_color = "🟢" if c["statut"] == "PAYÉ" else "🔴"
            with st.expander(f"{status_color} {c['date']} - {c['patient']}"):
                st.write(f"**Diagnostic :** {c['diagnostic']}")
                st.write(f"**Prescription :** {c['prescription']}")
                st.write(f"**Détails Financiers :** Total {int(c['total'])} FCFA (Patient: {int(c['part_patient'])} FCFA / Assur.: {int(c['part_assurance'])} FCFA)")
                st.write(f"**Statut :** {c['statut']}")
