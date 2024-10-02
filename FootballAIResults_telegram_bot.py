import requests
import matplotlib.pyplot as plt
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import io
import os

# Configura las variables de entorno
API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "7dcb5906ce9b48cf9becc41685b38867")  # API key de football-data.org
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7309741382:AAETHbkJYLMha85xOyuvmdRTLm1WUPD2y0c")  # Token de Telegram
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://initial-proyects.onrender.com/webhook")  # URL del webhook

# Endpoints de la API
BASE_URL = 'https://api.football-data.org/v4/matches'
TEAMS_URL = 'https://api.football-data.org/v4/teams'
STANDINGS_URL = 'https://api.football-data.org/v4/competitions/{league_id}/standings'

# Ligas de interés (IDs de las ligas)
LEAGUES = {
    'La Liga': 2014,    
    'Premier League': 2021,
    'Bundesliga': 2002,
    'Ligue 1': 2015,
    'Serie A (Italia)': 2019,
    'Champions League': 2001
}

confidence_threshold = 0.6  # Umbral de confianza para predicciones

def get_matches(season='2024'):
    headers = {'X-Auth-Token': API_KEY}
    matches = []
    for league_name, league_id in LEAGUES.items():
        response = requests.get(f"{BASE_URL}?competitions={league_id}&season={season}", headers=headers)
        if response.status_code == 200:
            league_matches = response.json().get('matches', [])
            matches.extend(league_matches)
        else:
            print(f"Error al obtener partidos de {league_name}. Estado: {response.status_code}")
    return matches

def get_team_stats(team_id, league_id):
    headers = {'X-Auth-Token': API_KEY}
    response = requests.get(STANDINGS_URL.format(league_id=league_id), headers=headers)
    if response.status_code == 200:
        standings_data = response.json()
        for standing in standings_data['standings'][0]['table']:
            if standing['team']['id'] == team_id:
                return {
                    'position': standing.get('position', None),
                    'points': standing.get('points', 0),
                    'goalsFor': standing.get('goalsFor', 0),
                    'goalsAgainst': standing.get('goalsAgainst', 0),
                    'goalDifference': standing.get('goalsFor', 0) - standing.get('goalsAgainst', 0),
                    'matchesPlayed': standing.get('matchesPlayed', 1),
                    'last5Games': standing.get('last5Games', [])
                }
    print(f"Error al obtener estadísticas del equipo {team_id}. Estado: {response.status_code}")
    return None

def plot_probabilities(home_win_percentage, draw_percentage, away_win_percentage, home_team_name, away_team_name):
    labels = [home_team_name, 'Empate', away_team_name]
    sizes = [home_win_percentage, draw_percentage, away_win_percentage]
    colors = ['#ff9999', '#66b3ff', '#99ff99']
    plt.figure(figsize=(8, 5))
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')  
    plt.title('Probabilidades de Resultado')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)  
    plt.close()  
    return buf

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    matches = get_matches()
    if matches:
        match_list = "\n".join([f"{match['id']}: {match['homeTeam']['name']} vs {match['awayTeam']['name']}" for match in matches])
        await update.message.reply_text(f"¡Hola! Aquí tienes la lista de partidos disponibles:\n{match_list}\n\nUsa /predict <match_id> para predecir el resultado de un partido.")
    else:
        await update.message.reply_text("No se encontraron partidos disponibles en este momento.")

async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("Por favor proporciona un ID de partido válido.")
        return

    match_id = int(context.args[0])
    match_response = requests.get(f"{BASE_URL}/{match_id}", headers={'X-Auth-Token': API_KEY})
    if match_response.status_code == 200:
        match_data = match_response.json()
        home_team_id = match_data['homeTeam']['id']
        away_team_id = match_data['awayTeam']['id']
        league_id = match_data['competition']['id']
        home_team_name = match_data['homeTeam']['name']
        away_team_name = match_data['awayTeam']['name']

        result, winning_team, win_percentage, draw_percentage, lose_percentage, home_last_5, away_last_5, home_stats, away_stats = predict_result(
            home_team_id, away_team_id, league_id, home_team_name, away_team_name)

        if result:
            league_info = f"{home_team_name} (Posición: {home_stats['position']}, Puntos: {home_stats['points']}) vs {away_team_name} (Posición: {away_stats['position']}, Puntos: {away_stats['points']})"
            await update.message.reply_text(league_info)

            await update.message.reply_text(f"Predicción: {result}")

            prob_buf = plot_probabilities(win_percentage, draw_percentage, lose_percentage, home_team_name, away_team_name)
            await update.message.reply_photo(photo=prob_buf)
    else:
        await update.message.reply_text("Error al obtener los datos del partido.")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("predict", predict))

    application.run_webhook(
        listen="0.0.0.0",
        port=8443,
        url_path="/webhook",
        webhook_url=WEBHOOK_URL
    )
