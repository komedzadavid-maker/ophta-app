import streamlit as st
import sqlite3
import hashlib
import logging
from typing import Tuple, Optional, List, Any

# Configuration globale
st.set_page_config(page_title="OphtaClinique Pro", page_icon="👁️", layout="wide")
DB_NAME = 'clinique.db'

# --- FONCTIONS SYSTÈME ET SÉCURITÉ ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS utilisateurs (identifiant TEXT PRIMARY KEY, mot_de_passe_hash TEXT NOT NULL, role TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS patients (id INTEGER PRIMARY KEY AUTOINCREMENT, nom_complet TEXT NOT NULL, telephone TEXT, statut TEXT DEFAULT 'En attente')''')
        c.execute('''CREATE TABLE IF NOT EXISTS services (id INTEGER PRIMARY KEY AUTOINCREMENT, nom_service TEXT NOT NULL, prix REAL NOT NULL)''')
        
        # Initialisation si vide
        c.execute("SELECT COUNT(*) FROM utilisateurs")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO utilisateurs VALUES (?, ?, ?)", ("admin_togo", hash_password("admin123"), "Administrateur"))
            c.execute("INSERT INTO services (nom_service, prix) VALUES (?, ?)", ("Consultation Standard", 5000))
        conn.commit()

# --- FONCTIONS DE DONNÉES (SERVICES & PATIENTS) ---
def get_services() -> List[Tuple[Any, ...]]:
    with sqlite3.connect(DB_NAME) as conn:
        return conn.cursor().execute("SELECT * FROM services").fetchall()

def ajouter_service(nom: str, prix: float):
    with sqlite3.connect(DB_NAME) as conn:
        conn.cursor().execute("INSERT INTO services (nom_service, prix) VALUES (?, ?)", (nom, prix))
        conn.commit()

def recuperer_patients_par_statut(statut: Optional[str] = None):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        if statut:
            c.execute("SELECT * FROM patients WHERE statut = ?", (statut,))
        else:
            c.execute("SELECT * FROM patients")
        return c.fetchall()

# --- INTERFACES (LES BLOCS RÉUTILISABLES) ---
def afficher_interface_caisse():
    st.title("💸 Module Caisse")
    st.write("Gestion des encaissements et accueil.")
    # (Logique de caisse ici...)

def afficher_interface_medecin():
    st.title("🩺 Module Médecin")
    st.write("Dossiers patients et diagnostics.")
    # Accès au catalogue (le médecin lit les prix, il ne les change pas)
    services = get_services()
    st.write("Catalogue des actes :", services)

def afficher_interface_admin():
    st.title("👑 Panneau de Direction")
    tab1, tab2 = st.tabs(["📊 Tarifs & Services", "👥 Ressources Humaines"])
    
    with tab1:
        st.subheader("Modifier les tarifs")
        with st.form("new_service"):
            n = st.text_input("Nom du service")
            p = st.number_input("Prix")
            if st.form_submit_button("Ajouter"):
                ajouter_service(n, p)
                st.rerun()
    with tab2:
        st.write("Gestion des utilisateurs...")

# --- ROUTEUR PRINCIPAL (HIÉRARCHIQUE) ---
def main():
    init_db()
    if 'connecte' not in st.session_state: st.session_state['connecte'] = False

    if not st.session_state['connecte']:
        # [Logique de login inchangée...]
        # (Pour abréger, je l'ai omise ici, garde celle que tu as déjà)
        pass 
    else:
        role = st.session_state.get('role')
        st.sidebar.title(f"Menu {role}")
        
        # LOGIQUE HIÉRARCHIQUE :
        # L'Administrateur voit TOUT
        if role == "Administrateur":
            choix = st.sidebar.radio("Navigation", ["Direction", "Médecine", "Caisse"])
            if choix == "Direction":
                afficher_interface_admin()
            elif choix == "Médecine":
                afficher_interface_medecin()
            else:
                afficher_interface_caisse()
        
        # Le Médecin voit le médecin
        elif role == "Médecin":
            afficher_interface_medecin()
            
        # La Caisse voit la caisse
        elif role == "Caisse":
            afficher_interface_caisse()

if __name__ == '__main__':
    main()