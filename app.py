import streamlit as st
import pandas as pd
import sqlite3
import re
import urllib.parse
import io
from datetime import datetime

# Import per la generazione del PDF ufficiale (ReportLab)
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(page_title="OphtaClinique Togo - ERP", page_icon="👁️", layout="centered")

# 2. STRUTTURA PERSISTENZA DATI (SQLITE ORA SOTTOSTANTE)
DB_FILE = "clinic.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Tabella Pazienti con vincolo di unicità sul telefono
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            tel TEXT NOT NULL UNIQUE,
            email TEXT,
            assurance TEXT NOT NULL,
            taux REAL NOT NULL
        )
    """)
    # Tabella Consultazioni con timestamp cronologico nativo e snapshot dei dati finanziari
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consultations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            patient_nom TEXT NOT NULL,
            patient_tel TEXT NOT NULL,
            assurance TEXT NOT NULL,
            acte TEXT NOT NULL,
            total INTEGER NOT NULL,
            part_patient INTEGER NOT NULL,
            part_assurance INTEGER NOT NULL,
            diagnostic TEXT,
            statut TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Dizionario di configurazione rigido per evitare parsing fragili di stringhe
ASSURANCES_CONFIG = {
    "Aucune (100% Patient)": 0.0,
    "INAM (80%)": 0.80,
    "Ascoma (70%)": 0.70
}

TARIFS_PREDEFINIS = {
    "Consultation Simple": 5000,
    "Fond d'œil": 8000,
    "Examen de Réfraction (Lunettes)": 4000
}

# Funzione di utilità per validare i numeri di telefono (Formato Togo: +228XXXXXXXX)
def est_telephone_valide(tel):
    pattern = r"^\+228\d{8}$"
    return bool(re.match(pattern, tel))

# 3. MOTORE DI GENERAZIONE PDF CERTIFICATO (FORMATO A4 & ACCENTI STANDARD)
def generer_facture_pdf(caisse_record):
    buffer = io.BytesIO()
    # Impostazione esplicita su formato standard A4
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor('#1E3A8A'), alignment=1)
    normal_style = styles['Normal']
    bold_style = ParagraphStyle('BoldStyle', parent=normal_style, fontName='Helvetica-Bold')
    
    # Intestazione della Clinica
    story.append(Paragraph("<b>OPHTACLINIQUE - TOGO</b>", title_style))
    story.append(Paragraph("Lomé, Quartier Adidogomé | Tél: +228 22 00 00 00", ParagraphStyle('Sub', alignment=1, fontSize=9)))
    story.append(Spacer(1, 20))
    
    # Dettagli del Documento Fiscale (I dati passati come stringhe Unicode gestiscono correttamente gli accenti)
    story.append(Paragraph(f"<b>FACTURE N° :</b> FAC-2026-{caisse_record[0]}", normal_style))
    story.append(Paragraph(f"<b>Date d'émission :</b> {datetime.strptime(caisse_record[11], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y %H:%M')}", normal_style))
    story.append(Paragraph(f"<b>Patient :</b> {caisse_record[2]}", normal_style))
    story.append(Paragraph(f"<b>Couverture d'assurance :</b> {caisse_record[4]}", normal_style))
    story.append(Spacer(1, 15))
    
    # Tabella Finanziaria Strutturata
    table_data = [
        [Paragraph("<b>Désignation de l'acte</b>", bold_style), Paragraph("<b>Montant Total</b>", bold_style), Paragraph("<b>Part Assurance</b>", bold_style), Paragraph("<b>Net à Payer Patient</b>", bold_style)],
        [Paragraph(caisse_record[5], normal_style), f"{caisse_record[6]} FCFA", f"{caisse_record[8]} FCFA", f"{caisse_record[7]} FCFA"]
    ]
    
    t = Table(table_data, colWidths=[200, 90, 90, 110])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F3F4F6')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 25))
    
    story.append(Paragraph("<b>Statut du Paiement : PAYÉ</b>", ParagraphStyle('Status', textColor=colors.HexColor('#16A34A'), fontName='Helvetica-Bold', fontSize=11)))
    story.append(Spacer(1, 10))
    story.append(Paragraph("<i>Ce document fait foi de reçu officiel de paiement. Les montants sont perçus en Francs CFA (XOF).</i>", normal_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# 4. CONTROLLO RIGIDO DEGLI ACCESSI (ROLES-BASED ACCESS CONTROL)
st.sidebar.title("🔐 Authentification")
role = st.sidebar.selectbox(
    "Sélectionnez votre rôle opérationnel :",
    ["Veuillez choisir un rôle", "Réception", "Médecin", "Caisse", "Direction Uficiale"]
)

if "last_paid_id" not in st.session_state:
    st.session_state.last_paid_id = None

# INTERFACCIA DI BENVENUTO SE NESSUN RUOLO È SELEZIONATO
if role == "Veuillez choisir un rôle":
    st.info("👋 Bienvenue sur l'ERP OphtaClinique. Veuillez sélectionner votre rôle dans le panneau latéral gauche pour accéder aux fonctionnalités sécurisées.")

# ==========================================
# MODULE 1 : RECEPTION
# ==========================================
elif role == "Réception":
    st.header("📋 Espace Réception & Enregistrement")
    
    with st.form("form_enregistrement_patient"):
        nom = st.text_input("Nom et Prénom du Patient *")
        tel = st.text_input("Numéro de Téléphone (ex: +22890123456) *")
        email = st.text_input("Adresse E-mail (Optionnel)")
        assurance_sel = st.selectbox("Prise en charge / Assurance", list(ASSURANCES_CONFIG.keys()))
        
        if st.form_submit_button("Enregistrer le dossier patient"):
            if not nom or not tel:
                st.error("❌ Erreur : Les champs Nom et Téléphone sont obligatoires.")
            elif not est_telephone_valide(tel.strip()):
                st.error("❌ Erreur de format : Le numéro doit respecter le format officiel du Togo (ex: +22890123456).")
            else:
                tel_clean = tel.strip().replace(" ", "")
                taux_associe = ASSURANCES_CONFIG[assurance_sel]
                
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "INSERT INTO patients (nom, tel, email, assurance, taux) VALUES (?, ?, ?, ?, ?)",
                        (nom.strip(), tel_clean, email.strip().lower(), assurance_sel, taux_associe)
                    )
                    conn.commit()
                    st.success(f"✔️ Le dossier de {nom} è stato creato con successo.")
                except sqlite3.IntegrityError:
                    st.error(f"❌ Erreur Sécurité : Un patient possède déjà le numéro de téléphone {tel_clean}.")
                finally:
                    conn.close()

# ==========================================
# MODULE 2 : MEDECIN
# ==========================================
elif role == "Médecin":
    st.header("🩺 Espace de Consultation Médicale")
    
    search_q = st.text_input("🔍 Rechercher un patient par Nom o Téléphone :")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if search_q:
        cursor.execute("SELECT * FROM patients WHERE nom LIKE ? OR tel LIKE ?", (f"%{search_q}%", f"%{search_q}%"))
    else:
        cursor.execute("SELECT * FROM patients")
    patients_liste = cursor.fetchall()
    conn.close()

    if patients_liste:
        dict_patients = {f"{p[1]} ({p[2]})": p for p in patients_liste}
        patient_choisi_str = st.selectbox("Sélectionner le patient sur le fauteuil :", list(dict_patients.keys()))
        p_actif = dict_patients[patient_choisi_str]
        
        st.success(f"📋 Dossier Actif : **{p_actif[1]}** | Assurance : **{p_actif[4]}**")
        
        type_acte = st.radio("Origine de la tarification du soin :", ["Tarif Standard Catalogue", "Prestation Spécifique (Saisie Manuelle)"])
        
        nom_acte_final = ""
        prix_acte_final = 0
        
        if type_acte == "Tarif Standard Catalogue":
            acte_sel = st.selectbox("Choisir l'acte :", list(TARIFS_PREDEFINIS.keys()))
            nom_acte_final = acte_sel
            prix_acte_final = TARIFS_PREDEFINIS[acte_sel]
            st.metric("Tarif Réglementaire de l'acte", f"{prix_acte_final} FCFA")
        else:
            nom_acte_final = st.text_input("Saisir l'intitulé exact de la prestation spécifique *")
            prix_acte_final = st.number_input("Définir le prix de l'acte (FCFA) *", min_value=0, step=1000, value=5000)
            
        diagnostic = st.text_area("Observations cliniques & Diagnostic")
        
        if st.button("Transmettre le dossier financier et Verrouiller l'acte 🔒"):
            if type_acte != "Tarif Standard Catalogue" and not nom_acte_final:
                st.error("❌ Erreur : Veuillez spécifier le libellé de l'acte personnalisé.")
            else:
                total = int(prix_acte_final)
                part_ass = int(total * p_actif[5])
                part_pat = int(total - part_ass)
                
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO consultations (patient_id, patient_nom, patient_tel, assurance, acte, total, part_patient, part_assurance, diagnostic, statut)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (p_actif[0], p_actif[1], p_actif[2], p_actif[4], nom_acte_final.strip(), total, part_pat, part_ass, diagnostic.strip(), "En attente de paiement"))
                conn.commit()
                conn.close()
                st.success(f"🔒 Acte transmis en caisse. Montant dû par le patient : {part_pat} FCFA")
    else:
        st.warning("Aucun patient correspondant trouvé dans la base de données.")

# ==========================================
# MODULE 3 : CAISSE (BLINDATO CONTRO LE MANIPOLAZIONI)
# ==========================================
elif role == "Caisse":
    st.header("💰 Caisse Principale d'Encaissement")
    
    # Gestione post-incasso (Emissione documenti bloccati)
    if st.session_state.last_paid_id is not None:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM consultations WHERE id = ?", (st.session_state.last_paid_id,))
        last_c = cursor.fetchone()
        conn.close()
        
        if last_c:
            st.success(f"🎟️ Encaissement validé pour : **{last_c[2]}** | Montant perçu : **{last_c[7]} FCFA**")
            
            # Generazione dinamica del PDF sicuro in formato A4
            pdf_data = generer_facture_pdf(last_c)
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📥 Télécharger la Facture PDF (A4)",
                    data=pdf_data,
                    file_name=f"Facture_{last_c[0]}_{last_c[2].replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )
            with col2:
                msg_wa = f"*OPHTACLINIQUE TOGO*\nReçu Officiel de Paiement\nFacture N°: FAC-2026-{last_c[0]}\nPatient: {last_c[2]}\nActe: {last_c[5]}\nMontant encaissé: {last_c[7]} FCFA\nStatut: PAYÉ ✔️"
                st.link_button("📲 Envoyer via WhatsApp", f"https://wa.me/{last_c[3]}?text={urllib.parse.quote(msg_wa)}")
                
            if st.button("🔄 Passer au patient suivant", type="primary"):
                st.session_state.last_paid_id = None
                st.rerun()
            st.write("---")

    # Elenco delle fatture inviate dal medico (Sola Lettura)
    st.subheader("💳 Attentes de règlement")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM consultations WHERE statut = 'En attente de paiement'")
    attentes = cursor.fetchall()
    conn.close()
    
    if not attentes:
        st.info("📌 Aucune facture en attente de paiement actuellement.")
    else:
        for c in attentes:
            with st.container():
                st.write(f"**Patient :** {c[2]} | Couverture : *{c[4]}*")
                st.write(f"**Acte prescrit par le médecin :** {c[5]}")
                st.error(f"💵 **MONTANT INTEGRAL IMPOSÉ : {c[7]} FCFA**")
                
                # FUNZIONALITÀ DI CONFERMA PER EVITARE CLIC ACCIDENTALI
                with st.popover(f"Valider l'encaissement de {c[7]} FCFA"):
                    st.write("⚠️ Confirmez-vous avoir reçu physiquement les fonds en espèces ?")
                    if st.button("Oui, confirmer et verrouiller la transaction", key=f"btn_lock_{c[0]}"):
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE consultations SET statut = 'PAYÉ' WHERE id = ?", (c[0],))
                        conn.commit()
                        conn.close()
                        st.session_state.last_paid_id = c[0]
                        st.rerun()
            st.write("---")

# ==========================================
# MODULE 4 : DIRECTION & EXPORT (CON BOM PER EXCEL)
# ==========================================
elif role == "Direction Uficiale":
    st.header("📊 Tableau de Bord Direction & Audit")
    
    conn = sqlite3.connect(DB_FILE)
    # Lettura completa della tabella per analisi statistica
    df = pd.read_sql_query("SELECT * FROM consultations", conn)
    conn.close()
    
    if not df.empty:
        # Formattazione corretta della data per i filtri di interfaccia
        df['created_at_dt'] = pd.to_datetime(df['created_at'])
        
        st.subheader("🔍 Filtres d'Audit Financier")
        f_col1, f_col2, f_col3 = st.columns(3)
        
        with f_col1:
            ass_filter = st.selectbox("Assurance", ["Toutes"] + list(df['assurance'].unique()))
        with f_col2:
            acte_filter = st.selectbox("Acte Médical", ["Tous"] + list(df['acte'].unique()))
        with f_col3:
            statut_filter = st.selectbox("Statut Règlement", ["Tous", "PAYÉ", "En attente de paiement"])
            
        # Applicazione rigida dei filtri sul DataFrame
        df_f = df
        if ass_filter != "Toutes": df_f = df_f[df_f['assurance'] == ass_filter]
        if acte_filter != "Tous": df_f = df_f[df_f['acte'] == acte_filter]
        if statut_filter != "Tous": df_f = df_f[df_f['statut'] == statut_filter]
        
        # Indicatori Finanziari Chiave (KPI)
        st.write("---")
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric("Volume Total Facturé", f"{int(df_f['total'].sum())} FCFA")
        with kpi2:
            real_ca = int(df_f[df_f['statut'] == 'PAYÉ']['part_patient'].sum())
            st.metric("Encaissements réels en caisse", f"{real_ca} FCFA", delta="Flux Physique Attendu")
        with kpi3:
            st.metric("Créances Assurances", f"{int(df_f['part_assurance'].sum())} FCFA")
            
        st.write("---")
        st.subheader("📋 Registre chronologique des transactions")
        st.dataframe(df_f[['id', 'created_at', 'patient_nom', 'assurance', 'acte', 'part_patient', 'part_assurance', 'statut']], use_container_width=True)
        
        # RIGENERAZIONE REPORT CON BOM CORRETTO PER EVITARE ROTTURE DI ACCENTI SU WINDOWS EXCEL
        csv_buffer = df_f.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📊 Exporter le registre d'audit vers Excel (CSV sécurisé)",
            data=csv_buffer,
            file_name=f"Audit_Financier_Clinique_{datetime.now().strftime('%d_%m_%Y')}.csv",
            mime="text/csv"
        )
    else:
        st.info("Aucune donnée financière n'est enregistrée dans la base de données centrale pour le moment.")