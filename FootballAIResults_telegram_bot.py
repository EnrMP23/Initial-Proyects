import requests
import matplotlib.pyplot as plt
import io
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler

# Define your API key and endpoints
API_KEY = "7dcb5906ce9b48cf9becc41685b38867"
TEAMS_URL = "https://api.football-data.org/v4/teams"
MATCHES_URL = "https://api.football-data.org/v4/matches"

# Fetch last 5 games for a team
def get_last_5_games(team_id):
    headers = {
        'X-Auth-Token': API_KEY
    }
    
    response = requests.get(f"{TEAMS_URL}/{team_id}/matches?status=FINISHED", headers=headers)
    
    if response.status_code == 200:
        matches = response.json().get('matches', [])[-5:]  # Get the last 5 matches
        last_5_games = []
        
        for match in matches:
            last_5_games.append({
                'homeTeam': match['homeTeam']['name'],
                'awayTeam': match['awayTeam']['name'],
                'score': {
                    'homeTeam': match['score']['fullTime']['homeTeam'],
                    'awayTeam': match['score']['fullTime']['awayTeam']
                }
            })
        return last_5_games
    else:
        print(f"Error al obtener los últimos 5 partidos del equipo {team_id}. Estado: {response.status_code}")
        return []

# Plot last 5 games performance
def plot_last_5_games(home_last_5, away_last_5, home_team_name, away_team_name):
    # Ensure the score extraction is correct for both home and away teams
    home_scores = [game['score']['homeTeam'] for game in home_last_5]  # Extract home team scores
    away_scores = [game['score']['awayTeam'] for game in away_last_5]  # Extract away team scores

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
    buf.seek(0)
    plt.close()  # Close the figure to free memory
    return buf

# Fetch team statistics (like goals for, goals against, and points)
def get_team_stats(team_id):
    headers = {
        'X-Auth-Token': API_KEY
    }
    
    response = requests.get(f"{TEAMS_URL}/{team_id}", headers=headers)
    
    if response.status_code == 200:
        team_data = response.json()
        return {
            'goalsFor': team_data['goalsFor'],
            'goalsAgainst': team_data['goalsAgainst'],
            'points': team_data['points']
        }
    else:
        print(f"Error al obtener las estadísticas del equipo {team_id}. Estado: {response.status_code}")
        return {}

# Fetch the match by ID and generate prediction and stats
def get_match_prediction(match_id):
    headers = {
        'X-Auth-Token': API_KEY
    }
    
    response = requests.get(f"{MATCHES_URL}/{match_id}", headers=headers)
    
    if response.status_code == 200:
        match_data = response.json()
        
        home_team_id = match_data['homeTeam']['id']
        away_team_id = match_data['awayTeam']['id']
        
        home_team_name = match_data['homeTeam']['name']
        away_team_name = match_data['awayTeam']['name']
        
        home_last_5 = get_last_5_games(home_team_id)
        away_last_5 = get_last_5_games(away_team_id)
        
        home_stats = get_team_stats(home_team_id)
        away_stats = get_team_stats(away_team_id)

        # Generate a plot of the last 5 matches performance
        plot_buf = plot_last_5_games(home_last_5, away_last_5, home_team_name, away_team_name)
        
        # Build the response text including basic and advanced stats
        response_text = (
            f"Predicción del Partido:\n\n"
            f"{home_team_name} vs {away_team_name}\n"
            f"Últimos 5 Partidos:\n"
            f"{home_team_name}: {home_last_5}\n"
            f"{away_team_name}: {away_last_5}\n\n"
            f"Estadísticas Avanzadas:\n"
            f"{home_team_name} - Goles: {home_stats['goalsFor']}, Goles en Contra: {home_stats['goalsAgainst']}, Puntos: {home_stats['points']}\n"
            f"{away_team_name} - Goles: {away_stats['goalsFor']}, Goles en Contra: {away_stats['goalsAgainst']}, Puntos: {away_stats['points']}"
        )
        
        return response_text, plot_buf
    else:
        print(f"Error al obtener los datos del partido {match_id}. Estado: {response.status_code}")
        return None, None

# Bot command to predict a match
async def predict(update: Update, context):
    match_id = context.args[0] if context.args else None
    
    if not match_id:
        await update.message.reply_text("Por favor proporciona un ID de partido válido.")
        return
    
    response_text, plot_buf = get_match_prediction(match_id)
    
    if response_text and plot_buf:
        await update.message.reply_photo(photo=plot_buf, caption=response_text)
    else:
        await update.message.reply_text("Error al obtener la predicción del partido.")

# Main function to run the bot
async def main():
    application = ApplicationBuilder().token("7309741382:AAETHbkJYLMha85xOyuvmdRTLm1WUPD2y0c").build()
    
    # Add the prediction command handler
    application.add_handler(CommandHandler("predict", predict))
    
    # Start the bot
    await application.start()
    await application.idle()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

