import json
import sqlite3
import time
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import CallbackContext

hilo_file = "Hilo.json"
group_id = -1002366180097
house_wallet_id = 1234
admin_id = 1493164653
global_game_active = False
min_bet = 0.5
max_bet = 10

def start_dh(update: Update, context: CallbackContext):
    global global_game_active
    user_id = update.effective_user.id
    if update.effective_chat.id != group_id:
        update.message.reply_text("Game can only be played in LuckGamble Group.")
        return
    if global_game_active:
        update.message.reply_text("A game is already active. Please wait for it to finish.")
        return
    try:
        bet_input = context.args[0]
        if bet_input.lower() == 'all':
            bet_amount = get_user_balance(user_id)
        elif bet_input.lower() == 'half':
            bet_amount = get_user_balance(user_id) / 2
        else:
            bet_amount = float(bet_input)
        if bet_amount < min_bet or bet_amount > max_bet:
            update.message.reply_text(f"Bet amount must be between ${min_bet} and ${max_bet}.")
            return
    except (IndexError, ValueError):
        update.message.reply_text("Usage: /dh <bet amount>")
        return
    with sqlite3.connect("dice.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM wallet WHERE ID = ?", (user_id,))
        result = cursor.fetchone()
        if result is None or result[0] < bet_amount:
            update.message.reply_text("Insufficient balance.")
            return
        cursor.execute("UPDATE wallet SET balance = balance - ? WHERE ID = ?", (bet_amount, user_id))
        conn.commit()
    global_game_active = True
    dice_message = update.message.reply_dice()
    initial_roll = dice_message.dice.value
    context.chat_data["game_active"] = True
    context.chat_data["game_id"] = user_id
    context.chat_data["bet_amount"] = bet_amount
    context.chat_data["initial_roll"] = initial_roll
    time.sleep(3)
    odds_text, keyboard = get_odds_keyboard(initial_roll)
    update.message.reply_text(
        f"The bot rolled a {initial_roll}. Please select your bet.\n\n{odds_text}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    save_game_state(user_id, initial_roll, bet_amount)

def handle_dh_choice(update: Update, context: CallbackContext):
    global global_game_active
    user_id = update.effective_user.id
    if not context.chat_data.get("game_active") or context.chat_data["game_id"] != user_id:
        update.callback_query.answer()
        return
    user_choice = update.callback_query.data
    update.callback_query.answer()
    update.callback_query.edit_message_reply_markup(reply_markup=None)
    initial_roll = context.chat_data["initial_roll"]
    bet_amount = context.chat_data["bet_amount"]
    second_roll_message = update.callback_query.message.reply_dice()
    second_roll = second_roll_message.dice.value
    
    if second_roll == initial_roll:
        if user_choice == "same":
            time.sleep(3)
            update.callback_query.message.reply_text("The bot rolled the same number. You win 5.5x!")
            profit = bet_amount * 5.55
            update_user_stats(user_id, bet_amount, True, profit)
            update_balance(user_id, profit)
            update_balance(house_wallet_id, -profit)
        else:
            time.sleep(3)
            update.callback_query.message.reply_text("The bot rolled the same number. You lose!")
            update_user_stats(user_id, bet_amount, False, 0)
            update_balance(house_wallet_id, bet_amount)
        global_game_active = False
        context.chat_data.clear()
        delete_game_state()
        return

    if initial_roll == 1 or initial_roll == 6:
        # For rolls of 1 or 6, no refund on same roll, only win/loss based on the choice.
        win = (user_choice == "higher" and second_roll > initial_roll) or \
              (user_choice == "lower" and second_roll < initial_roll)
        payout_multiplier = get_payout_multiplier(initial_roll, user_choice) if win else 0
        profit = bet_amount * payout_multiplier if win else 0
        result_text = f"The bot rolled {second_roll}. " + \
                      (f"✅ You win! Your bet of ${bet_amount} earned ${profit:.2f}." if win else f"❌ You lose. Your bet of ${bet_amount} is lost.")
        time.sleep(3)
        context.bot.send_message(chat_id=update.effective_chat.id, text=result_text)
        update_user_stats(user_id, bet_amount, win, profit)
        if win:
            update_balance(user_id, profit)
            update_balance(house_wallet_id, -profit)
        else:
            update_balance(house_wallet_id, bet_amount)
    else:
        # For rolls 2-5, process refund if "same" was chosen and the bot rolled the same number.
        win = (user_choice == "higher" and second_roll > initial_roll) or \
              (user_choice == "lower" and second_roll < initial_roll)
        payout_multiplier = get_payout_multiplier(initial_roll, user_choice) if win else 0
        profit = bet_amount * payout_multiplier if win else 0
        result_text = f"The bot rolled {second_roll}. " + \
                      (f"✅ You win! Your bet of ${bet_amount} earned ${profit:.2f}." if win else f"❌ You lose. Your bet of ${bet_amount} is lost.")
        time.sleep(3)
        context.bot.send_message(chat_id=update.effective_chat.id, text=result_text)
        update_user_stats(user_id, bet_amount, win, profit)
        if win:
            update_balance(user_id, profit)
            update_balance(house_wallet_id, -profit)
        else:
            update_balance(house_wallet_id, bet_amount)

    global_game_active = False
    context.chat_data.clear()
    delete_game_state()
def get_odds_keyboard(roll):
    if roll == 1:
        return "Higher (1.1x) | Same (5.55x)", [[
            InlineKeyboardButton("Higher (1.1x)", callback_data="higher"),
            InlineKeyboardButton("Same (5.55x)", callback_data="same")
        ]]
    elif roll == 6:
        return "Same (5.55x) | Lower (1.1x)", [[
            InlineKeyboardButton("Same (5.55x)", callback_data="same"),
            InlineKeyboardButton("Lower (1.1x)", callback_data="lower")
        ]]
    odds = {
        2: ("Higher (1.15x) | Lower (2.75x)", "higher", "lower"),
        3: ("Higher (1.39x) | Lower (1.85x)", "higher", "lower"),
        4: ("Higher (1.85x) | Lower (1.39x)", "higher", "lower"),
        5: ("Higher (2.75x) | Lower (1.15x)", "higher", "lower")
    }
    odds_text, high_data, low_data = odds[roll]
    return odds_text, [[
        InlineKeyboardButton(f"{high_data.capitalize()} ({odds_text.split('|')[0].split()[-1]})", callback_data="higher"),
        InlineKeyboardButton(f"{low_data.capitalize()} ({odds_text.split('|')[1].split()[-1]})", callback_data="lower")
    ]]

def get_payout_multiplier(roll, choice):
    multipliers = {
        (1, "higher"): 1.1, (1, "same"): 5.55,
        (2, "higher"): 1.15, (2, "lower"): 2.75,
        (3, "higher"): 1.39, (3, "lower"): 1.85,
        (4, "higher"): 1.85, (4, "lower"): 1.39,
        (5, "higher"): 2.75, (5, "lower"): 1.15,
        (6, "lower"): 1.1, (6, "same"): 5.55
    }
    return multipliers.get((roll, choice), 0)

def update_balance(user_id, amount):
    with sqlite3.connect("dice.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE wallet SET balance = balance + ? WHERE ID = ?", (amount, user_id))
        conn.commit()

def update_user_stats(user_id, bet_amount, win, profit):
    with sqlite3.connect("dice.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE wallet SET total_games = total_games + 1, wins = wins + ?, total_wagered = total_wagered + ?, total_earnings = total_earnings + ? WHERE ID = ?",
                       (int(win), bet_amount, profit, user_id))
        conn.commit()

def refund_bet(user_id, bet_amount):
    with sqlite3.connect("dice.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE wallet SET balance = balance + ? WHERE ID = ?", (bet_amount, user_id))
        conn.commit()

def save_game_state(user_id, initial_roll, bet_amount):
    game_data = {
        "user_id": user_id,
        "initial_roll": initial_roll,
        "bet_amount": bet_amount
    }
    with open(hilo_file, "w") as f:
        json.dump(game_data, f)

def delete_game_state():
    with open(hilo_file, "w") as f:
        json.dump({}, f)

def get_user_balance(user_id):
    with sqlite3.connect("dice.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM wallet WHERE ID = ?", (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0

def reset_hilo(update: Update, context: CallbackContext):
    global global_game_active
    if update.effective_user.id != admin_id:
        update.message.reply_text("You do not have permission to reset the game.")
        return
    global_game_active = False
    context.chat_data.clear()
    delete_game_state()
    update.message.reply_text("HiLo Reset Done")
