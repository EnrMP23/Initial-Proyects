import requests
import matplotlib.pyplot as plt
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import io

# Configura tu clave API y los endpoints
API_KEY = '7dcb5906ce9b48cf9becc41685b38867'  # Reemplaza con tu clave API de football-data.org
BASE_URL = 'https://api.football-data.org/v4/matches'
TEAMS_URL = 'https://api.football-data.org/v4/teams'
STANDINGS_URL = 'https://api.football-data.org/v4/competitions/{league_id}/standings'

# Ligas de interés (IDs de las ligas)
LEAGUES = {
    'La Liga': 2014,    # Liga Española
    'Premier League': 2021,  # Liga Inglesa
    'Bundesliga': 2002,   # Liga Alemana
    'Ligue 1': 2015,   # Liga Francesa
    'Serie A (Italia)': 2019,
    'Champions League': 2001
}

# Personalización de la predicción
confidence_threshold = 0.65  # Umbral de confianza para mostrar predicciones

# Initialize the bot application
application = ApplicationBuilder().token("7309741382:AAETHbkJYLMha85xOyuvmdRTLm1WUPD2y0c").build()

# Set the webhook URL (this should be a URL publicly accessible from the internet)
application.bot.set_webhook(url="https://initial-proyects.onrender.com")

# Start the application listening for incoming webhooks
application.run_webhook(
    listen="0.0.0.0",  # Listen on all available interfaces
    port=8443,         # The port on your server
    url_path="your-webhook-url",  # Path that Telegram will send updates to
    webhook_url="https://initial-proyects.onrender.com"  # Full webhook URL
)


def get_matches(season='2024'):
    headers = {
        'X-Auth-Token': API_KEY
    }

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
    headers = {
        'X-Auth-Token': API_KEY
    }

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
                    'matchesPlayed': standing.get('matchesPlayed', 1),  # Usar 1 para evitar división por cero
                    'last5Games': standing.get('last5Games', [])
                }

    print(f"Error al obtener estadísticas del equipo {team_id}. Estado: {response.status_code}")
    return None

def get_last_5_games(team_id):
    headers = {
        'X-Auth-Token': API_KEY
    }

    response = requests.get(f"{TEAMS_URL}/{team_id}/matches?status=FINISHED", headers=headers)
    if response.status_code == 200:
        matches = response.json().get('matches', [])[-5:]  # Obtener solo los últimos 5 partidos
        return [{'homeTeam': match['homeTeam']['name'], 'awayTeam': match['awayTeam']['name'], 'score': match['score']['fullTime']} for match in matches]
    else:
        print(f"Error al obtener los últimos 5 partidos del equipo {team_id}. Estado: {response.status_code}")
        return []

def plot_probabilities(home_win_percentage, draw_percentage, away_win_percentage, home_team_name, away_team_name):
    labels = [home_team_name, 'Empate', away_team_name]
    sizes = [home_win_percentage, draw_percentage, away_win_percentage]
    colors = ['#ff9999', '#66b3ff', '#99ff99']

    plt.figure(figsize=(8, 5))
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title('Probabilidades de Resultado')

    # Guardar la gráfica en un buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)  # Volver al inicio del buffer
    plt.close()  # Cerrar la figura para liberar memoria
    return buf

def plot_last_5_games(home_last_5, away_last_5, home_team_name, away_team_name):
    # Ensure the score extraction is correct for both home and away teams
    home_scores = [game['score']['home'] for game in home_last_5]  # Extract home team scores
    away_scores = [game['score']['away'] for game in away_last_5]  # Extract away team scores

    plt.figure(figsize=(10, 5))
    plt.plot(range(1, 6), home_scores, marker='o', label=home_team_name, color='blue')
    plt.plot(range(1, 6), away_scores, marker='o', label=away_team_name, color='red')
    
    plt.xticks(range(1, 6), ['Partido 1', 'Partido 2', 'Partido 3', 'Partido 4', 'Partido 5'])
    plt.title('Rendimiento en los Últimos 5 Partidos')
    plt.xlabel('Partidos')
    plt.ylabel('Goles')
    plt.legend()
    
    # Save the plot in a buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)  # Go back to the beginning of the buffer
    plt.close()  # Close the figure to free memory
    return buf

