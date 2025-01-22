from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import os

# Définir les autorisations nécessaires pour l'API Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def authenticate_google_account():
    creds = None
    
    # Si le fichier token.json existe déjà, essaye de l'utiliser
    if os.path.exists('token.json'):
        creds = None  # On ne va pas utiliser celui-là car il est corrompu
    
    # Si aucune information d'identification n'est valide, demande à l'utilisateur de s'authentifier
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Utiliser le fichier credentials.json pour obtenir un nouveau token
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)  # 'credentials.json' est ton fichier d'authentification
            creds = flow.run_local_server(port=0)

        # Sauvegarder les informations d'identification dans token.json pour les réutiliser à l'avenir
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

# Appel de la fonction pour créer ou actualiser les informations d'identification
authenticate_google_account()