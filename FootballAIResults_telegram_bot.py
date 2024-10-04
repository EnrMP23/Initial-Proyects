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

# Personalización de la predicción
confidence_threshold = 0.65  # Umbral de confianza para mostrar predicciones

# Funciones para obtener partidos, estadísticas y gráficos
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
                }
    print(f"Error al obtener estadísticas del equipo {team_id}. Estado: {response.status_code}")
    return None

def get_last_5_games(team_id):
    headers = {'X-Auth-Token': API_KEY}
    response = requests.get(f"{TEAMS_URL}/{team_id}/matches?status=FINISHED", headers=headers)
    if response.status_code == 200:
        matches = response.json().get('matches', [])[-5:]
        return [{'homeTeam': match['homeTeam']['name'], 'awayTeam': match['awayTeam']['name'], 'score': match['score']['fullTime']} for match in matches]
    else:
        print(f"Error al obtener los últimos 5 partidos del equipo {team_id}. Estado: {response.status_code}")
        return []

def get_home_away_performance(team_id):
    headers = {'X-Auth-Token': API_KEY}
    response = requests.get(f"{TEAMS_URL}/{team_id}/matches?status=FINISHED", headers=headers)
    
    if response.status_code == 200:
        matches = response.json().get('matches', [])
        home_games = [match for match in matches if match['homeTeam']['id'] == team_id]
        away_games = [match for match in matches if match['awayTeam']['id'] == team_id]

        home_performance = {'played': len(home_games), 'wins': sum(1 for m in home_games if m['score']['winner'] == 'HOME_TEAM')}
        away_performance = {'played': len(away_games), 'wins': sum(1 for m in away_games if m['score']['winner'] == 'AWAY_TEAM')}

        return home_performance, away_performance
    else:
        print(f"Error al obtener el rendimiento en casa y fuera del equipo {team_id}. Estado: {response.status_code}")
        return None, None

def get_shots_stats(match_id):
    headers = {'X-Auth-Token': API_KEY}
    response = requests.get(f"{BASE_URL}/{match_id}", headers=headers)

    if response.status_code == 200:
        match = response.json()
        home_shots = match['homeTeam']['statistics']['shotsOnTarget']
        away_shots = match['awayTeam']['statistics']['shotsOnTarget']
        return home_shots, away_shots
    else:
        print(f"Error al obtener estadísticas de disparos para el partido {match_id}. Estado: {response.status_code}")
        return None, None

def get_suspensions_injuries(match_id):
    headers = {'X-Auth-Token': API_KEY}
    response = requests.get(f"{BASE_URL}/{match_id}", headers=headers)

    if response.status_code == 200:
        match = response.json()
        injuries_home = match['homeTeam']['lineup']['missingPlayers'] if 'lineup' in match['homeTeam'] else []
        injuries_away = match['awayTeam']['lineup']['missingPlayers'] if 'lineup' in match['awayTeam'] else []
        return injuries_home, injuries_away
    else:
        print(f"Error al obtener lesiones para el partido {match_id}. Estado: {response.status_code}")
        return None, None

def get_set_piece_efficiency(team_id):
    headers = {'X-Auth-Token': API_KEY}
    response = requests.get(f"{TEAMS_URL}/{team_id}/matches?status=FINISHED", headers=headers)

    if response.status_code == 200:
        matches = response.json().get('matches', [])
        corners = sum(match['statistics']['corners'] for match in matches if 'statistics' in match)
        goals_from_set_pieces = sum(1 for match in matches if match.get('goalType') == 'setPiece')
        return corners, goals_from_set_pieces
    else:
        print(f"Error al obtener la eficiencia de jugadas de balón parado para el equipo {team_id}. Estado: {response.status_code}")
        return None, None

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

def plot_last_5_games(home_last_5, away_last_5, home_team_name, away_team_name):
    home_scores = []
    away_scores = []
    for game in home_last_5:
        if game['homeTeam'] == home_team_name:
            home_scores.append(game['score']['home'])
        else:
            home_scores.append(game['score']['away'])
    for game in away_last_5:
        if game['awayTeam'] == away_team_name:
            away_scores.append(game['score']['away'])
        else:
            away_scores.append(game['score']['home'])
    plt.figure(figsize=(10, 5))
    plt.plot(range(1, 6), home_scores, marker='o', label=home_team_name, color='blue')
    plt.plot(range(1, 6), away_scores, marker='o', label=away_team_name, color='red')
    plt.xticks(range(1, 6), ['Partido 1', 'Partido 2', 'Partido 3', 'Partido 4', 'Partido 5'])
    plt.title('Rendimiento en los Últimos 5 Partidos')
    plt.xlabel('Partidos')
    plt.ylabel('Goles')
    plt.legend()
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

