import os
import sqlite3
import json
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from uuid import uuid4
from time import sleep
from telegram.ext import CallbackContext

DATABASE = 'dice.db'
GAME_DATA_FILE = 'dr.json'
dr_min = 0.5
dr_max = 10
GROUP_ID = -1002040392620

def load_game_data():
    try:
        with open(GAME_DATA_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_game_data(data):
    with open(GAME_DATA_FILE, 'w') as f:
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

def update_bot_balance(payout):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("UPDATE wallet SET balance = balance - ? WHERE id = 1234", (payout,))
    conn.commit()
    conn.close()

def update_wallet_stats(user_id, bet_amount, winnings=0):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT total_games, wins, total_wagered, total_earnings FROM wallet WHERE id = ?", (user_id,))
    stats = cursor.fetchone()
    if stats:
        total_games, wins, total_wagered, total_earnings = stats
        total_games += 1
        total_wagered += bet_amount
        if winnings > 0:
            wins += 1
            total_earnings += winnings
    else:
        total_games, wins, total_wagered, total_earnings = 1, int(winnings > 0), bet_amount, winnings

    cursor.execute(
        "UPDATE wallet SET total_games = ?, wins = ?, total_wagered = ?, total_earnings = ? WHERE id = ?",
        (total_games, wins, total_wagered, total_earnings, user_id)
    )
    conn.commit()
    conn.close()

def start_dice_roulette(update, context):
    global dr_data
    chat_id = update.effective_chat.id
    if chat_id != GROUP_ID:
        update.message.reply_text("This game can only be played in Diceable Casino Group")
        return
    user_id = str(update.effective_user.id)
    if user_id in dr_data and dr_data[user_id]['status'] == 'playing':
        update.message.reply_text("Finish your previous game before starting a new one!")
        return
    try:
        bet_amount = context.args[0]
        if bet_amount == 'all':
            bet_amount = get_user_balance(user_id)
        elif bet_amount == 'half':
            bet_amount = get_user_balance(user_id) / 2
        else:
            bet_amount = float(bet_amount)
    except (IndexError, ValueError):
        update.message.reply_text("Usage: /dr <bet amount>")
        return
    if bet_amount < dr_min or bet_amount > dr_max:
        update.message.reply_text(f"Bet amount must be between ${dr_min} and ${dr_max}.")
        return
    balance = get_user_balance(user_id)
    if bet_amount > balance:
        update.message.reply_text("Insufficient balance.")
        return
    update_user_balance(user_id, balance - bet_amount)
    game_id = str(uuid4())
    dr_data[user_id] = {"status": "playing", "bet_amount": bet_amount, "choice": "none", "game_id": game_id}
    save_game_data(dr_data)
    number_buttons = [
        [InlineKeyboardButton(str(i), callback_data=f"num_{i}_{game_id}") for i in range(1, 4)],
        [InlineKeyboardButton(str(i), callback_data=f"num_{i}_{game_id}") for i in range(4, 7)]
    ]
    odd_even_buttons = [
        [InlineKeyboardButton("Odd", callback_data=f"odd_{game_id}"), InlineKeyboardButton("Even", callback_data=f"even_{game_id}")],
        [InlineKeyboardButton("High", callback_data=f"high_{game_id}"), InlineKeyboardButton("Low", callback_data=f"low_{game_id}")]
    ]
    keyboard = number_buttons + odd_even_buttons
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "🎲 Dice Roulette\n\nMultipliers for High/Low/Odd/Even: x1.92\nMultipliers for numbers: x5\n\nChoose your bet option:",
        reply_markup=reply_markup
    )

def handle_bet_choice(update, context):
    global dr_data
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data.split("_")
    if len(data) < 2:
        query.answer("Invalid data format!")
        return
    if data[0] == "num":
        choice = data[1]
        game_id = data[2]
    else:
        choice = data[0]
        game_id = data[1]
    if user_id not in dr_data or dr_data[user_id]['status'] != 'playing' or dr_data[user_id]['game_id'] != game_id:
        query.answer("This is not your game mate!")
        return
    if dr_data[user_id]['choice'] != "none":
        query.answer("You've already selected your prediction.")
        return
    dr_data[user_id]['choice'] = choice
    save_game_data(dr_data)
    query.edit_message_text(f"🎲 Dice Roulette\nYour choice: {choice}\nBot is rolling...")
    query.answer(f"Prediction chosen: {choice}")
    roll_dice(update, context, game_id)

def roll_dice(update, context, game_id):
    global dr_data
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or user_id
    if user_id not in dr_data or dr_data[user_id]['game_id'] != game_id:
        update.effective_message.reply_text("This is not your game!")
        return
    bet_amount = dr_data[user_id]['bet_amount']
    choice = dr_data[user_id]['choice']
    dice_message = context.bot.send_dice(chat_id=update.effective_chat.id, emoji="🎲")
    dice_value = dice_message.dice.value
    sleep(3)
    if choice.isdigit() and int(choice) == dice_value:
        winnings = bet_amount * 5
    elif (choice == "odd" and dice_value % 2 != 0) or (choice == "even" and dice_value % 2 == 0) or \
         (choice == "high" and dice_value > 3) or (choice == "low" and dice_value <= 3):
        winnings = bet_amount * 1.92
    else:
        winnings = 0
    if winnings > 0:
        new_balance = get_user_balance(user_id) + winnings
        update_user_balance(user_id, new_balance)
        update_bot_balance(winnings)
        update_wallet_stats(user_id, bet_amount, winnings)
        result_message = f"✅ You win! Bot rolled {dice_value} 🎲. Payout of ${winnings:.2f} has been added."
        wins_channel_id = "@diceablewins"
        wins_message = f"@{username} just won ${winnings:.2f} in 🎲 Dice Roulette!"
        context.bot.send_message(chat_id=wins_channel_id, text=wins_message)
    else:
        update_wallet_stats(user_id, bet_amount)
        result_message = f"❌ You lose. Bot rolled {dice_value} 🎲. You lost ${bet_amount:.2f}."
    del dr_data[user_id]
    save_game_data(dr_data)
    update.effective_message.reply_text(result_message)

dr_data = load_game_data()
