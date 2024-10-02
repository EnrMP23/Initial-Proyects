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
    # Extraer los goles anotados
    home_scores = [game['score']['home'] for game in home_last_5]  # Goles anotados por el equipo local
    away_scores = [game['score']['away'] for game in away_last_5]  # Goles anotados por el equipo visitante

    # Calcular goles recibidos
    home_conceded = [game['score']['away'] for game in home_last_5]  # Goles recibidos por el equipo local
    away_conceded = [game['score']['home'] for game in away_last_5]  # Goles recibidos por el equipo visitante

    # Crear la figura
    plt.figure(figsize=(12, 6))

    # Graficar goles anotados
    plt.plot(range(1, 6), home_scores, marker='o', label=f'{home_team_name} (Anotados)', color='blue', linestyle='-', linewidth=2)
    plt.plot(range(1, 6), away_scores, marker='o', label=f'{away_team_name} (Anotados)', color='red', linestyle='-', linewidth=2)

    # Graficar goles recibidos
    plt.plot(range(1, 6), home_conceded, marker='x', linestyle='--', label=f'{home_team_name} (Recibidos)', color='cyan', linewidth=2)
    plt.plot(range(1, 6), away_conceded, marker='x', linestyle='--', label=f'{away_team_name} (Recibidos)', color='orange', linewidth=2)

    # Añadir etiquetas y título
    plt.xticks(range(1, 6), ['Partido 1', 'Partido 2', 'Partido 3', 'Partido 4', 'Partido 5'], fontsize=10)
    plt.title('Rendimiento en los Últimos 5 Partidos', fontsize=14)
    plt.xlabel('Partidos', fontsize=12)
    plt.ylabel('Goles', fontsize=12)
    plt.grid(True)
    plt.legend(fontsize=10)

    # Anotar los goles en cada punto
    for i in range(5):
        plt.annotate(home_scores[i], (i + 1, home_scores[i]), textcoords="offset points", xytext=(0,5), ha='center', color='blue', fontsize=10)
        plt.annotate(away_scores[i], (i + 1, away_scores[i]), textcoords="offset points", xytext=(0,5), ha='center', color='red', fontsize=10)
        plt.annotate(home_conceded[i], (i + 1, home_conceded[i]), textcoords="offset points", xytext=(0,-15), ha='center', color='cyan', fontsize=10)
        plt.annotate(away_conceded[i], (i + 1, away_conceded[i]), textcoords="offset points", xytext=(0,-15), ha='center', color='orange', fontsize=10)

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
    total_goals = estimated_home_goals + estimated_

