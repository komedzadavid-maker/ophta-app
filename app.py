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
        {"id": 1, "nom": "Koffi Mensah", "tel": "+22890123456", "ass": "INAM (80%)", "taux": 0.80},
        {"id": 2, "nom": "Amavi Adjo", "tel": "+22891887766", "ass": "Aucune (100% Patient)", "taux": 0.0},
        {"id": 3, "nom": "Folly Kodjo", "tel": "+22892112233", "ass": "Ascoma (70%)", "taux": 0.70}
    ]

if "consultations" not in st.session_state:
    st.session_state.consultations = [
        {"id": 1, "patient": "Koffi Mensah", "tel": "+22890123456", "assurance": "INAM (80%)", "date": date(2026, 5, 10), "acte": "Consultation Simple", "diagnostic": "Myopie", "prescription": "Lunettes", "total": 5000, "part_patient": 1000, "part_assurance": 4000, "statut": "PAYÉ"},
        {"id": 2, "patient": "Amavi Adjo", "tel": "+22891887766", "assurance": "Aucune (100% Patient)", "date": date(2026, 5, 15), "acte": "Fond d'œil", "diagnostic": "Suivi diabète", "prescription": "RAS", "total": 8000, "part_patient": 8000, "part_assurance": 0, "statut": "PAYÉ"},
        {"id": 3, "patient": "Folly Kodjo", "tel": "+22892112233", "assurance": "Ascoma (70%)", "date": date(2026, 6, 2), "acte": "Examen de Réfraction (Lunettes)", "diagnostic": "Presbytie", "prescription": "Verres progressifs", "total": 4000, "part_patient": 1200, "part_assurance": 2800, "statut": "PAYÉ"}
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
st.write("Système Anti-Fraude, Assurances & Reçus WhatsApp")

tab1, tab2, tab3, tab4 = st.tabs(["📱 Accueil", "🩺 Médecin", "💰 Caisse", "📊 Direction"])

# ------------------------------------------
# TAB 1: ACCUEIL
# ------------------------------------------
with tab1:
    st.header("Enregistrement Patient")
    with st.form("new_patient_form"):
        nom = st.text_input("Nom et Prénom du Patient")
        tel = st.text_input("Numéro de Téléphone (ex: +22890XXXXXX)")
        ass = st.selectbox("Assurance / Prise en charge", ["Aucune (100% Patient)", "INAM (80%)", "Ascoma (70%)"])
        
        submitted = st.form_submit_button("Enregistrer le Patient")
        if submitted and nom:
            taux = 0.0
            if "INAM" in ass: taux = 0.80
            elif "Ascoma" in ass: taux = 0.70
            
            new_id = len(st.session_state.patients) + 1
            st.session_state.patients.append({"id": new_id, "nom": nom, "tel": tel.replace(" ", ""), "ass": ass, "taux": taux})
            st.success(f"✔️ Patient {nom} enregistré !")

# ------------------------------------------
# TAB 2: MÉDECIN
# ------------------------------------------
with tab2:
    st.header("Espace Consultation")
    lista_nomi = {p["nom"]: p for p in st.session_state.patients}
    patient_sel = st.selectbox("Sélectionner le patient", list(lista_nomi.keys()))
    
    if patient_sel:
        p_data = lista_nomi[patient_sel]
        st.info(f"📋 Patient: {p_data['nom']} | Couverture: {p_data['ass']}")
        
        acte = st.selectbox("Acte Médical / Examen", list(TARIFS.keys()))
        diagnostic = st.text_area("Diagnostic")
        prescription = st.text_input("Prescription")
        
        if st.button("Valider la Consultation 🔒"):
            montant_total = TARIFS[acte]
            part_assurance = montant_total * p_data["taux"]
            part_patient = montant_total - part_assurance
            
            st.session_state.consultations.append({
                "id": len(st.session_state.consultations) + 1,
                "patient": p_data["nom"],
                "tel": p_data["tel"],
                "assurance": p_data["ass"],
                "date": date.today(),
                "acte": acte,
                "diagnostic": diagnostic,
                "prescription": prescription,
                "total": montant_total,
                "part_patient": part_patient,
                "part_assurance": part_assurance,
                "statut": "En attente de paiement"
            })
            st.success("🔒 Envoyé à la caisse ! Montant bloqué.")

# ------------------------------------------
# TAB 3: CAISSE & WHATSAPP
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
                st.success("🎟️ COMPTABILISÉ EFFICACEMENT !")
                st.rerun()
                
    st.write("---")
    st.subheader("Derniers reçus payés (Envoi WhatsApp)")
    payes_recents = [c for c in st.session_state.consultations if c["statut"] == "PAYÉ"]
    
    for p in payes_recents[-3:]: # Mostra gli ultimi 3 pagati
        st.write(f"🟢 {p['patient']} - {int(p['part_patient'])} FCFA")
        
        # Generazione testo per WhatsApp
        texte_recu = (
            f"*OPHTACLINIQUE TOGO*\n"
            f"Reçu de paiement officiel\n"
            f"---------------------------\n"
            f"Date: {p['date'].strftime('%d/%m/%Y')}\n"
            f"Patient: {p['patient']}\n"
            f"Acte: {p['acte']}\n"
            f"Montant payé: {int(p['part_patient'])} FCFA\n"
            f"Prise en charge Assurance: {int(p['part_assurance'])} FCFA\n"
            f"---------------------------\n"
            f"Merci pour votre confiance !"
        )
        # Urlencode per convertire gli spazi e caratteri speciali per il link web
        texte_code = urllib.parse.quote(texte_recu)
        link_wa = f"https://wa.me/{p['tel']}?text={texte_code}"
        
        # Pulsante che apre direttamente WhatsApp
        st.video = st.link_button("📲 Envoyer le reçu via WhatsApp", link_wa)

# ------------------------------------------
# TAB 4: DIRECTION & EXCEL EXPORT
# ------------------------------------------
with tab4:
    st.header("Contrôle Directeur & Audits")
    
    oggi = date.today()
    primo_maggio = date(2026, 5, 1)
    
    per_input = st.date_input("Sélectionnez la période", value=(primo_maggio, oggi), max_value=oggi)
    
    if isinstance(per_input, tuple) and len(per_input) == 2:
        start_date, end_date = per_input
    else:
        start_date = end_date = per_input[0] if isinstance(per_input, tuple) else per_input

    if st.session_state.consultations:
        df = pd.DataFrame(st.session_state.consultations)
        df_filtre = df[(df['date'] >= start_date) & (df['date'] <= end_date) & (df['statut'] == 'PAYÉ')]
        
        cash_reel = df_filtre['part_patient'].sum() if not df_filtre.empty else 0
        dette_ass = df_filtre['part_assurance'].sum() if not df_filtre.empty else 0
        
        st.markdown(f"### 📈 Rapport du **{start_date.strftime('%d/%m/%Y')}** au **{end_date.strftime('%d/%m/%Y')}**")
        
        col1, col2 = st.columns(2)
        col1.metric("💵 Cash Réel Perçu", f"{int(cash_reel):,} FCFA".replace(",", " "))
        col2.metric("🏦 À facturer aux Assurances", f"{int(dette_ass):,} FCFA".replace(",", " "))
        
        # NUOVO PULSANTE EXPORT EXCEL/CSV
        if not df_filtre.empty:
            st.write(" ")
            # Escludiamo colonne tecniche per rendere il file Excel pulito per il direttore
            df_export = df_filtre[['date', 'patient', 'assurance', 'acte', 'total', 'part_patient', 'part_assurance']]
            csv_data = df_export.to_csv(index=False).encode('utf-8')
            
            st.download_button(
                label="📥 Télécharger ce rapport pour Excel (.csv)",
                data=csv_data,
                file_name=f"Rapport_OphtaClinique_{start_date}_{end_date}.csv",
                mime="text/csv",
            )
            
            st.dataframe(df_export)
    else:
        st.write("Aucune donnée.")