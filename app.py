import streamlit as st
import sqlite3
import hashlib
from typing import List, Any

# Configurazione Pagina
st.set_page_config(page_title="OphtaClinique Pro", page_icon="👁️", layout="wide")
DB_NAME = 'clinique.db'

# --- UTILS SICUREZZA ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tabelle
    c.execute('''CREATE TABLE IF NOT EXISTS utilisateurs (identifiant TEXT PRIMARY KEY, mot_de_passe_hash TEXT NOT NULL, role TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS services (id INTEGER PRIMARY KEY AUTOINCREMENT, nom_service TEXT NOT NULL, prix REAL NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS patients (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT, telephone TEXT, service_nom TEXT, montant REAL, statut TEXT DEFAULT 'En attente')''')
    
    # Dati di default
    c.execute("SELECT COUNT(*) FROM utilisateurs")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO utilisateurs VALUES (?, ?, ?)", ("admin", hash_password("admin123"), "Administrateur"))
        c.execute("INSERT INTO utilisateurs VALUES (?, ?, ?)", ("medecin", hash_password("med123"), "Médecin"))
        c.execute("INSERT INTO utilisateurs VALUES (?, ?, ?)", ("caisse", hash_password("caisse123"), "Caisse"))
    
    c.execute("SELECT COUNT(*) FROM services")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO services (nom_service, prix) VALUES (?, ?)", ("Consultation Standard", 5000))
    conn.commit()
    conn.close()

# --- COMPONENTI UI RIUTILIZZABILI ---
def afficher_gestion_services():
    st.subheader("🛠 Gestion du Catalogue des Actes")
    conn = sqlite3.connect(DB_NAME)
    services = conn.cursor().execute("SELECT * FROM services").fetchall()
    conn.close()
    
    for s in services: st.write(f"🔹 **{s[1]}** : {s[2]} CFA")
    
    with st.form("add_service"):
        nom = st.text_input("Nom du service")
        prix = st.number_input("Prix (CFA)", min_value=0)
        if st.form_submit_button("Ajouter"):
            conn = sqlite3.connect(DB_NAME)
            conn.cursor().execute("INSERT INTO services (nom_service, prix) VALUES (?, ?)", (nom, prix))
            conn.commit(); conn.close(); st.rerun()

# --- INTERFACCE RUOLI ---
def interface_admin():
    st.title("👑 Panneau Administration")
    tab1, tab2 = st.tabs(["📊 Gestion Services", "👥 Gestion Personnel"])
    with tab1: afficher_gestion_services()
    with tab2:
        st.write("Gestion des accès...")
        with st.form("new_user"):
            new_id = st.text_input("ID")
            new_pwd = st.text_input("Pass", type="password")
            role = st.selectbox("Role", ["Caisse", "Médecin", "Administrateur"])
            if st.form_submit_button("Créer"):
                conn = sqlite3.connect(DB_NAME)
                try:
                    conn.cursor().execute("INSERT INTO utilisateurs VALUES (?, ?, ?)", (new_id, hash_password(new_pwd), role))
                    conn.commit(); st.success("OK")
                except: st.error("ID déjà utilisé")
                conn.close()

def interface_medecin():
    st.title("🩺 Module Médecin")
    tab1, tab2 = st.tabs(["📝 Consultations", "🛠 Gestion Prix"])
    with tab1:
        conn = sqlite3.connect(DB_NAME)
        services = conn.cursor().execute("SELECT * FROM services").fetchall()
        conn.close()
        
        with st.form("new_pat"):
            nom = st.text_input("Nom Patient")
            tel = st.text_input("Tel")
            serv = st.selectbox("Service", [s[1] for s in services])
            if st.form_submit_button("Enregistrer"):
                # Trova prezzo
                conn = sqlite3.connect(DB_NAME)
                prezzo = conn.cursor().execute("SELECT prix FROM services WHERE nom_service=?", (serv,)).fetchone()[0]
                conn.cursor().execute("INSERT INTO patients (nom, telephone, service_nom, montant) VALUES (?, ?, ?, ?)", (nom, tel, serv, prezzo))
                conn.commit(); conn.close(); st.success("Patient ajouté!")
    with tab2: afficher_gestion_services()

def interface_caisse():
    st.title("💸 Module Caisse")
    conn = sqlite3.connect(DB_NAME)
    pazienti = conn.cursor().execute("SELECT * FROM patients WHERE statut='En attente'").fetchall()
    conn.close()
    
    if not pazienti: st.info("Aucun patient en attente.")
    for p in pazienti:
        col1, col2 = st.columns([3, 1])
        col1.write(f"👤 {p[1]} | Acte: {p[3]} | **Prix: {p[4]} CFA**")
        if col2.button(f"Encaissement ID {p[0]}"):
            conn = sqlite3.connect(DB_NAME)
            conn.cursor().execute("UPDATE patients SET statut='Payé' WHERE id=?", (p[0],))
            conn.commit(); conn.close(); st.rerun()

# --- MAIN ---
def main():
    init_db()
    if 'connecte' not in st.session_state: st.session_state['connecte'] = False

    if not st.session_state['connecte']:
        st.title("Login OphtaClinique")
        id_user = st.text_input("ID")
        pwd = st.text_input("Pass", type="password")
        if st.button("Connexion"):
            conn = sqlite3.connect(DB_NAME)
            res = conn.cursor().execute("SELECT role, mot_de_passe_hash FROM utilisateurs WHERE identifiant=?", (id_user,)).fetchone()
            if res and res[1] == hash_password(pwd):
                st.session_state.update({'connecte': True, 'role': res[0]})
                st.rerun()
            else: st.error("Login erroné")
            conn.close()
    else:
        role = st.session_state['role']
        if role == "Administrateur": interface_admin()
        elif role == "Médecin": interface_medecin()
        elif role == "Caisse": interface_caisse()
        
        if st.sidebar.button("Déconnexion"): st.session_state.clear(); st.rerun()

if __name__ == '__main__':
    main()