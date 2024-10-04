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
    'La Liga': 2014,    # Liga Española
    'Premier League': 2021,  # Liga Inglesa
    'Bundesliga': 2002,   # Liga Alemana
    'Ligue 1': 2015,   # Liga Francesa
    'Serie A (Italia)': 2019,
    'Champions League': 2001
}

# Personalización de la predicción
confidence_threshold = 0.65  # Umbral de confianza para mostrar predicciones

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
    home_scores = []
    away_scores = []

    # Revisar todos los partidos del equipo 1 (home team)
    for game in home_last_5:
        if game['homeTeam'] == home_team_name:
            # Si el equipo es local, tomar los goles del equipo local
            home_scores.append(game['score']['home'])
        else:
            # Si el equipo es visitante, tomar los goles del equipo visitante
            home_scores.append(game['score']['away'])

    # Revisar todos los partidos del equipo 2 (away team)
    for game in away_last_5:
        if game['awayTeam'] == away_team_name:
            # Si el equipo es visitante, tomar los goles del equipo visitante
            away_scores.append(game['score']['away'])
        else:
            # Si el equipo es local, tomar los goles del equipo local
            away_scores.append(game['score']['home'])

    # Gráfica ajustada
    plt.figure(figsize=(10, 5))
    plt.plot(range(1, 6), home_scores, marker='o', label=home_team_name, color='blue')
    plt.plot(range(1, 6), away_scores, marker='o', label=away_team_name, color='red')
    plt.xticks(range(1, 6), ['Partido 1', 'Partido 2', 'Partido 3', 'Partido 4', 'Partido 5'])
    plt.title('Rendimiento en los Últimos 5 Partidos')
    plt.xlabel('Partidos')
    plt.ylabel('Goles')
    plt.legend()

    # Guardar la gráfica en un buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)  # Volver al inicio del buffer
    plt.close()  # Cerrar la figura para liberar memoria
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
        result += f" (Alta confianza en que {home_team_name} ganará)"
    elif away_win_percentage >= confidence_threshold * 100:
        result += f" (Alta confianza en que {away_team_name} ganará)"
    else:
        result += " (Confianza baja en la predicción)"

    return result, winning_team, home_win_percentage, draw_percentage, away_win_percentage, home_last_5, away_last_5, home_stats, away_stats

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Obtener los partidos disponibles
    matches = get_matches()
    if matches:
        match_list = "\n".join([f"{match['id']}: {match['homeTeam']['name']} vs {match['awayTeam']['name']}" for match in matches])
        await update.message.reply_text(f"¡Hola! Aquí tienes la lista de partidos disponibles:\n{match_list}\n\nUsa /predict <match_id> para predecir el resultado de un partido.")
    else:
        await update.message.reply_text("No se encontraron partidos disponibles en este momento, intentalo mas tarde o a las 17:00 horas para actualización.")

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

            # Mensaje sobre la predicción
            await update.message.reply_text(f"Predicción: {result}")

            # Graficar probabilidades y enviar imagen
            prob_buf = plot_probabilities(win_percentage, draw_percentage, lose_percentage, home_team_name, away_team_name)
            await update.message.reply_photo(photo=prob_buf)

            # Graficar rendimiento de los últimos 5 partidos
            performance_buf = plot_last_5_games(home_last_5, away_last_5, home_team_name, away_team_name)
            await update.message.reply_photo(photo=performance_buf)

            # Mostrar los últimos 5 partidos
            home_last_games_text = f"\nÚltimos 5 partidos de {home_team_name}:\n\n" + "\n".join([f"{game['homeTeam']} {game['score']['home']} - {game['score']['away']} {game['awayTeam']}" for game in home_last_5])
            away_last_games_text = f"\n\nÚltimos 5 partidos de {away_team_name}:\n\n" + "\n".join([f"{game['homeTeam']} {game['score']['home']} - {game['score']['away']} {game['awayTeam']}" for game in away_last_5])
            await update.message.reply_text(home_last_games_text + away_last_games_text)

            # Mostrar estadísticas avanzadas
            advanced_stats_text = (
                f"\n\nEstadísticas Avanzadas:\n"
                f"{home_team_name} - Goles: {home_stats['goalsFor']}, Goles en Contra: {home_stats['goalsAgainst']}, Puntos: {home_stats['points']}\n"
                f"{away_team_name} - Goles: {away_stats['goalsFor']}, Goles en Contra: {away_stats['goalsAgainst']}, Puntos: {away_stats['points']}"
            )
            await update.message.reply_text(advanced_stats_text)

    else:
        await update.message.reply_text("Error al obtener los datos del partido.")
        
def get_match_stats(match_id):
    headers = {'X-Auth-Token': API_KEY}
    response = requests.get(f"{BASE_URL}/matches/{match_id}", headers=headers)

    if response.status_code == 200:
        match = response.json()
        home_shots_on_target = match['homeTeam']['statistics']['shotsOnTarget']
        away_shots_on_target = match['awayTeam']['statistics']['shotsOnTarget']
        
        return home_shots_on_target, away_shots_on_target
    else:
        return None, None


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
    
    print('SIUUUUUUUUH')
