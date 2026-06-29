import streamlit as st
import sqlite3
import hashlib
import logging
from typing import Tuple, Optional, List, Any

# ==========================================
# CONFIGURATION ET LOGGING
# ==========================================
st.set_page_config(page_title="OphtaClinique Pro", page_icon="👁️", layout="wide")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_NAME = 'clinique.db'

# ==========================================
# COUCHE SÉCURITÉ ET DONNÉES
# ==========================================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    """Initialisation complète de la base de données."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Création des tables
    c.execute('''CREATE TABLE IF NOT EXISTS utilisateurs 
                 (identifiant TEXT PRIMARY KEY, mot_de_passe_hash TEXT NOT NULL, role TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS patients 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nom_complet TEXT NOT NULL, telephone TEXT, statut TEXT DEFAULT 'En attente')''')
    c.execute('''CREATE TABLE IF NOT EXISTS services 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nom_service TEXT NOT NULL, prix REAL NOT NULL)''')
    
    # Inserimento dati di default se le tabelle sono vuote
    c.execute("SELECT COUNT(*) FROM utilisateurs")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO utilisateurs VALUES (?, ?, ?)", ("admin_togo", hash_password("admin123"), "Administrateur"))
        c.execute("INSERT INTO utilisateurs VALUES (?, ?, ?)", ("secretaire_lome", hash_password("password123"), "Caisse"))
        c.execute("INSERT INTO utilisateurs VALUES (?, ?, ?)", ("dr_kossi", hash_password("password123"), "Médecin"))
        
    c.execute("SELECT COUNT(*) FROM services")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO services (nom_service, prix) VALUES (?, ?)", ("Consultation Standard", 5000))
        
    conn.commit()
    conn.close()

def get_services() -> List[Tuple[Any, ...]]:
    conn = sqlite3.connect(DB_NAME)
    res = conn.cursor().execute("SELECT * FROM services").fetchall()
    conn.close()
    return res

def ajouter_service(nom: str, prix: float):
    conn = sqlite3.connect(DB_NAME)
    conn.cursor().execute("INSERT INTO services (nom_service, prix) VALUES (?, ?)", (nom, prix))
    conn.commit()
    conn.close()

# ==========================================
# INTERFACES UI
# ==========================================
def afficher_ecran_connexion():
    st.title("🔒 OphtaClinique - Accès")
    with st.form("login"):
        id_user = st.text_input("Identifiant")
        pwd = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Connexion"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT mot_de_passe_hash, role FROM utilisateurs WHERE identifiant = ?", (id_user,))
            res = c.fetchone()
            if res and res[0] == hash_password(pwd):
                st.session_state.update({'connecte': True, 'identifiant': id_user, 'role': res[1]})
                st.rerun()
            else:
                st.error("Identifiants incorrects.")
            conn.close()

def afficher_interface_admin():
    st.title("👑 Panneau de Direction")
    tab1, tab2 = st.tabs(["📊 Tarifs & Services", "👥 Ressources Humaines"])
    with tab1:
        st.subheader("Catalogue des actes médicaux")
        services = get_services()
        for s in services:
            st.write(f"✅ **{s[1]}** : {s[2]} CFA")
        
        with st.form("new_service"):
            n = st.text_input("Nom du nouveau service")
            p = st.number_input("Prix (CFA)", min_value=0)
            if st.form_submit_button("Ajouter au catalogue"):
                ajouter_service(n, p)
                st.rerun()
    with tab2:
        st.write("Gestion des accès utilisateurs...")

def afficher_interface_medecin():
    st.title("🩺 Module Médecin")
    st.subheader("Catalogue des actes médicaux disponibles")
    services = get_services()
    if services:
        for s in services:
            st.write(f"🔹 **{s[1]}** : {s[2]} CFA")
    else:
        st.info("Aucun service configuré.")

def afficher_interface_caisse():
    st.title("💸 Module Caisse")
    st.write("Gestion des encaissements.")

# ==========================================
# ROUTAGE PRINCIPAL
# ==========================================
def main():
    init_db()
    if 'connecte' not in st.session_state:
        st.session_state['connecte'] = False

    if not st.session_state['connecte']:
        afficher_ecran_connexion()
    else:
        role = st.session_state.get('role')
        st.sidebar.title(f"Menu {role}")
        
        # Logique de navigation hiérarchique
        if role == "Administrateur":
            choix = st.sidebar.radio("Navigation", ["Direction", "Médecine", "Caisse"])
            if choix == "Direction": afficher_interface_admin()
            elif choix == "Médecine": afficher_interface_medecin()
            else: afficher_interface_caisse()
        elif role == "Médecin":
            afficher_interface_medecin()
        elif role == "Caisse":
            afficher_interface_caisse()

        if st.sidebar.button("Déconnexion"):
            st.session_state.clear()
            st.rerun()

if __name__ == '__main__':
    main()