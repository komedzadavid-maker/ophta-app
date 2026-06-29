import streamlit as st
import sqlite3
import hashlib
import logging
from typing import Tuple, Optional, List, Any

# ==========================================
# CONFIGURATION GLOBALE ET LOGGING
# ==========================================
st.set_page_config(page_title="OphtaClinique Pro", page_icon="👁️", layout="centered")

# Configuration du journal des événements (Logs) pour la maintenance
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OphtaClinique")

DB_NAME = 'clinique.db'

# ==========================================
# COUCHE SÉCURITÉ (SECURITY LAYER)
# ==========================================
def hash_password(password: str) -> str:
    """
    Hache le mot de passe en utilisant l'algorithme SHA-256.
    
    Args:
        password (str): Le mot de passe en clair.
        
    Returns:
        str: L'empreinte cryptographique (hash) du mot de passe.
    """
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# ==========================================
# COUCHE DONNÉES (DATA LAYER)
# ==========================================
def init_db() -> None:
    """Initialise la base de données et crée les tables si elles n'existent pas."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            
            # Table Utilisateurs (RBAC)
            c.execute('''
                CREATE TABLE IF NOT EXISTS utilisateurs (
                    identifiant TEXT PRIMARY KEY,
                    mot_de_passe_hash TEXT NOT NULL,
                    role TEXT NOT NULL
                )
            ''')
            
            # Table Patients
            c.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom_complet TEXT NOT NULL,
                    telephone TEXT,
                    statut TEXT NOT NULL DEFAULT 'En attente',
                    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Création des utilisateurs par défaut pour le premier lancement
            c.execute("SELECT COUNT(*) FROM utilisateurs")
            if c.fetchone()[0] == 0:
                pwd_par_defaut = hash_password("password123")
                utilisateurs_test = [
                    ("secretaire_lome", pwd_par_defaut, "Caisse"),
                    ("dr_kossi", pwd_par_defaut, "Médecin")
                ]
                c.executemany(
                    "INSERT INTO utilisateurs (identifiant, mot_de_passe_hash, role) VALUES (?, ?, ?)", 
                    utilisateurs_test
                )
                conn.commit()
                logger.info("Base de données initialisée avec les comptes par défaut.")
    except sqlite3.Error as e:
        logger.error(f"Erreur critique lors de l'initialisation de la BD : {e}")
        st.error("Erreur système : Impossible de se connecter à la base de données.")

def verifier_connexion(identifiant: str, mot_de_passe: str) -> Tuple[bool, Optional[str]]:
    """
    Vérifie les identifiants de l'utilisateur.
    
    Returns:
        Tuple[bool, Optional[str]]: (Est_valide, Role_Utilisateur)
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("SELECT mot_de_passe_hash, role FROM utilisateurs WHERE identifiant = ?", (identifiant,))
            resultat = c.fetchone()
            
            if resultat:
                hash_stocke, role = resultat
                if hash_stocke == hash_password(mot_de_passe):
                    logger.info(f"Connexion réussie pour l'utilisateur : {identifiant}")
                    return True, role
                    
        logger.warning(f"Tentative de connexion échouée pour : {identifiant}")
        return False, None
    except sqlite3.Error as e:
        logger.error(f"Erreur BD lors de la vérification de connexion : {e}")
        return False, None

def ajouter_patient(nom_complet: str, telephone: str) -> bool:
    """Insère un nouveau patient dans la file d'attente."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO patients (nom_complet, telephone) VALUES (?, ?)", (nom_complet, telephone))
            conn.commit()
            logger.info(f"Nouveau patient enregistré : {nom_complet}")
        return True
    except sqlite3.Error as e:
        logger.error(f"Erreur lors de l'ajout du patient {nom_complet} : {e}")
        return False

def recuperer_patients_par_statut(statut: str) -> List[Tuple[Any, ...]]:
    """Récupère la liste des patients selon leur statut actuel."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, nom_complet, telephone, date_creation FROM patients WHERE statut = ? ORDER BY date_creation ASC", 
                (statut,)
            )
            return c.fetchall()
    except sqlite3.Error as e:
        logger.error(f"Erreur lors de la récupération des patients ({statut}) : {e}")
        return []

