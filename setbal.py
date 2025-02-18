# setbal.py

import sqlite3
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the path to the dice database from environment variables
database_dice = os.getenv('DATABASE_DICE')

if not database_dice:
    raise ValueError("DATABASE_DICE is missing from the environment variables.")

def set_user_balance(user_id, new_balance):
    """Sets the balance for a user with the given ID."""
    try:
        # Connect to the database
        connection = sqlite3.connect(database_dice)
        cursor = connection.cursor()

        # Update the user's balance
        cursor.execute("UPDATE wallet SET balance = ? WHERE ID = ?", (new_balance, user_id))
        
        # Check if the update was successful
        if cursor.rowcount == 0:
            print(f"No user found with ID {user_id}.")
        else:
            print(f"Balance for user ID {user_id} updated to {new_balance}.")
        
        # Commit the changes and close the connection
        connection.commit()
        connection.close()

    except sqlite3.Error as e:
        print(f"An error occurred while setting balance: {e}")

# Example usage
if __name__ == "__main__":
    # Replace with actual user ID and balance
    user_id = int(input("Enter user ID: "))
    new_balance = float(input("Enter new balance: "))
    set_user_balance(user_id, new_balance)
