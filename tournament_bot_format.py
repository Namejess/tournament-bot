import discord
from discord.ext import commands
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import html
import re
from bs4 import BeautifulSoup

# Load .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Bot configuration
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Google Calendar API configuration
GOOGLE_API_KEY = "AIzaSyATql_wEgjDLLQFqfxA8OOhj4nsWrdxVsQ"
CALENDAR_ID = "aniskxhmifgc@gmail.com"

# Function to clean the description (remove HTML, unescape entities, and extract links)
# Function to clean the description (remove HTML, unescape entities, and extract links)
def clean_description(description):
    # Nettoyer les entités HTML (comme \xa0 pour l'espace insécable)
    description = html.unescape(description)  # Décodage des entités HTML

    # Supprimer les espaces insécables (\xa0)
    description = description.replace('\xa0', ' ')

    # Utiliser BeautifulSoup pour supprimer les balises HTML (comme <a href=...>)
    soup = BeautifulSoup(description, "html.parser")
    clean_text = soup.get_text(separator="\n")  # Séparer les parties par des sauts de ligne

    # Transformer les liens Markdown [texte](url) pour les garder intacts
    clean_text = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'[\1](\2)', clean_text)

    # Ajouter https:// pour les liens relatifs (qui commencent par //)
    clean_text = re.sub(r'//([^\s]+)', r'https://\1', clean_text)

    # Séparer les sections importantes comme Discord et Note sur des lignes distinctes
    clean_text = re.sub(r'(Discord :)', r'\n\1', clean_text)
    clean_text = re.sub(r'(Note :)', r'\n\1', clean_text)

    # Nettoyer les espaces superflus
    clean_text = ' '.join(clean_text.split())  # Enlever les espaces superflus

    return clean_text

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

@bot.command(name="tournament")
async def get_tournament(ctx, date: str = None):
    if date is None:
        await ctx.send("❌ Vous devez spécifier une date. Exemple : `!tournament 2025-01-17`")
        return

    try:
        # Valider le format de la date
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        await ctx.send(f"**Tournois pour la date : {date_obj.strftime('%d %B %Y')}**")
    except ValueError:
        await ctx.send("❌ Format de date invalide. Utilisez `YYYY-MM-DD`. Exemple : `!tournament 2025-01-17`")
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

    events = response.json()  # Les données brutes de l'API

    # Vérifie s'il y a des événements et les envoie par morceaux
    if not events.get('items'):
        await ctx.send(f"Aucun tournoi trouvé pour le {date}.")
    else:
        # Formatage des événements de manière concise
        events_data = ""
        for event in events.get('items', []):
            event_name = event.get('summary', 'Nom inconnu')
            event_link = event.get('htmlLink', 'Aucun lien disponible')
            description = event.get('description', '')

            # Nettoyer la description de tout HTML et récupérer les liens
            cleaned_description = clean_description(description)

            # Création d'un message pour chaque événement
            event_message = f"**{event_name}**\n🔗[Voir l'événement]({event_link})\n"

            # Extraction des liens de la description
            if cleaned_description:
                print(event_message)
                event_message += f"🔗 {cleaned_description}\n"  # Ajouter chaque description propre

            events_data += event_message + "\n"  # Ajouter un événement à la liste

        # Diviser en morceaux si nécessaire
        max_message_length = 2000
        for i in range(0, len(events_data), max_message_length):
            await ctx.send(events_data[i:i+max_message_length])  # Envoie chaque morceau

# Run the bot
bot.run(TOKEN)