def predict_result(home_team_id, away_team_id, league_id, home_team_name, away_team_name):
    # Obtener estadísticas de los equipos
    home_stats = get_team_stats(home_team_id, league_id)
    away_stats = get_team_stats(away_team_id, league_id)

    # Obtener rendimiento en casa y fuera
    home_performance, away_performance = get_home_away_performance(home_team_id)
    
    # Obtener últimos 5 partidos
    home_last_5 = get_last_5_games(home_team_id)
    away_last_5 = get_last_5_games(away_team_id)

    # Obtener goles por partido
    home_goals = home_stats['goalsFor'] / home_stats['matchesPlayed']
    away_goals = away_stats['goalsFor'] / away_stats['matchesPlayed']
    
    # Obtener estadísticas de disparos
    home_shots, away_shots = get_shots_stats(home_team_id)  # Cambiar a ID de equipo
    home_shots_on_target, away_shots_on_target = home_shots, away_shots
    
    # Lesiones y sanciones
    injuries_home, injuries_away = get_suspensions_injuries(home_team_id)  # Cambiar a ID de equipo
    
    # Eficiencia en jugadas de balón parado
    corners_home, goals_home = get_set_piece_efficiency(home_team_id)  # Cambiar a ID de equipo
    corners_away, goals_away = get_set_piece_efficiency(away_team_id)  # Cambiar a ID de equipo
    
    # Cálculo de probabilidades
    home_win_percentage = (home_goals + home_performance['wins'] + goals_home) / (home_performance['played'] + away_performance['played']) * 100
    away_win_percentage = (away_goals + away_performance['wins'] + goals_away) / (home_performance['played'] + away_performance['played']) * 100
    draw_percentage = 100 - (home_win_percentage + away_win_percentage)
    
    result = None
    winning_team = None
    
    if home_win_percentage >= confidence_threshold * 100:
        result = "Victoria de " + home_team_name
        winning_team = home_team_name
    elif away_win_percentage >= confidence_threshold * 100:
        result = "Victoria de " + away_team_name
        winning_team = away_team_name
    else:
        result = "Empate"

    return result, winning_team, home_win_percentage, draw_percentage, away_win_percentage, home_last_5, away_last_5, home_stats, away_stats

# Comandos del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    matches = get_matches()
    if matches:
        message = "Partidos disponibles para predecir:\n"
        for match in matches:
            message += f"{match['homeTeam']['name']} vs {match['awayTeam']['name']} (ID: {match['id']})\n"
        await update.message.reply_text(message + "Usa el comando /predict <match_id> para obtener una predicción para un partido.")
    else:
        await update.message.reply_text("Lo siento, no hay partidos disponibles para predecir en este momento.")

async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0:
        await update.message.reply_text("Por favor, proporciona el ID del partido. Usa el comando /start para ver la lista de partidos.")
        return
    try:
        match_id = int(context.args[0])
        matches = get_matches()
        selected_match = next((match for match in matches if match['id'] == match_id), None)
        if not selected_match:
            await update.message.reply_text("ID de partido no válido. Usa /start para ver la lista de partidos disponibles.")
            return
        home_team_id = selected_match['homeTeam']['id']
        away_team_id = selected_match['awayTeam']['id']
        league_id = selected_match['competition']['id']
        home_team_name = selected_match['homeTeam']['name']
        away_team_name = selected_match['awayTeam']['name']
        result, winning_team, home_win_percentage, draw_percentage, away_win_percentage, home_last_5, away_last_5, home_stats, away_stats = predict_result(
            home_team_id, away_team_id, league_id, home_team_name, away_team_name
        )
        if not result:
            await update.message.reply_text("No se pudo obtener estadísticas para este partido.")
            return
        plot_image = plot_probabilities(home_win_percentage, draw_percentage, away_win_percentage, home_team_name, away_team_name)
        last5_image = plot_last_5_games(home_last_5, away_last_5, home_team_name, away_team_name)
        caption = (f"Predicción para {home_team_name} vs {away_team_name}:\n\n"
                   f"Resultado probable: {result}\n"
                   f"Posición en la liga:\n"
                   f"{home_team_name}: {home_stats['position']}º, {home_stats['points']} pts, {home_stats['goalDifference']} dif. de gol\n"
                   f"{away_team_name}: {away_stats['position']}º, {away_stats['points']} pts, {away_stats['goalDifference']} dif. de gol\n"
                   f"Últimos 5 partidos:\n{home_last_5}\n{away_last_5}")
        await update.message.reply_photo(photo=plot_image, caption=caption)
        await update.message.reply_photo(photo=last5_image, caption="Rendimiento en los últimos 5 partidos")
    except ValueError:
        await update.message.reply_text("ID de partido no válido. Usa /start para ver la lista de partidos disponibles.")


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
