import discord
from discord.ext import commands
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth import load_credentials_from_file
import re

# Load .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
CALENDAR_ID = os.getenv('CALENDAR_ID')

# Bot configuration
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# Set up Google Calendar service (Assume credentials.json is available)
def get_calendar_service():
    creds = None
    # Lisez les informations d'identification à partir du fichier token.json si disponible
    if os.path.exists('token.json'):
        creds, _ = load_credentials_from_file('token.json')

    # Si les identifiants sont invalides ou expirés, rafraîchissez-les
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("Les informations d'identification ne sont pas valides")

    # Build the service
    service = build('calendar', 'v3', credentials=creds)
    return service

# Function to get events from Google Calendar API
def get_events(service, date):
    # Convert the date to start and end of the day
    start_time = datetime.strptime(date, "%Y-%m-%d")
    end_time = start_time + timedelta(days=1)

    events_result = service.events().list(
        calendarId=CALENDAR_ID,  # Replace with the ID of your calendar
        timeMin=start_time.isoformat() + 'Z',  # Google Calendar uses UTC
        timeMax=end_time.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    return events

def clean_html_tags(text):
    # Supprimer les balises <br>
    text = text.replace('<br>', '\n')
    
    # Supprimer les attributs target="_blank"
    text = re.sub(r'target="_blank"', '', text)
    
    # Supprimer les balises <u>
    text = re.sub(r'</?u>', '', text)
    
    # Supprimer les attributs dir="ltr"
    text = re.sub(r'dir="ltr"', '', text)
    
    # Extraire les liens des balises <a>
    def replace_link(match):
        link_url = match.group(1)
        link_text = match.group(2)
        # Si le texte du lien est une URL, ne pas le répéter
        if link_text.startswith(('http://', 'https://', 'www.')):
            return link_url
        return f"{link_text}: {link_url}"
    
    # Remplacer les balises <a> par le format texte
    text = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(?:<u>)?([^<]+)(?:</u>)?</a>', replace_link, text)
    
    # Nettoyer les espaces multiples et les retours à la ligne
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()
    
    return text

@bot.command(name="tournament")
async def get_tournament(ctx, date: str = None):
    if date is None:
        await ctx.send("❌ Vous devez spécifier une date. Exemple : `!tournament 2025-01-17`, `!tournament today` ou `!tournament tomorrow`")
        return

    try:
        # Si l'argument est "today", utiliser la date du jour
        if date.lower() == "today":
            date = datetime.now().strftime("%Y-%m-%d")
        # Si l'argument est "tomorrow", utiliser la date de demain
        elif date.lower() == "tomorrow":
            date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Valider le format de la date
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        await ctx.send(f"Tournaments pour la date : {date_obj.strftime('%d %B %Y')}")
    except ValueError:
        await ctx.send("❌ Format de date invalide. Utilisez `YYYY-MM-DD`, `today` ou `tomorrow`. Exemple : `!tournament 2025-01-17`, `!tournament today` ou `!tournament tomorrow`")
        return

    # Appel à l'API Google Calendar
    url = f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events"
    params = {
        "key": GOOGLE_API_KEY,
        "timeMin": f"{date}T00:00:00Z",  # début de la journée en UTC
        "timeMax": f"{date}T23:59:59Z",  # fin de la journée en UTC
        "singleEvents": True,
        "orderBy": "startTime",
    }
    response = requests.get(url, params=params)

    events = response.json().get("items", [])

    if not events:
        await ctx.send(f"Aucun tournoi trouvé pour le {date}.")
    else:
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            event_date = start.split("T")[0]  # Extrait juste la date sans l'heure

            # Extraire l'heure de début si elle est présente
            event_time = ""
            if "dateTime" in event["start"]:
                event_time = datetime.fromisoformat(event["start"]["dateTime"]).strftime("%H:%M")
            else:
                event_time = "Non spécifié"  # Cas où il n'y a pas d'heure définie, juste une date
            
            if event_date == date:
                event_name = event['summary']
                event_link = event.get('htmlLink', 'Aucun lien disponible')
                description = event.get('description', '')
                
                # Récupération des informations de récurrence
                recurrence = event.get('recurrence', [])
                recurrence_info = ""
                if recurrence:
                    for rule in recurrence:
                        if 'RRULE' in rule:
                            recurrence_info = rule.split('RRULE:')[1].strip()
                            # Simplifier l'affichage de la récurrence
                            if 'FREQ=WEEKLY' in recurrence_info:
                                recurrence_info = "Toutes les semaines"
                            elif 'FREQ=MONTHLY' in recurrence_info:
                                recurrence_info = "Tous les mois"
                            elif 'FREQ=DAILY' in recurrence_info:
                                recurrence_info = "Tous les jours"

                # Formatage du message avec plus de détails
                message_event = f"**{event_name}**\n"
                
                # Ajout de la date formatée
                start_date = datetime.fromisoformat(start.split('T')[0])
                message_event += f"{start_date.strftime('%A, %d %B').capitalize()}\n"
                
                # Ajout de l'heure si spécifiée
                if event_time != "Non spécifié":
                    message_event += f"Début : {event_time}\n"
                
                # Ajout des informations de récurrence
                if recurrence_info:
                    message_event += f"{recurrence_info}\n"
                
                # Ajout de la description complète
                if description:
                    # Nettoyer les balises HTML de la description
                    clean_description = clean_html_tags(description)
                    message_event += f"\n{clean_description}\n"
                
                message_event += f"\n[Voir l'événement]({event_link})"

                # Envoyer un message séparé pour chaque tournoi
                await ctx.send(message_event)

# Run the bot
bot.run(TOKEN)