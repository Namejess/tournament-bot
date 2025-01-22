import discord
from discord.ext import commands
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.auth import load_credentials_from_file

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

@bot.command(name="tournament")
async def get_tournament(ctx, date: str = None):
    if date is None:
        await ctx.send("❌ Vous devez spécifier une date. Exemple : `!tournament 2025-01-17`")
        return

    try:
        # Valider le format de la date
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        await ctx.send(f"Tournaments pour la date : {date_obj.strftime('%d %B %Y')}")
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

    events = response.json().get("items", [])

    if not events:
        await ctx.send(f"Aucun tournoi trouvé pour le {date}.")
    else:
        message = f"**Tournois pour le {date} :**\n"
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
                event_link = event.get('htmlLink', 'Aucun lien disponible')  # Lien de l'événement
                description = event.get('description', '')

                # Récupération des autres données de description comme les liens (si présents)
                info_link = event.get('description', '').split('Infos : ')[-1] if 'Infos : ' in description else ''
                signup_link = event.get('description', '').split('Inscriptions : ')[-1] if 'Inscriptions : ' in description else ''
                twitch_link = event.get('description', '').split('Twitch : ')[-1] if 'Twitch : ' in description else ''
                note = event.get('description', '').split('Note : ')[-1] if 'Note : ' in description else ''

                # Formatage des liens dans le message
                message_event = f"**{event_name}**\nDébut : {event_time}\n[Voir l'événement]({event_link})\n"
                
                if info_link:
                    message_event += f"🔗 Infos : [{info_link}]({info_link})\n"
                if signup_link:
                    message_event += f"🔗 Inscriptions : [{signup_link}]({signup_link})\n"
                if twitch_link:
                    message_event += f"🔗 Twitch : [{twitch_link}]({twitch_link})\n"
                if note:
                    message_event += f"📝 Note : {note}\n"

                message_event += "\n"

                # Si le message dépasse la limite de 2000 caractères, on l'envoie et on recommence
                if len(message + message_event) > 2000:
                    await ctx.send(message)
                    message = ""  # Réinitialiser le message pour le prochain envoi
                message += message_event

        # Envoi du message restant s'il y en a un
        if message:
            await ctx.send(message)

# Run the bot
bot.run(TOKEN)