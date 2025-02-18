import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

database_dice = os.getenv('DATABASE_DICE')
database_dicegame = os.getenv('DATABASE_DICEGAME')
database_bowlgame = os.getenv('DATABASE_BOWLGAME')
database_dartgame = os.getenv('DATABASE_DARTGAME')

if not database_dice:
    raise ValueError("DATABASE_DICE is missing from the environment variables.")
if not database_dicegame:
    raise ValueError("DATABASE_DICEGAME is missing from the environment variables.")
if not database_bowlgame:
    raise ValueError("DATABASE_BOWLGAME is missing from the environment variables.")
if not database_dartgame:
    raise ValueError("DATABASE_DARTGAME is missing from the environment variables.")

def initialize_database(db_path, table_creation_queries):
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}. Creating new database...")
    else:
        print(f"Database file found at {db_path}. Ensuring tables exist...")

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    for query in table_creation_queries:
        cursor.execute(query)
    connection.commit()
    connection.close()
    print(f"Database at {db_path} initialized successfully.")

wallet_table_query = '''
    CREATE TABLE IF NOT EXISTS wallet (
        ID INTEGER PRIMARY KEY,
        balance REAL DEFAULT 0.0,
        code TEXT DEFAULT '0',
        amount REAL DEFAULT 0.0,
        name TEXT,
        wins INTEGER DEFAULT 0,
        total_games INTEGER DEFAULT 0,
        total_earnings REAL DEFAULT 0.0,
        total_wagered REAL DEFAULT 0.0
    )
'''

rains_table_query = '''
    CREATE TABLE IF NOT EXISTS rains (
        rain_id TEXT PRIMARY KEY,
        admin_id INTEGER,
        amount REAL,
        min_wagered REAL,
        start_time TEXT,
        end_time TEXT,
        chat_id INTEGER,
        message_id INTEGER,
        host_username TEXT
    )
'''

rain_participants_table_query = '''
    CREATE TABLE IF NOT EXISTS rain_participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rain_id TEXT,
        user_id INTEGER,
        username TEXT,
        FOREIGN KEY (rain_id) REFERENCES rains (rain_id)
    )
'''

initialize_database(database_dice, [wallet_table_query, rains_table_query, rain_participants_table_query])

game_table_query = '''
    CREATE TABLE IF NOT EXISTS game (
        game_id INTEGER PRIMARY KEY,
        player_1 INTEGER,
        player_2 INTEGER,
        total_turn INTEGER DEFAULT 0,
        turn_number INTEGER,
        game_status TEXT DEFAULT 'pending',
        winner INTEGER DEFAULT 0,
        Amount REAL DEFAULT 0.0,
        player_1_name TEXT,
        player_2_name TEXT,
        player_1_wins INTEGER DEFAULT 0,
        player_2_wins INTEGER DEFAULT 0,
        FOREIGN KEY(player_1) REFERENCES wallet(ID),
        FOREIGN KEY(player_2) REFERENCES wallet(ID)
    )
'''

initialize_database(database_dicegame, [game_table_query])
initialize_database(database_bowlgame, [game_table_query])
initialize_database(database_dartgame, [game_table_query])

print("All databases and tables initialized successfully.")
