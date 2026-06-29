import streamlit as st
import sqlite3
import hashlib
from typing import List, Any

# ==========================================
# CONFIGURATION ET DB
# ==========================================
st.set_page_config(page_title="OphtaClinique Pro", page_icon="👁️", layout="wide")
DB_NAME = 'clinique.db'

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tabelle
    c.execute('''CREATE TABLE IF NOT EXISTS utilisateurs (identifiant TEXT PRIMARY KEY, mot_de_passe_hash TEXT NOT NULL, role TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS services (id INTEGER PRIMARY KEY AUTOINCREMENT, nom_service TEXT NOT NULL, prix REAL NOT NULL)''')
    
    # Init dati
    c.execute("SELECT COUNT(*) FROM utilisateurs")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO utilisateurs VALUES (?, ?, ?)", ("admin_togo", hash_password("admin123"), "Administrateur"))
        c.execute("INSERT INTO utilisateurs VALUES (?, ?, ?)", ("dr_kossi", hash_password("password123"), "Médecin"))
        c.execute("INSERT INTO utilisateurs VALUES (?, ?, ?)", ("caisse_lome", hash_password("password123"), "Caisse"))
    
    c.execute("SELECT COUNT(*) FROM services")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO services (nom_service, prix) VALUES (?, ?)", ("Consultation Standard", 5000))
    conn.commit()
    conn.close()

# ==========================================
# LOGIQUE GESTION SERVICES (Commune Admin/Medecin)
# ==========================================
def afficher_gestion_services():
    st.subheader("🛠 Gestion du Catalogue des Actes")
    services = sqlite3.connect(DB_NAME).cursor().execute("SELECT * FROM services").fetchall()
    
    # Visualizzazione Lista
    for s in services:
        st.write(f"🔹 **{s[1]}** : {s[2]} CFA")
    
    # Form aggiunta
    with st.form("add_service"):
        nom = st.text_input("Nom du nouveau service")
        prix = st.number_input("Prix (CFA)", min_value=0)
        if st.form_submit_button("Ajouter au catalogue"):
            conn = sqlite3.connect(DB_NAME)
            conn.cursor().execute("INSERT INTO services (nom_service, prix) VALUES (?, ?)", (nom, prix))
            conn.commit()
            conn.close()
            st.rerun()

# ==========================================
# INTERFACES
# ==========================================
def afficher_interface_admin():
    st.title("👑 Panneau Administration")
    tab1, tab2 = st.tabs(["📊 Gestion Services", "👥 Gestion Personnel"])
    with tab1:
        afficher_gestion_services()
    with tab2:
        st.write("Interface de gestion des utilisateurs...")

def afficher_interface_medecin():
    st.title("🩺 Module Médecin")
    tab1, tab2 = st.tabs(["📝 Consultations", "🛠 Gestion Prix"])
    with tab1:
        st.write("Gestion des patients...")
    with tab2:
        afficher_gestion_services() # Il Medico può gestire i prezzi

def afficher_interface_caisse():
    st.title("💸 Module Caisse")
    st.write("Interface de paiement.")

# ==========================================
# ROUTEUR PRINCIPAL
# ==========================================
def main():
    init_db()
    if 'connecte' not in st.session_state: st.session_state['connecte'] = False

    if not st.session_state['connecte']:
        # Login standard
        with st.form("login"):
            id_user = st.text_input("Identifiant")
            pwd = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Connexion"):
                conn = sqlite3.connect(DB_NAME)
                res = conn.cursor().execute("SELECT role, mot_de_passe_hash FROM utilisateurs WHERE identifiant = ?", (id_user,)).fetchone()
                if res and res[1] == hash_password(pwd):
                    st.session_state.update({'connecte': True, 'role': res[0]})
                    st.rerun()
                else: st.error("Erreur")
    else:
        role = st.session_state.get('role')
        if role == "Administrateur": afficher_interface_admin()
        elif role == "Médecin": afficher_interface_medecin()
        elif role == "Caisse": afficher_interface_caisse()
        
        if st.sidebar.button("Déconnexion"):
            st.session_state.clear()
            st.rerun()

if __name__ == '__main__':
    main()