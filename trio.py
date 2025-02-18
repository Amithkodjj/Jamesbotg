import os
import sqlite3
import json
import random
import hashlib
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from uuid import uuid4
from time import sleep
from telegram.ext import CallbackContext

DATABASE = 'dice.db'
TRIO_GAME_FILE = 'trio.json'
GROUP_ID =  -1002366180097
dr_min = 0.5
dr_max = 10.0

def load_trio_data():
    try:
        with open(TRIO_GAME_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_trio_data(data):
    with open(TRIO_GAME_FILE, 'w') as f:
        json.dump(data, f)

def get_user_balance(user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM wallet WHERE id = ?", (user_id,))
    balance = cursor.fetchone()
    conn.close()
    return balance[0] if balance else 0

def update_user_balance(user_id, new_balance):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE wallet SET balance = ? WHERE id = ?", (new_balance, user_id))
    conn.commit()
    conn.close()

def get_house_balance():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM wallet WHERE id = ?", (1234,))
    house_balance = cursor.fetchone()
    conn.close()
    return house_balance[0] if house_balance else 0

def update_house_balance(new_balance):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE wallet SET balance = ? WHERE id = ?", (new_balance, 1234))
    conn.commit()
    conn.close()

def generate_game_hash(server_seed, client_seed):
    combined = f"{server_seed}{client_seed}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()

def start_trio_game(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    if chat_id != GROUP_ID:
        update.message.reply_text("This game can only be played in Diceable Casino Group")
        return

    user_id = str(update.effective_user.id)

    if len(context.args) < 1:
        update.message.reply_text(
            "Usage: /trio <betamount> <mode>\n"
            "Game info:\n"
            "How to Play Trio\n\n"
            "Modes:\n"
            " • Easy Mode: One button is win, one is lose, and one is draw, offering balanced odds. 1.3x win\n"
            " • Hard Mode: One button is win, while two are lose, increasing the risk for bigger thrills. 2.5x win\n"
            " • All Mode: Bet your entire balance\n"
            " • Half Mode: Bet half your balance\n\n"
            "1. Place Your Bet: Choose an amount to wager.\n"
            "2. Pick a Button: Three hidden options are presented, each linked to a win, lose, or draw outcome (depending on mode).\n"
            "3. Reveal the Outcome: After selecting, the hidden result is revealed:\n"
            "• Win: Earn a payout (e.g., 1.3x or 2.5x your bet depending on mode).\n"
            "• Lose: Forfeit your bet.\n"
            "• Draw: Get your bet back.\n\n"
            "Button order is randomized each round for fairness and excitement!"
        )
        return

    try:
        if context.args[0].lower() == "all":
            bet_amount = get_user_balance(user_id)
        elif context.args[0].lower() == "half":
            bet_amount = get_user_balance(user_id) / 2
        else:
            bet_amount = float(context.args[0])
    except ValueError:
        update.message.reply_text("Bet amount must be a number!")
        return

    mode = context.args[1].lower() if len(context.args) > 1 else "easy"

    if mode == "all" or mode == "half":
        pass
    elif mode not in ["easy", "hard"]:
        update.message.reply_text("Invalid mode! Choose either 'easy', 'hard', 'all', or 'half'.")
        return

    if bet_amount < dr_min or bet_amount > dr_max:
        update.message.reply_text(f"Bet amount must be between ${dr_min} and ${dr_max}.")
        return

    balance = get_user_balance(user_id)
    if bet_amount > balance:
        update.message.reply_text("Insufficient balance.")
        return

    new_balance = balance - bet_amount
    update_user_balance(user_id, new_balance)

    game_id = str(uuid4())
    trio_data = load_trio_data()
    trio_data[user_id] = {"status": "playing", "bet_amount": bet_amount, "game_id": game_id, "choice": "none", "mode": mode}
    save_trio_data(trio_data)
    server_seed = str(uuid4())
    client_seed = user_id
    game_hash = generate_game_hash(server_seed, client_seed)

    if mode == "easy":
        order = ["Win", "Lose", "Draw"]
        multiplier = 1.3
    elif mode == "hard":
        order = ["Win", "Lose", "Lose"]
        multiplier = 2.5
    elif mode == "all" or mode == "half":
        order = ["Win", "Lose", "Draw"]  
        multiplier = 1.3  
    random.shuffle(order)

    trio_data[user_id]["order"] = order
    trio_data[user_id]["server_seed"] = server_seed
    trio_data[user_id]["game_hash"] = game_hash
    trio_data[user_id]["multiplier"] = multiplier
    save_trio_data(trio_data)

    keyboard = [
        [InlineKeyboardButton("1", callback_data=f"choice_1_{game_id}"),
         InlineKeyboardButton("2", callback_data=f"choice_2_{game_id}"),
         InlineKeyboardButton("3", callback_data=f"choice_3_{game_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"🔮 Trio ({mode.capitalize()} Mode)\nSelect your button!\n\nWin-{multiplier}x\nLose-Lose Bet\nDraw-Refund" if mode == "easy" else
        f"🔮 Trio ({mode.capitalize()} Mode)\nSelect your button!\n\nWin-{multiplier}x\nLose-Lose Bet",
        reply_markup=reply_markup
    )
def handle_trio_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    username = query.from_user.username or user_id
    game_id = query.data.split("_")[2]
    choice = int(query.data.split("_")[1])
    trio_data = load_trio_data()

    if user_id not in trio_data or trio_data[user_id]["status"] != "playing" or trio_data[user_id]["game_id"] != game_id:
        query.answer("This is not your game!")
        return

    if trio_data[user_id]["choice"] != "none":
        query.answer("You already made a choice!")
        return

    trio_data[user_id]["choice"] = choice
    save_trio_data(trio_data)
    query.edit_message_text(f"🔮 Trio\nYou chose button {choice}.\nBot is drawing...")
    order = trio_data[user_id]["order"]
    outcome = order[choice - 1]
    bet_amount = trio_data[user_id]["bet_amount"]
    multiplier = trio_data[user_id]["multiplier"]
    result_message = ""
    winnings = 0

    if outcome == "Win":
        winnings = bet_amount * multiplier
        new_balance = get_user_balance(user_id) + winnings
        update_user_balance(user_id, new_balance)

        house_balance = get_house_balance()
        new_house_balance = house_balance - winnings
        update_house_balance(new_house_balance)
        result_message = f"✅ You win! You win ${winnings:.2f}."

        wins_channel_id = "@LuckGamblewins"
        wins_message = f"@{username} Just Won ${winnings:.2f} in 🔮 Trio"
        context.bot.send_message(chat_id=wins_channel_id, text=wins_message)

    elif outcome == "Draw":
        new_balance = get_user_balance(user_id) + bet_amount
        update_user_balance(user_id, new_balance)
        result_message = f"⚖️ It's a draw! Your bet of ${bet_amount:.2f} is refunded."

    else:
        house_balance = get_house_balance()
        new_house_balance = house_balance + bet_amount
        update_house_balance(new_house_balance)

        result_message = f"❌ You lose. Your bet of ${bet_amount:.2f} is lost."

    server_seed = trio_data[user_id]["server_seed"]
    game_hash = trio_data[user_id]["game_hash"]

    result_message += f"\n\nThe order was:\n{' - '.join(order)}"
    result_message += f"\n\nServer seed:\n> {server_seed}\nGame Hash:\n> {game_hash}"

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT total_games, total_earnings, total_wagered FROM wallet WHERE id = ?", (user_id,))
    stats = cursor.fetchone()
    total_games, total_earnings, total_wagered = stats if stats else (0, 0.0, 0.0)
    total_games += 1
    total_wagered += bet_amount
    total_earnings += winnings if outcome == "Win" else 0

    cursor.execute("""
        UPDATE wallet SET total_games = ?, total_earnings = ?, total_wagered = ?
        WHERE id = ?
    """, (total_games, total_earnings, total_wagered, user_id))
    conn.commit()
    conn.close()

    query.edit_message_text(result_message)
    query.answer()