def predict_result(home_team_id, away_team_id, league_id, home_team_name, away_team_name):
    home_stats = get_team_stats(home_team_id, league_id)
    away_stats = get_team_stats(away_team_id, league_id)

    if not home_stats or not away_stats:
        return None, None, None, None, None, None, None, None

    # Obtener los últimos 5 partidos
    home_last_5 = get_last_5_games(home_team_id)
    away_last_5 = get_last_5_games(away_team_id)

    # Cálculo de rendimiento
    home_goals_avg = home_stats['goalsFor'] / home_stats['matchesPlayed']
    away_goals_avg = away_stats['goalsFor'] / away_stats['matchesPlayed']
    home_goals_conceded_avg = home_stats['goalsAgainst'] / home_stats['matchesPlayed']
    away_goals_conceded_avg = away_stats['goalsAgainst'] / away_stats['matchesPlayed']

    # Estimaciones de goles (ajustando para realismo)
    estimated_home_goals = (home_goals_avg + away_goals_conceded_avg) / 2
    estimated_away_goals = (away_goals_avg + home_goals_conceded_avg) / 2

    # Probabilidades basadas en las estimaciones de goles
    total_goals = estimated_home_goals + estimated_away_goals

    if total_goals > 0:
        home_win_percentage = (estimated_home_goals / total_goals) * 100
        away_win_percentage = (estimated_away_goals / total_goals) * 100
    else:
        home_win_percentage = 50
        away_win_percentage = 50

    # Añadir un porcentaje base para el empate
    draw_percentage = 100 - (home_win_percentage + away_win_percentage)
    if draw_percentage < 10:
        draw_percentage = 10

    # Normalizar porcentajes
    total_adjusted = home_win_percentage + away_win_percentage + draw_percentage
    home_win_percentage = (home_win_percentage / total_adjusted) * 100
    away_win_percentage = (away_win_percentage / total_adjusted) * 100
    draw_percentage = (draw_percentage / total_adjusted) * 100

    # Determinación del resultado
    if home_win_percentage > away_win_percentage and home_win_percentage > draw_percentage:
        result = f"{home_team_name} ganará"
        winning_team = home_team_name
    elif away_win_percentage > home_win_percentage and away_win_percentage > draw_percentage:
        result = f"{away_team_name} ganará"
        winning_team = away_team_name
    else:
        result = "Empate"
        winning_team = "Ninguno (Empate)"

    # Verificar la confianza en la predicción
    if home_win_percentage >= confidence_threshold * 100:
        result += f" (Alta confianza en la victoria de {home_team_name})"
    elif away_win_percentage >= confidence_threshold * 100:
        result += f" (Alta confianza en la victoria de {away_team_name})"
    else:
        result += " (Baja confianza en la predicción)"

    return result, home_win_percentage, draw_percentage, away_win_percentage, home_last_5, away_last_5


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    matches = get_matches()
    if matches:
        match_list = "\n".join([f"{match['id']}: {match['homeTeam']['name']} vs {match['awayTeam']['name']}" for match in matches])
        await update.message.reply_text(f"Aquí está la lista de partidos disponibles:\n{match_list}\n\nUsa /predict <match_id> para predecir el resultado de un partido.")
    else:
        await update.message.reply_text("No hay partidos disponibles en este momento.")


async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text("Por favor, proporciona un ID de partido válido.")
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

        result, win_percentage, draw_percentage, lose_percentage, home_last_5, away_last_5 = predict_result(
            home_team_id, away_team_id, league_id, home_team_name, away_team_name)

        if result:
            await update.message.reply_text(result)

            # Send the probability pie chart
            buf = plot_probabilities(win_percentage, draw_percentage, lose_percentage, home_team_name, away_team_name)
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=buf)

            # Send the last 5 games performance chart
            buf_last_5 = plot_last_5_games(home_last_5, away_last_5, home_team_name, away_team_name)
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=buf_last_5)
        else:
            await update.message.reply_text("No se pudo realizar la predicción debido a la falta de datos.")
    else:
        await update.message.reply_text("Error al obtener datos del partido. Asegúrate de que el ID del partido es válido.")


# Register command handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("predict", predict))

# Start the application
if __name__ == "__main__":
    print('¡EXITO Y SUERTE!')
    application.run_polling()  # This line can be adjusted based on your webhook settings

    

