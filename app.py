import streamlit as st
import sqlite3
import hashlib
import logging
from typing import Tuple, Optional, List, Any

# Configurazione globale
st.set_page_config(page_title="OphtaClinique Pro", page_icon="👁️", layout="wide")
DB_NAME = 'clinique.db'

# --- FUNZIONI DI SICUREZZA ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS utilisateurs (identifiant TEXT PRIMARY KEY, mot_de_passe_hash TEXT NOT NULL, role TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS patients (id INTEGER PRIMARY KEY AUTOINCREMENT, nom_complet TEXT NOT NULL, telephone TEXT, statut TEXT DEFAULT 'En attente')''')
        c.execute('''CREATE TABLE IF NOT EXISTS services (id INTEGER PRIMARY KEY AUTOINCREMENT, nom_service TEXT NOT NULL, prix REAL NOT NULL)''')
        
        # Inizializzazione se il DB è vuoto
        c.execute("SELECT COUNT(*) FROM utilisateurs")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO utilisateurs VALUES (?, ?, ?)", ("admin_togo", hash_password("admin123"), "Administrateur"))
            c.execute("INSERT INTO utilisateurs VALUES (?, ?, ?)", ("secretaire_lome", hash_password("password123"), "Caisse"))
            c.execute("INSERT INTO utilisateurs VALUES (?, ?, ?)", ("dr_kossi", hash_password("password123"), "Médecin"))
            c.execute("INSERT INTO services (nom_service, prix) VALUES (?, ?)", ("Consultation Standard", 5000))
        conn.commit()

def verifier_connexion(identifiant: str, mot_de_passe: str) -> Tuple[bool, Optional[str]]:
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT mot_de_passe_hash, role FROM utilisateurs WHERE identifiant = ?", (identifiant,))
        resultat = c.fetchone()
        if resultat and resultat[0] == hash_password(mot_de_passe):
            return True, resultat[1]
    return False, None

# --- FUNZIONI DATI ---
def get_services() -> List[Tuple[Any, ...]]:
    with sqlite3.connect(DB_NAME) as conn:
        return conn.cursor().execute("SELECT * FROM services").fetchall()

def ajouter_service(nom: str, prix: float):
    with sqlite3.connect(DB_NAME) as conn:
        conn.cursor().execute("INSERT INTO services (nom_service, prix) VALUES (?, ?)", (nom, prix))
        conn.commit()

# --- INTERFACCE ---
def afficher_ecran_connexion():
    st.title("🔒 OphtaClinique - Accès")
    with st.form("login"):
        id_user = st.text_input("Identifiant")
        pwd = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Connexion"):
            valide, role = verifier_connexion(id_user, pwd)
            if valide:
                st.session_state['connecte'] = True
                st.session_state['identifiant'] = id_user
                st.session_state['role'] = role
                st.rerun()
            else:
                st.error("Identifiants incorrects.")

def afficher_interface_caisse():
    st.title("💸 Module Caisse")
    st.write("Gestion des encaissements.")

def afficher_interface_medecin():
    st.title("🩺 Module Médecin")
    services = get_services()
    st.write("Catalogue des actes :", services)

def afficher_interface_admin():
    st.title("👑 Panneau de Direction")
    tab1, tab2 = st.tabs(["📊 Tarifs & Services", "👥 Ressources Humaines"])
    with tab1:
        st.subheader("Modifier les tarifs")
        with st.form("new_service"):
            n = st.text_input("Nom du service")
            p = st.number_input("Prix", min_value=0)
            if st.form_submit_button("Ajouter"):
                ajouter_service(n, p)
                st.rerun()
    with tab2:
        st.write("Gestion des accès utilisateurs...")

# --- MAIN ROUTER ---
def main():
    init_db()
    if 'connecte' not in st.session_state:
        st.session_state['connecte'] = False

    if not st.session_state['connecte']:
        afficher_ecran_connexion()
    else:
        role = st.session_state.get('role')
        st.sidebar.title(f"Menu {role}")
        
        # Logique di navigazione gerarchica
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