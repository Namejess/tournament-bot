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

# Command to query events for a given date
@bot.command(name="tournament")
async def get_tournament(ctx, date: str= None):
    if date is None:
        await ctx.send("❌ Vous devez spécifier une date. Exemple : `!tournament 2025-01-17`")
        return

    # Validate the date format
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        await ctx.send(f"Tournament pour la date : {date_obj.strftime('%d %B %Y')}")
    except ValueError:
        await ctx.send("❌ Format de date invalide. Utilisez `YYYY-MM-DD`. Exemple : `!tournament 2025-01-17`")
        return

    try:
        # Get the calendar service
        service = get_calendar_service()

        # Get events from Google Calendar
        events = get_events(service, date)

        # Format the response
        if not events:
            await ctx.send(f"Aucun tournoi trouvé pour le {date}.")
        else:
            message = f"Tournois pour le {date} :\n"
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                message += f"- {event['summary']} (début : {start})\n"
            await ctx.send(message)

    except Exception as e:
        await ctx.send(f"Une erreur est survenue : {e}")

# Run the bot
bot.run(TOKEN)