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
confidence_threshold = 0.6  # Umbral de confianza para mostrar predicciones

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

    # Realizamos la solicitud de los últimos 5 partidos finalizados
    response = requests.get(f"{TEAMS_URL}/{team_id}/matches?status=FINISHED", headers=headers)
    
    if response.status_code == 200:
        matches = response.json().get('matches', [])
        last_5_matches = matches[-5:]  # Obtenemos solo los últimos 5 partidos

        # Procesamos los últimos 5 partidos con más detalles
        games_data = []
        for match in last_5_matches:
            game_info = {
                'date': match['utcDate'],  # Fecha del partido
                'homeTeam': match['homeTeam']['name'],
                'awayTeam': match['awayTeam']['name'],
                'homeScore': match['score']['fullTime']['homeTeam'],
                'awayScore': match['score']['fullTime']['awayTeam'],
                'location': 'Home' if match['homeTeam']['id'] == team_id else 'Away'
            }
            games_data.append(game_info)
        
        return games_data
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
    home_scores = [game['homeScore'] for game in home_last_5]
    away_scores = [game['awayScore'] for game in away_last_5]

    plt.figure(figsize=(10, 5))
    plt.plot(range(1, 6), home_scores, marker='o', label=home_team_name, color='blue')
    plt.plot(range(1, 6), away_scores, marker='o', label=away_team_name, color='red')
    
    plt.xticks(range(1, 6), ['Partido 1', 'Partido 2', 'Partido 3', 'Partido 4', 'Partido 5'])
    plt.title(f'Rendimiento de los Últimos 5 Partidos: {home_team_name} vs {away_team_name}')
    plt.xlabel('Partidos')
    plt.ylabel('Goles')
    plt.legend()

    # Guardar la gráfica en un buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()  # Cerramos la figura para liberar memoria
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

    return (home_win_percentage, draw_percentage, away_win_percentage, 
            estimated_home_goals, estimated_away_goals, 
            home_last_5, away_last_5, result)

# Manejo del comando /match
async def match_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    match_id = context.args[0]

    # Aquí iría tu lógica para buscar el partido con base en el match_id
    # Puedes usar get_matches() para obtener todos los partidos y buscar por match_id
    # Ejemplo de búsqueda:

    matches = get_matches()  # Obtiene todos los partidos
    match = next((m for m in matches if str(m['id']) == match_id), None)

    if not match:
        await update.message.reply_text(f"No se encontró el partido con ID {match_id}.")
        return

    home_team_id = match['homeTeam']['id']
    away_team_id = match['awayTeam']['id']
    home_team_name = match['homeTeam']['name']
    away_team_name = match['awayTeam']['name']
    league_id = match['competition']['id']

    (home_win_percentage, draw_percentage, away_win_percentage,
     estimated_home_goals, estimated_away_goals, 
     home_last_5, away_last_5, result) = predict_result(home_team_id, away_team_id, league_id, home_team_name, away_team_name)

    if not home_win_percentage:
        await update.message.reply_text("Hubo un problema al predecir el resultado. Inténtalo de nuevo.")
        return

    # Mensaje de respuesta
    response = f"Partido: {home_team_name} vs {away_team_name}\n"
    response += f"Estadísticas del partido:\n"
    response += f"Probabilidad de victoria {home_team_name}: {home_win_percentage:.2f}%\n"
    response += f"Probabilidad de empate: {draw_percentage:.2f}%\n"
    response += f"Probabilidad de victoria {away_team_name}: {away_win_percentage:.2f}%\n"
    response += f"Predicción: {result}\n"
    response += f"Estimación de goles: {home_team_name} {estimated_home_goals:.1f} - {estimated_away_goals:.1f} {away_team_name}\n"

    # Enviar el mensaje al usuario
    await update.message.reply_text(response)

    # Gráficas
    pie_chart = plot_probabilities(home_win_percentage, draw_percentage, away_win_percentage, home_team_name, away_team_name)
    last_5_games_chart = plot_last_5_games(home_last_5, away_last_5, home_team_name, away_team_name)

    # Enviar las gráficas
    await update.message.reply_photo(photo=pie_chart)
    await update.message.reply_photo(photo=last_5_games_chart)

    # Información de los últimos 5 partidos
    home_last_games_text = (
        f"\nÚltimos 5 partidos de {home_team_name}:\n\n" + 
        "\n".join([f"{game['date'][:10]}: {game['homeTeam']} {game['homeScore']} - {game['awayScore']} {game['awayTeam']} (Local: {game['location']})"
                   for game in home_last_5])
    )
    away_last_games_text = (
        f"\n\nÚltimos 5 partidos de {away_team_name}:\n\n" + 
        "\n".join([f"{game['date'][:10]}: {game['homeTeam']} {game['homeScore']} - {game['awayScore']} {game['awayTeam']} (Local: {game['location']})"
                   for game in away_last_5])
    )
    await update.message.reply_text(home_last_games_text + away_last_games_text)

# Configuración del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('¡Hola! Usa el comando /match <id> para obtener una predicción de partido.')

if __name__ == '__main__':
    # Configuración de la aplicación
    application = ApplicationBuilder().token('7309741382:AAETHbkJYLMha85xOyuvmdRTLm1WUPD2y0c').build()

    # Configurar los comandos del bot
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("match", match_prediction))

    # Iniciar la aplicación
    application.run_polling()