# ==========================================
# COUCHE PRÉSENTATION (FRONTEND / UI)
# ==========================================
def afficher_ecran_connexion() -> None:
    """Génère l'interface de connexion."""
    st.title("🔒 OphtaClinique - Portail Sécurisé")
    st.write("Veuillez saisir vos identifiants d'entreprise.")
    
    with st.form("formulaire_connexion"):
        identifiant = st.text_input("Identifiant").strip()
        mot_de_passe = st.text_input("Mot de passe", type="password")
        bouton_validation = st.form_submit_button("Se connecter", use_container_width=True)
        
        if bouton_validation:
            if not identifiant or not mot_de_passe:
                st.warning("⚠️ Veuillez remplir tous les champs.")
                return
                
            est_valide, role_utilisateur = verifier_connexion(identifiant, mot_de_passe)
            if est_valide:
                st.session_state['connecte'] = True
                st.session_state['identifiant'] = identifiant
                st.session_state['role'] = role_utilisateur
                st.rerun()
            else:
                st.error("❌ Identifiant ou mot de passe incorrect.")

def afficher_interface_caisse() -> None:
    """Génère l'interface dédiée au secrétariat et à la caisse."""
    st.title("💸 Module Caisse & Accueil")
    
    st.subheader("Enregistrer un nouveau patient")
    with st.form("formulaire_patient", clear_on_submit=True):
        nom_patient = st.text_input("Nom et Prénom du patient", max_chars=100)
        tel_patient = st.text_input("Numéro de téléphone (Optionnel)", max_chars=20)
        soumettre_patient = st.form_submit_button("Valider et mettre en attente")
        
        if soumettre_patient:
            if nom_patient.strip():
                if ajouter_patient(nom_patient.strip(), tel_patient.strip()):
                    st.success(f"Dossier créé pour '{nom_patient}'. Patient en attente.")
            else:
                st.warning("⚠️ Le nom du patient est obligatoire pour l'enregistrement.")
    
    st.subheader("État de la salle d'attente")
    patients_en_attente = recuperer_patients_par_statut("En attente")
    
    if patients_en_attente:
        for p in patients_en_attente:
            st.text(f"🆔 Dossier: #{p[0]} | 👤 Nom: {p[1]} | 📞 Tel: {p[2] if p[2] else 'N/D'}")
    else:
        st.info("La salle d'attente est actuellement vide.")

def afficher_interface_medecin() -> None:
    """Génère l'interface dédiée aux consultations médicales."""
    st.title("🩺 Module Clinique & Diagnostics")
    st.subheader("File d'attente médicale")
    
    patients_a_consulter = recuperer_patients_par_statut("En attente")
    
    if patients_a_consulter:
        st.write("Sélectionnez un dossier patient pour commencer la consultation :")
        for p in patients_a_consulter:
            heure_enregistrement = p[3][11:16] if p[3] else "N/D"
            with st.expander(f"👤 {p[1]} (Arrivée : {heure_enregistrement})"):
                st.write(f"**Contact :** {p[2] if p[2] else 'Non renseigné'}")
                st.button(f"Ouvrir le dossier clinique #{p[0]}", key=f"btn_visite_{p[0]}")
    else:
        st.success("🎉 Tous les patients ont été vus. Aucune consultation en attente.")

def main() -> None:
    """Point d'entrée principal de l'application."""
    init_db()
    
    if 'connecte' not in st.session_state:
        st.session_state['connecte'] = False

    if not st.session_state['connecte']:
        afficher_ecran_connexion()
    else:
        # Barre latérale (Sidebar) de gestion de session
        st.sidebar.title("👁️ OphtaClinique")
        st.sidebar.markdown("---")
        st.sidebar.write(f"👤 **Agent :** {st.session_state['identifiant']}")
        st.sidebar.write(f"🛡️ **Accès :** {st.session_state['role']}")
        st.sidebar.markdown("---")
        
        if st.sidebar.button("🚪 Déconnexion sécurisée", use_container_width=True):
            st.session_state.clear()
            st.rerun()
            
        # Routage selon le rôle (RBAC Routing)
        role = st.session_state.get('role')
        if role == "Caisse":
            afficher_interface_caisse()
        elif role == "Médecin":
            afficher_interface_medecin()
        else:
            st.error("Erreur de privilège : Rôle non reconnu par le système.")

if __name__ == '__main__':
    main()