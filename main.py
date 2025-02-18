from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler, \
    CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update,ChatMember
import sqlite3
import json
import requests
import time
import base58
import bech32
from telegram import ParseMode
from telegram import Bot
from dotenv import load_dotenv
import os
import random
import re
import logging
import sys
from blackjack import start_blackjack_game, format_hand, handle_hit, handle_stand, payout, calculate_hand_total, \
    format_hand_with_suits, format_player_hand, draw_card, multiplier_blackjack
from dr import start_dice_roulette, handle_bet_choice
from trio import start_trio_game, handle_trio_choice
from hilo import start_dh, handle_dh_choice, reset_hilo
def setup_logger():
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.flush = sys.stdout.flush
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.DEBUG,  # Set the logging level to DEBUG for more detailed output
        handlers=[handler]
    )
    logging.getLogger('apscheduler').setLevel(logging.DEBUG)

load_dotenv()

merchant_key = os.getenv('MERCHANT_KEY')
payout_key = os.getenv("PAYOUT_KEY")
database_dice = os.getenv('DATABASE_DICE')
database_dicegame = os.getenv('DATABASE_DICEGAME')
bot_environment = os.getenv('BOT_ENV')
database_bowlgame = os.getenv('DATABASE_BOWLGAME')
database_dartgame = os.getenv('DATABASE_DARTGAME')
if bot_environment == "dev":
    bot_name = "Diceable Casino"
    admin_id =  6066784716
    group_id =  -4556744769
    bot_token =  os.getenv("BOT_TOKEN_DEV")
    telegram_link = "https://t.me/DiceableCasinoBot"
    bot_player = Bot(bot_token)
 

elif bot_environment == "prod":
    bot_name = "Diceable Casino"
    admin_id =  6582686636
    group_id = -1002040392620 
    bot_token = os.getenv('BOT_TOKEN_PROD')
    telegram_link = "https://t.me/Diceablecasinobot"
    bot_player = Bot(bot_token)

else:
    raise ValueError("Invalid BOT_ENVIRONMENT value. Use 'dev' or 'prod' ")

if not bot_token:
    raise ValueError("BOT_TOKEN is missing from the environment variables.")
if not merchant_key:
    raise ValueError("MERCHANT_KEY is missing from the environment variables.")
if not payout_key:
    raise ValueError("PAYOUT_KEY is missing from the environment variables.")
if not database_dice:
    raise ValueError("DATABASE_DICE is missing from the environment variables.")
if not database_dicegame:
    raise ValueError("DATABASE_DICEGAME is missing from the environment variables.")

WTH = range(1)
DEFAULT_SIZE_TTT = 3
DEFAULT_SIZE = 5
bot_active = True
maximum_bet_amount = 25
multipliers = {
    1: [1.02, 1.03, 1.07, 1.12, 1.18, 1.24, 1.30, 1.39, 1.47, 1.57, 1.68, 1.81, 1.96, 2.14, 2.35, 2.61, 2.94, 3.36, 3.91, 4.70, 5.89, 7.84, 11.76, 23.51],
    2: [1.03, 1.11, 1.22, 1.34, 1.48, 1.65, 1.84, 2.07, 2.35, 2.69, 3.09, 3.62, 4.28, 5.13, 6.27, 7.84, 10.08, 13.43, 18.81, 28.22, 47.03, 93.05, 282.15],
    3: [1.07, 1.22, 1.41, 1.62, 1.90, 2.23, 2.65, 3.18, 3.87, 4.75, 5.95, 7.56, 9.82, 13.11, 18.02, 25.76, 38.63, 61.81, 108.16, 216.32, 566.44, 2163.15],
    4: [1.12, 1.34, 1.62, 1.99, 2.45, 3.07, 3.88, 5.00, 6.54, 8.71, 11.88, 16.64, 24.04, 36.05, 56.66, 94.42, 169.96, 339.92, 792.15, 2379.47, 11872.32],
    5: [1.18, 1.48, 1.90, 2.45, 3.22, 4.29, 5.83, 8.08, 11.34, 16.24, 24.95, 38.82, 63.09, 107.16, 198.29, 396.58, 892.29, 2379.47, 8323.13, 49918.77],
    6: [1.24, 1.65, 2.23, 3.15, 4.29, 6.14, 8.97, 13.46, 20.80, 33.28, 55.46, 97.06, 180.76, 359.52, 792.15, 1982.89, 5948.66, 23794.65, 166563.55],
    7: [1.30, 1.84, 2.65, 3.89, 5.83, 8.97, 14.20, 23.24, 39.52, 70.25, 131.73, 263.50, 570.83, 1360.00, 3777.48, 12558.29, 56612.29, 1017211.29],
    8: [1.39, 2.07, 3.18, 5.00, 8.08, 13.86, 23.24, 41.85, 79.04, 158.18, 338.73, 790.39, 2055.99, 6164.98, 22605.92, 112024.58, 1017211.29],
    9: [1.47, 2.35, 3.87, 6.54, 11.44, 20.29, 39.52, 79.04, 168.96, 383.90, 959.75, 2687.29, 8733.72, 34934.88, 191142.79, 5670.38, 2167.65],
    10: [1.57, 2.69, 4.75, 8.71, 16.64, 33.28, 70.25, 158.18, 383.90, 1023.73, 3060.23, 10788.19, 46735.33, 279478.98, 3074273.28],
    11: [1.68, 3.10, 5.94, 14.50, 24.96, 55.46, 131.73, 338.73, 959.75, 3060.23, 11516.99, 53745.96, 349873.73],
    12: [1.80, 4.01, 7.56, 16.19, 38.82, 97.06, 263.50, 790.39, 2687.29, 10788.19, 53745.96, 376221.71, 4880887.65],
    13: [1.96, 4.28, 9.82, 24.04, 63.09, 180.76, 570.83, 2055.99, 8682.42, 46579.83, 349873.73, 4880887.65],
    14: [2.14, 5.13, 13.11, 36.05, 107.16, 359.52, 1360.00, 6164.98, 34934.88, 279478.98, 349873.73],
    15: [2.34, 6.27, 18.02, 56.67, 198.29, 792.15, 3777.48, 22605.92, 191142.79, 3074273.28],
    16: [2.61, 8.25, 25.76, 94.42, 396.58, 1982.89, 12558.29, 112024.58, 1911427.01],
    17: [2.93, 10.08, 38.63, 169.96, 892.29, 5948.66, 56612.29, 1017211.29],
    18: [3.36, 13.43, 61.81, 339.92, 2379.47, 23794.65, 166563.55],
    19: [3.91, 20.81, 108.16, 792.15, 8323.13, 166563.55],
    20: [4.70, 28.22, 216.32, 2379.47, 49918.77],
    21: [5.89, 47.03, 540.78, 11872.32],
    22: [7.84, 93.05, 2167.65],
    23: [11.76, 282.15],
    24: [23.51],
    25: [47.03]
}
def bot_stop(update: Update, context: CallbackContext):
    global bot_active

    user_id = update.effective_user.id

    if user_id != admin_id:
        update.message.reply_text("Only the bot owner can stop the bot.")
        return

    bot_active = False
    update.message.reply_text("The bot has been stopped and will not respond to any further commands.")

def bot_start(update: Update, context: CallbackContext):
    global bot_active

    user_id = update.effective_user.id

    if user_id != admin_id:
        update.message.reply_text("Only the bot owner can start the bot.")
        return

    bot_active = True
    update.message.reply_text("The bot has been started and will now respond to commands.")
def button(update, context):
    global bot_active
    if not bot_active:
        return
    query = update.callback_query
    a = query.data
    c = update.callback_query.message.message_id
    userg = update.callback_query.message.from_user

    un = userg.username
    fn = userg.first_name
    ln = userg.last_name
    na = "{} {}(@{})".format(fn, ln, un)

    if a == "play":
        context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                   message_id=c)
        c = context.bot.createChatInviteLink(chat_id="@DiceableCasino", member_limit=1)
        ink = c['invite_link']
        keyboard = [[InlineKeyboardButton("💬 Group Chat", url=ink)],
                    [InlineKeyboardButton("◀️ Back", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        context.bot.send_message(chat_id=update.effective_user.id,
                                 text="🎲 Challenge a friend!\n\nTo play with your friend, join our group - @DiceableCasino.",
                                 reply_markup=reply_markup)

    elif a == "main_menu":
        context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                   message_id=c)
        connection = sqlite3.connect(database_dice)
        cursor = connection.cursor()
        cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
        for names in cursor:
            balance = f"{names[0]:.2f}"
        connection.close()
        keyboard = [[InlineKeyboardButton("🎲 Play Against Friend", callback_data="play")],
                    [InlineKeyboardButton("💳 Deposit", callback_data="deposit"),
                     InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")]]
        reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        context.bot.send_message(chat_id=update.effective_user.id,
                                 text="🏠 Welcome to the Main Menu\n\nYour current balance is: ${}".format(balance),
                                 reply_markup=reply_markup)

    elif a == "deposit":
        keyboard = [
            [InlineKeyboardButton("Litecoin", callback_data="LTC")],
            [InlineKeyboardButton("Ethereum", callback_data="ETH"),
             InlineKeyboardButton("Tron TRC20", callback_data="TRX")],
            [(InlineKeyboardButton("USDT BEP20", callback_data="USDT")),
             InlineKeyboardButton("BNB BEP20", callback_data="BNB")],
            [InlineKeyboardButton("USDC ERC20", callback_data="USDC")],
            [InlineKeyboardButton("Toncoin", callback_data="TON"),
             InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        context.bot.send_message(chat_id=update.effective_user.id,
                                 text="Please select the coin you'd like to deposit!", reply_markup=reply_markup)

    elif "LTC" in a or "BTC" in a or "TRX" in a or "TON" in a or "ETH" in a or "TRX" in a or "BNB" in a or "USDT" in a or "BNB" in a or "USDC" in a:
        try:
            context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                       message_id=c)
            url = 'https://api.oxapay.com/merchants/request/staticaddress'
            data = {
                'merchant': merchant_key,
                'currency': a,
            }
            response = requests.post(url, data=json.dumps(data))
            result = response.json()
            print(result)
            addr = result['address']
            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM wallet WHERE id = ?", (update.effective_user.id,))
            jobs = cursor.fetchall()
            if len(jobs) == 0:
                cursor.execute("""
                    INSERT INTO wallet (ID, balance, code, amount, name, wins, total_games, total_earnings, total_wagered) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (update.effective_user.id, 0.0, addr, 0.0, na, 0, 0, 0.0, 0.0))
                connection.commit()
                connection.close()
            else:
                connection.execute("UPDATE wallet SET code = ? WHERE ID = ?", (addr, int(update.effective_user.id)))
                connection.commit()
                connection.close()
            crypto_networks= {
                "ETH": "Ethereum (ERC20)",
                "LTC": "Litecoin",
                "TRX": "Tron TRC20",
                "TON": "Toncoin (TON)",
                "USDT": "USDT BEP20",
                "BNB": "BNB BEP20",
                "USDC": "USDC ERC20"
            }
            context.job_queue.run_once(revoke, 3600, name=f"{addr}-{update.effective_user.id}")
            keyboard = [[InlineKeyboardButton("🔙 Cancel Payment", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            context.bot.send_message(chat_id=update.effective_user.id,
                                     text=" **💳{} Deposit:** \n\n __To top up your balance, transfer the desired amount to this LTC address__ \n\nNote:\n  1. One address can only recieve one payment.\n2. The address below expires after 1 hour.\n\nAddress: `{}`\n\n".format(
                                         crypto_networks[a], addr),
                                     reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            print(f"Deposit error: {e}", flush=True)

    elif a == "withdraw":
        context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                   message_id=c)
        connection = sqlite3.connect(database_dice)
        cursor = connection.cursor()
        cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
        for names in cursor:
            ba = names[0]
            balance = f"{ba:.2f}"
        connection.close()
        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        if ba > 4.5:
            context.bot.send_message(chat_id=update.effective_user.id,
                                     text="💸 Withdraw LTC\n\nImportant:\nMinimum withdrawal: 5 LTC\nNetwork fee: 1%\n\nPlease provide your LTC wallet address and the amount you'd like to withdraw in LTC.\n\nExample:\n0x1234567890123456789012345678901234567890-12",
                                     reply_markup=reply_markup)
            return WTH
        else:
            context.bot.send_message(chat_id=update.effective_user.id,
                                     text="The minimum withdrawal is $5, but your balance is only ${}".format(balance)),


############
    elif "dartconfirm" in a:
        a = a.split("-")
        msgid = a[1]
        print(msgid)
        asd = query.message.reply_to_message.from_user.id
        if asd == update.effective_user.id:
            am = a[2]
            am = float(am)
            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
            for names in cursor:
                balance = names[0]
                nb = balance - am
            connection.execute("UPDATE wallet SET balance = ? WHERE ID = ?", (nb, int(update.effective_user.id)))
            connection.commit()
            connection.close()
            na = update.callback_query.from_user.first_name
            context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                       message_id=c)
            keyboard = [
            [InlineKeyboardButton("✅ Accept Match", callback_data=f"dartaccept-{msgid}-{am}")],
            [InlineKeyboardButton("Play Against Bot", callback_data=f"dartbotmatch-{msgid}-{am}")]
]

            reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            context.bot.send_message(chat_id=group_id,
                                     text='{} is inviting you to a dart game!\n\nBet amount: ${}\nChance to win: 50/50\nPayout multiplier: 1.92x\nFirst to 3 points wins.\n\nTo join, click "✅ Accept Match"'.format(
                                         na, f"{am:.2f}"),
                                     reply_to_message_id=msgid, reply_markup=reply_markup)
        else:
            query.answer("❌ You're not allowed to interact with this button!", show_alert=True)
##########
    elif "dartaccept" in a:
        a = a.split("-")
        msgid = a[1]
        am = float(a[2])

        asd = query.message.reply_to_message.from_user.id
        if asd != update.effective_user.id:
            na = update.callback_query.from_user.first_name
            conn = sqlite3.connect(database_dartgame)
            cur = conn.cursor()
            cur.execute("SELECT player_1_name FROM game WHERE game_id = ?", (msgid,))
            for names in cur:
                p1 = names[0]
            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
            for names in cursor:
                balance = names[0]
            if balance >= am:
                nb = balance - am
                connection.execute("UPDATE wallet SET balance = ? WHERE ID = ?", (nb, int(update.effective_user.id)))
                connection.commit()
                connection.close()
                conn.execute("UPDATE game SET game_status = ?, player_2 = ?, player_2_name = ? WHERE game_id = ?",
                             ('started', int(update.effective_user.id), na, msgid))
                conn.commit()
                conn.close()

                context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                           message_id=c)
                context.bot.send_message(chat_id=group_id,
                                         text="Match accepted!\n\nPlayer 1: {}\nPlayer 2: {}\n\n{}'s turn! To start, send a dart emoji (🎯)".format(
                                             p1, na, p1), reply_to_message_id=msgid)
            else:
                connection.close()
                conn.close()
                query.answer("You don't have enough funds to accept this match", show_alert=True)
        else:
            query.answer("❌ You're not allowed to interact with this button!", show_alert=True)
#######
    elif "dartbotmatch" in a:
        a = a.split("-")
        msgid = a[1]
        am = float(a[2])
        asd = query.message.reply_to_message.from_user.id
        if asd == update.effective_user.id:
            na = update.callback_query.from_user.first_name
            conn = sqlite3.connect(database_dartgame)
            cur = conn.cursor()
            cur.execute("SELECT player_1_name FROM game WHERE game_id = ?", (msgid,))
            for names in cur:
                p1 = names[0]
            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM wallet WHERE id = ?", (1234,))
            for names in cursor:
                balance = names[0]
            if balance >= am:
                nb = balance - am
                connection.execute("UPDATE wallet SET balance = ? WHERE ID = ?", (nb, 1234))
                connection.commit()
                connection.close()
                conn.execute("UPDATE game SET game_status = ?, player_2 = ?, player_2_name = ? WHERE game_id = ?",
                             ('started', 1234, 'bot', msgid))
                conn.commit()
                conn.close()

                context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                           message_id=c)
                context.bot.send_message(chat_id=group_id,
                                         text="Match accepted!\n\nPlayer 1: {}\nPlayer 2: {}\n\n{}'s turn! To start, send a dart emoji (🎯)".format(
                                             p1, na, p1), reply_to_message_id=msgid)
            else:
                connection.close()
                conn.close()
                query.answer("The bot doesn't have enough funds to accept this match", show_alert=True)
        else:
            query.answer("❌ You're not allowed to interact with this button!", show_alert=True)

    elif "dartcancel" in a:
        a = a.split("-")
        msgid = a[1]
        asd = query.message.reply_to_message.from_user.id
        print(asd)
        print(update.effective_user.id)
        if asd == update.effective_user.id:
            conn = sqlite3.connect(database_dartgame)
            conn.execute("DELETE FROM game WHERE game_id = ? AND player_1 = ?",
                         (int(msgid), int(update.effective_user.id)))
            conn.commit()
            context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                       message_id=c)
            context.bot.send_message(chat_id=group_id, text='Game canceled ❌', reply_to_message_id=msgid)
            conn.close()
        else:
            query.answer("❌ You're not allowed to interact with this button!", show_alert=True)


#bowl

    elif "bowlconfirm" in a:
        a = a.split("-")
        msgid = a[1]
        print(msgid)
        asd = query.message.reply_to_message.from_user.id
        if asd == update.effective_user.id:
            am = a[2]
            am = float(am)
            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
            for names in cursor:
                balance = names[0]
                nb = balance - am
            connection.execute("UPDATE wallet SET balance = ? WHERE ID = ?", (nb, int(update.effective_user.id)))
            connection.commit()
            connection.close()
            na = update.callback_query.from_user.first_name
            context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                       message_id=c)
            keyboard = [
            [InlineKeyboardButton("✅ Accept Match", callback_data=f"bowlaccept-{msgid}-{am}")],
            [InlineKeyboardButton("Play Against Bot", callback_data=f"bowlbotmatch-{msgid}-{am}")]
]

            reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            context.bot.send_message(chat_id=group_id,
                                     text='{} is inviting you to a bowl  game!\n\nBet amount: ${}\nChance to win: 50/50\nPayout multiplier: 1.92x\nFirst to 3 points wins.\n\nTo join, click "✅ Accept Match"'.format(
                                         na, f"{am:.2f}"),
                                     reply_to_message_id=msgid, reply_markup=reply_markup)
        else:
            query.answer("❌ You're not allowed to interact with this button!", show_alert=True)

    elif "bowlaccept" in a:
        a = a.split("-")
        msgid = a[1]
        am = float(a[2])

        asd = query.message.reply_to_message.from_user.id
        if asd != update.effective_user.id:
            na = update.callback_query.from_user.first_name
            conn = sqlite3.connect(database_bowlgame)
            cur = conn.cursor()
            cur.execute("SELECT player_1_name FROM game WHERE game_id = ?", (msgid,))
            for names in cur:
                p1 = names[0]
            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
            for names in cursor:
                balance = names[0]
            if balance >= am:
                nb = balance - am
                connection.execute("UPDATE wallet SET balance = ? WHERE ID = ?", (nb, int(update.effective_user.id)))
                connection.commit()
                connection.close()
                conn.execute("UPDATE game SET game_status = ?, player_2 = ?, player_2_name = ? WHERE game_id = ?",
                             ('started', int(update.effective_user.id), na, msgid))
                conn.commit()
                conn.close()

                context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                           message_id=c)
                context.bot.send_message(chat_id=group_id,
                                         text="Match accepted!\n\nPlayer 1: {}\nPlayer 2: {}\n\n{}'s turn! To start, send a bowl emoji (🎳)".format(
                                             p1, na, p1), reply_to_message_id=msgid)
            else:
                connection.close()
                conn.close()
                query.answer("You don't have enough funds to accept this match", show_alert=True)
        else:
            query.answer("❌ You're not allowed to interact with this button!", show_alert=True)

    elif "bowlbotmatch" in a:
        a = a.split("-")
        msgid = a[1]
        am = float(a[2])
        asd = query.message.reply_to_message.from_user.id
        if asd == update.effective_user.id:
            na = update.callback_query.from_user.first_name
            conn = sqlite3.connect(database_bowlgame)
            cur = conn.cursor()
            cur.execute("SELECT player_1_name FROM game WHERE game_id = ?", (msgid,))
            for names in cur:
                p1 = names[0]
            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM wallet WHERE id = ?", (1234,))
            for names in cursor:
                balance = names[0]
            if balance >= am:
                nb = balance - am
                connection.execute("UPDATE wallet SET balance = ? WHERE ID = ?", (nb, 1234))
                connection.commit()
                connection.close()
                conn.execute("UPDATE game SET game_status = ?, player_2 = ?, player_2_name = ? WHERE game_id = ?",
                             ('started', 1234, 'bot', msgid))
                conn.commit()
                conn.close()

                context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                           message_id=c)
                context.bot.send_message(chat_id=group_id,
                                         text="Match accepted!\n\nPlayer 1: {}\nPlayer 2: {}\n\n{}'s turn! To start, send a bowl  emoji (🎳)".format(
                                             p1, na, p1), reply_to_message_id=msgid)
            else:
                connection.close()
                conn.close()
                query.answer("The bot doesn't have enough funds to accept this match", show_alert=True)
        else:
            query.answer("❌ You're not allowed to interact with this button!", show_alert=True)

    elif "bowlcancel" in a:
        a = a.split("-")
        msgid = a[1]
        asd = query.message.reply_to_message.from_user.id
        print(asd)
        print(update.effective_user.id)
        if asd == update.effective_user.id:
            conn = sqlite3.connect(database_bowlgame)
            conn.execute("DELETE FROM game WHERE game_id = ? AND player_1 = ?",
                         (int(msgid), int(update.effective_user.id)))
            conn.commit()
            context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                       message_id=c)
            context.bot.send_message(chat_id=group_id, text='Game canceled ❌', reply_to_message_id=msgid)
            conn.close()
        else:
            query.answer("❌ You're not allowed to interact with this button!", show_alert=True)


#dice
    elif "confirm" in a:
        a = a.split("-")
        msgid = a[1]
        print(msgid)
        asd = query.message.reply_to_message.from_user.id
        if asd == update.effective_user.id:
            am = a[2]
            am = float(am)
            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
            for names in cursor:
                balance = names[0]
                nb = balance - am
            connection.execute("UPDATE wallet SET balance = ? WHERE ID = ?", (nb, int(update.effective_user.id)))
            connection.commit()
            connection.close()
            na = update.callback_query.from_user.first_name
            context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                       message_id=c)
            keyboard = [
            [InlineKeyboardButton("✅ Accept Match", callback_data=f"accept-{msgid}-{am}")],
            [InlineKeyboardButton("Play Against Bot", callback_data=f"botmatch-{msgid}-{am}")]
]

            reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            context.bot.send_message(chat_id=group_id,
                                     text='{} is inviting you to a dice game!\n\nBet amount: ${}\nChance to win: 50/50\nPayout multiplier: 1.92x\nFirst to 3 points wins.\n\nTo join, click "✅ Accept Match"'.format(
                                         na, f"{am:.2f}"),
                                     reply_to_message_id=msgid, reply_markup=reply_markup)
        else:
            query.answer("❌ You're not allowed to interact with this button!", show_alert=True)



    elif "accept" in a:
        a = a.split("-")
        msgid = a[1]
        am = float(a[2])

        asd = query.message.reply_to_message.from_user.id
        if asd != update.effective_user.id:
            na = update.callback_query.from_user.first_name
            conn = sqlite3.connect(database_dicegame)
            cur = conn.cursor()
            cur.execute("SELECT player_1_name FROM game WHERE game_id = ?", (msgid,))
            for names in cur:
                p1 = names[0]
            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
            for names in cursor:
                balance = names[0]
            if balance >= am:
                nb = balance - am
                connection.execute("UPDATE wallet SET balance = ? WHERE ID = ?", (nb, int(update.effective_user.id)))
                connection.commit()
                connection.close()
                conn.execute("UPDATE game SET game_status = ?, player_2 = ?, player_2_name = ? WHERE game_id = ?",
                             ('started', int(update.effective_user.id), na, msgid))
                conn.commit()
                conn.close()

                context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                           message_id=c)
                context.bot.send_message(chat_id=group_id,
                                         text="Match accepted!\n\nPlayer 1: {}\nPlayer 2: {}\n\n{}'s turn! To start, send a dice emoji (🎲)".format(
                                             p1, na, p1), reply_to_message_id=msgid)
            else:
                connection.close()
                conn.close()
                query.answer("You don't have enough funds to accept this match", show_alert=True)
        else:
            query.answer("❌ You're not allowed to interact with this button!", show_alert=True)

    elif "botmatch" in a:
        a = a.split("-")
        msgid = a[1]
        am = float(a[2])
        asd = query.message.reply_to_message.from_user.id
        if asd == update.effective_user.id:
            na = update.callback_query.from_user.first_name
            conn = sqlite3.connect(database_dicegame)
            cur = conn.cursor()
            cur.execute("SELECT player_1_name FROM game WHERE game_id = ?", (msgid,))
            for names in cur:
                p1 = names[0]
            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM wallet WHERE id = ?", (1234,))
            for names in cursor:
                balance = names[0]
            if balance >= am:
                nb = balance - am
                connection.execute("UPDATE wallet SET balance = ? WHERE ID = ?", (nb, 1234))
                connection.commit()
                connection.close()
                conn.execute("UPDATE game SET game_status = ?, player_2 = ?, player_2_name = ? WHERE game_id = ?",
                             ('started', 1234, 'bot', msgid))
                conn.commit()
                conn.close()

                context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                           message_id=c)
                context.bot.send_message(chat_id=group_id,
                                         text="Match accepted!\n\nPlayer 1: {}\nPlayer 2: {}\n\n{}'s turn! To start, send a dice emoji (🎲)".format(
                                             p1, na, p1), reply_to_message_id=msgid)
            else:
                connection.close()
                conn.close()
                query.answer("The bot doesn't have enough funds to accept this match", show_alert=True)
        else:
            query.answer("❌ You're not allowed to interact with this button!", show_alert=True)

    elif "cancel" in a:
        a = a.split("-")
        msgid = a[1]
        asd = query.message.reply_to_message.from_user.id
        print(asd)
        print(update.effective_user.id)
        if asd == update.effective_user.id:
            conn = sqlite3.connect(database_dicegame)
            conn.execute("DELETE FROM game WHERE game_id = ? AND player_1 = ?",
                         (int(msgid), int(update.effective_user.id)))
            conn.commit()
            context.bot.delete_message(chat_id=update.callback_query.message.chat_id,
                                       message_id=c)
            context.bot.send_message(chat_id=group_id, text='Game canceled ❌', reply_to_message_id=msgid)
            conn.close()
        else:
            query.answer("❌ You're not allowed to interact with this button!", show_alert=True)

    elif "reject" in a:
        a = a.split("-")
        msgid = int(a[1])
        am = float(a[2])
        asd = query.message.reply_to_message.from_user.id
        if asd == update.effective_user.id:
            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
            for names in cursor:
                balance = names[0]
                nb = balance + am
            connection.execute("UPDATE wallet SET balance = ? WHERE ID = ?", (nb, int(update.effective_user.id)))
            connection.commit()
            connection.close()
            conn = sqlite3.connect(database_dicegame)
            conn.execute("DELETE FROM game WHERE game_id = ? AND player_1 = ?",
                         (int(msgid), int(update.effective_user.id)))
            conn.commit()
            conn.close()
            context.bot.delete_message(chat_id=update.callback_query.message.chat_id, message_id=c)
            context.bot.send_message(chat_id=group_id, text='Game canceled ❌', reply_to_message_id=msgid)
        else:
            query.answer("❌ You're not allowed to interact with this button!", show_alert=True)

    else:
        asd = query.message.reply_to_message.from_user.id
        if asd == update.effective_user.id:
            if context.user_data.get('game_over', False):
                return

            if query.data == "cashout":
                handle_cashout(query, context)
                return

            try:
                x, y = map(int, query.data.split(','))
            except ValueError:
                return

            grid = context.user_data['grid']

            if grid[x][y] == '💣':
                context.user_data['revealed'] = {(i, j) for i in range(DEFAULT_SIZE) for j in range(DEFAULT_SIZE)}
                context.user_data['game_over'] = True
                message_text = '💥 Oh no! You stepped on a mine! 💣\nGame over! You lost this round.'
                keyboard = []
                for i in range(DEFAULT_SIZE):
                    row = []
                    for j in range(DEFAULT_SIZE):
                        text = context.user_data['grid'][i][j] if context.user_data['grid'][i][j] != ' ' else '❇️'
                        row.append(InlineKeyboardButton(text, callback_data=f"{i},{j}"))
                    keyboard.append(row)
                reply_markup = InlineKeyboardMarkup(keyboard)

                query.edit_message_text(
                    message_text,
                    reply_markup=reply_markup
                )
                return
            context.user_data['revealed'].add((x, y))
            send_grid(query.message, context, send_new_message=False)
        else:
            query.answer("❌ You're not allowed to interact with this button!", show_alert=True)


def is_valid_erc20_address(address):
    try:

        if address.startswith('L') or address.startswith('M'):
            decoded = base58.b58decode_check(address)
            return len(decoded) == 21

        if address.startswith('ltc1'):
            hrp, data = bech32.bech32_decode(address)
            if hrp == "ltc" and data:
                return True

        return False
    except Exception as e:

        return False


def start(update, context):
    global bot_active
    if not bot_active:
        return
    ref_id = update.message.text
    ref_id = ref_id.split()
    print(ref_id)
    if len(ref_id) > 1:
        asf = (ref_id[1]).strip()
        if asf == "deposit":
            keyboard = [
                [ InlineKeyboardButton("Ethereum", callback_data="ETH")],
                [InlineKeyboardButton("Litecoin", callback_data="LTC"),
                 InlineKeyboardButton("Tron", callback_data="TRX")],
                [(InlineKeyboardButton("USDT BEP20", callback_data="USDT")),
                 InlineKeyboardButton("BNB BEP20", callback_data="BNB")],
                [InlineKeyboardButton("USDC ERC20", callback_data="USDC")],
                [InlineKeyboardButton("Toncoin", callback_data="TON"),
                 InlineKeyboardButton("Back", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            context.bot.send_message(chat_id=update.effective_user.id,
                                     text="Please Select Your Coin That You Want To Deposit.",
                                     reply_markup=reply_markup)
            return
        elif asf == "withdraw":
            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
            for names in cursor:
                ba = names[0]
                balance = f"{ba:.2f}"
            connection.close()
            keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            if ba > 9:
                context.bot.send_message(chat_id=update.effective_user.id,
                                         text="Litecoin withdrawal\n\nPlease note:\nMinimum withdrawal amount: 5 USD\nNetwork fee: 1%\n\nPlease send your LTC wallet Address and the desired withdrawal amount in USD to the chat.\n\nExample:\n0x1234567890123456789012345678901234567890-12",
                                         reply_markup=reply_markup)
                return WTH
            else:
                context.bot.send_message(chat_id=update.effective_user.id,
                                         text=f"Minimum withdrawal is 5 and your balance is ${balance:.2f}",
                                         reply_markup=reply_markup)
    userg = update.message.from_user
    if userg.username:
        usaf = userg.username
    elif userg.first_name and userg.last_name:
        usaf = f"{userg.first_name} {userg.last_name}"  # Full name
    elif userg.first_name:
        usaf = userg.first_name  # First name only
    else:
        usaf = f"User {userg.id}"  # Fallback to user ID if no name is available

    connection = sqlite3.connect(database_dice)
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM wallet WHERE id = ?", (update.effective_user.id,))
    jobs = cursor.fetchall()

    if len(jobs) == 0:
        cursor.execute("""
            INSERT INTO wallet (ID, balance, code, amount, name, wins, total_games, total_earnings, total_wagered) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (update.effective_user.id, 0.0, "0", 0.0, usaf, 0, 0, 0.0, 0.0)
                       )
        connection.commit()

    cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
    for names in cursor:
        balance = balance = f"{names[0]:.2f}"

    connection.close()

    keyboard = [
        [InlineKeyboardButton("🎲 Play Against friend", callback_data="play")],
        [InlineKeyboardButton("💳 Deposit", callback_data="deposit"),
         InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    context.bot.send_message(chat_id=update.effective_user.id, text="🏠 Main Menu\n\nCurrent Balance: ${}".format(balance),
                             reply_markup=reply_markup)
def calculate_payout(bet_amount, diamonds, bombs):
    try:
        if diamonds < 1 or bombs < 1 or bombs > len(multipliers[diamonds]):
            return 0

        multiplier = multipliers[diamonds][bombs - 1]
        payout = bet_amount * multiplier
        return payout
    except (KeyError, IndexError):
        return 0

def mines(update: Update, context: CallbackContext) -> None:
    global bot_active
    if not bot_active:
        return
    userg = update.message.from_user
    if userg.username:
        usaf = userg.username
    elif userg.first_name and userg.last_name:
        usaf = f"{userg.first_name} {userg.last_name}"  # Full name
    elif userg.first_name:
        usaf = userg.first_name  # First name only
    else:
        usaf = f"User {userg.id}"  # Fallback to user ID if no name is available

    if len(context.args) != 2:
        update.message.reply_text("Please enter /mines, your bet amount, and the number of mines to start playing.")
        return

    if update.message.chat.type != 'group' and update.message.chat.type != 'supergroup':
        update.message.reply_text("You can only play Mines in the Diceable Casino group chat.")
        return

    if update.message.chat_id != group_id:
        update.message.reply_text("This game is only available in the Diceable Casino group.")
        return

    num_mines = int(context.args[1])
    if num_mines <= 0 or num_mines >= DEFAULT_SIZE * DEFAULT_SIZE:
        update.message.reply_text(f"Please choose a number of mines between 1 and {DEFAULT_SIZE * DEFAULT_SIZE - 1}.")
        return

    try:
        connection = sqlite3.connect(database_dice)
        cursor = connection.cursor()
        cursor.execute("SELECT id FROM wallet WHERE id = ?", (update.effective_user.id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO wallet (ID, balance, code, amount, name, wins, total_games, total_earnings, total_wagered) \
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (update.effective_user.id, 0.0, "0", 0.0, usaf, 0, 0, 0.0, 0.0))
            connection.commit()

        cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
        balance = cursor.fetchone()[0]
        cursor.execute("SELECT balance FROM wallet WHERE id = ?", (1234,))
        bot_balance = cursor.fetchone()[0]

        if context.args[0].lower() == "all":
            bet_amount = min(balance, maximum_bet_amount)
        else:
            bet_amount = float(context.args[0])

        if bet_amount < 0.5:
            update.message.reply_text("The minimum bet amount is $0.5.")
            return
        if bet_amount > maximum_bet_amount:
            update.message.reply_text("You can bet up to $25 maximum.")
            return
        if balance < bet_amount:
            connection.close()
            update.message.reply_text("Insufficient balance to place this bet.")
            return
        elif bot_balance < bet_amount:
            connection.close()
            update.message.reply_text("The bot doesn't have enough funds to accept this bet.")
            return
        else:
            new_balance = balance - bet_amount
            bot_new_balance = bot_balance + bet_amount
            connection.execute("UPDATE wallet SET balance = ? WHERE ID = ?", (new_balance, update.effective_user.id))
            connection.execute("UPDATE wallet SET balance = ? WHERE ID = ?", (bot_new_balance, 1234))
            connection.commit()
            connection.close()

    except ValueError:
        update.message.reply_text("Please enter valid numbers for the bet amount and number of mines.")
        return

    context.user_data['grid'] = generate_grid(num_mines)
    context.user_data['revealed'] = set()
    context.user_data['bet_amount'] = bet_amount
    context.user_data['num_mines'] = num_mines
    context.user_data['game_over'] = False
    context.user_data['processing'] = False

    send_grid(update.message, context, send_new_message=True)



def adjust_mine_probability(base_probability, revealed_cells):
    """
    Adjust the base probability of hitting a mine by the house edge.
    """

    if base_probability > 0.80:
        house_edge = 0.03  # 3% house edge
    elif 0.50 <= base_probability <= 0.80:
        house_edge = 0.03  # 3% house edge
    else:
        house_edge = 0.03  # 3% house edge

    house_edge += (revealed_cells // 2) * 0.01  # 1% per 2 revealed cells

    new_probability = base_probability - house_edge
    if new_probability < 0:
        new_probability = 0

    return new_probability

def swap_diamond_with_random_mine(grid, x, y, revealed):
    """
    Swap the clicked diamond (💎) with a random mine (💣), making the player lose.
    """
    if grid[x][y] != '❇️':
        return grid

    mine_positions = [(i, j) for i in range(len(grid)) for j in range(len(grid[i])) if grid[i][j] == '💣']

    if not mine_positions:
        return grid

    mine_x, mine_y = random.choice(mine_positions)

    grid[x][y], grid[mine_x][mine_y] = grid[mine_x][mine_y], grid[x][y]

    return grid


def swap_mine_with_unrevealed_diamond(grid, x, y, revealed):
    """
    Swap the clicked mine (💣) with a diamond (💎) in an unrevealed location.
    """
    if grid[x][y] != '💣':
        return grid

    unrevealed_diamond_positions = [(i, j) for i in range(len(grid)) for j in range(len(grid[i]))
                                    if grid[i][j] == '❇️' and (i, j) not in revealed]

    if not unrevealed_diamond_positions:
        return grid

    diamond_x, diamond_y = random.choice(unrevealed_diamond_positions)

    grid[x][y], grid[diamond_x][diamond_y] = grid[diamond_x][diamond_y], grid[x][y]
    print(f'Swap mine w diamond grid: {grid}',flush=True)
    print("Swapped the mine with an unrevealed diamond!",flush=True)

    return grid

def generate_grid(num_mines):
    if num_mines < 0 or num_mines >= DEFAULT_SIZE * DEFAULT_SIZE:
        raise ValueError("Number of mines must be between 0 and the grid size (excluding full grid).")

    grid = [[' ' for _ in range(DEFAULT_SIZE)] for _ in range(DEFAULT_SIZE)]
    total_cells = DEFAULT_SIZE * DEFAULT_SIZE

    mines = random.sample(range(total_cells), num_mines)
    for mine in mines:
        x, y = divmod(mine, DEFAULT_SIZE)
        grid[x][y] = '💣'

    available_cells = [(i, j) for i in range(DEFAULT_SIZE) for j in range(DEFAULT_SIZE) if grid[i][j] == ' ']
    num_diamonds = 25 - num_mines
    if num_diamonds < 0:
        raise ValueError("Not enough space to place the requested number of mines and diamonds.")
    diamonds = random.sample(available_cells, num_diamonds)
    for (x, y) in diamonds:
        grid[x][y] = '❇️'

    return grid



def send_grid(message, context: CallbackContext, send_new_message: bool = False, reveal_full: bool = False,
              disable: bool = False):
    """Send or update the current state of the grid, with optional button disabling."""
    keyboard = []
    for i in range(DEFAULT_SIZE):
        row = []
        for j in range(DEFAULT_SIZE):
            if reveal_full or (i, j) in context.user_data.get('revealed', set()):
                text = context.user_data['grid'][i][j] if context.user_data['grid'][i][j] != ' ' else '❇️'
            else:
                text = '⬜️'

            if disable:
                callback_data = None
            else:
                callback_data = f"{i},{j}"

            row.append(InlineKeyboardButton(text, callback_data=callback_data))
        keyboard.append(row)

    if not context.user_data.get('game_over', False):
        num_diamonds = len(context.user_data['revealed'])
        payout = calculate_payout(context.user_data['bet_amount'], num_diamonds, context.user_data['num_mines'])
        payout_text = f"{payout:.2f}" if payout > 0 else "0.00"

        if disable:
            keyboard.append([InlineKeyboardButton(f"Cash Out (${payout_text})", callback_data=None)])
        else:
            keyboard.append([InlineKeyboardButton(f"Cash Out (${payout_text})", callback_data="cashout")])

    reply_markup = InlineKeyboardMarkup(keyboard) if not context.user_data.get('game_over', False) else None

    if context.user_data.get('game_over', False):
        game_over_text = "💥 Oh no! You stepped on a mine! 💣\nGame over! You lost this round!\n"
    else:
        game_over_text = ""

    if send_new_message:
        message.reply_text(
            f'{game_over_text}💣 Minesweeper\nYour Bet: {context.user_data["bet_amount"]}',
            reply_markup=reply_markup
        )
    else:
        message.edit_text(
            f'{game_over_text}💣 Minesweeper\nYour Bet: {context.user_data["bet_amount"]}',
            reply_markup=reply_markup
        )

def send_text_grid(message, context: CallbackContext):
    """Send the fully revealed grid as an inline keyboard after the game is over."""
    grid = context.user_data['grid']
    keyboard = []

    for i in range(len(grid)):
        row = []
        for j in range(len(grid[i])):
            text = grid[i][j] 
            row.append(InlineKeyboardButton(text, callback_data='noop')) 
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    message.edit_text("Here’s the complete grid:", reply_markup=reply_markup)

def handle_mine_click(update: Update, context: CallbackContext) -> None:
    global bot_active
    if not bot_active:
        return
    logger = logging.getLogger(__name__)
    logger.info(f"Processing mine click...")

    query = update.callback_query
    user = query.from_user

    # Rate limiting
    current_time = time.time()
    last_action_time = context.user_data.get('last_action_time', 0)
    MIN_ACTION_INTERVAL = 0.5  # 0.5 seconds

    if current_time - last_action_time < MIN_ACTION_INTERVAL:
        query.answer("⏳ Please wait a moment before your next action.")
        return

    if context.user_data.get('processing', False):
        query.answer("Please wait, processing your previous move.", show_alert=True)
        return

    # Start processing
    context.user_data['processing'] = True
    context.user_data['last_action_time'] = current_time  # Update last action time

    try:
        try:
            x, y = map(int, query.data.split(','))
        except ValueError:
            context.user_data['processing'] = False
            return

        grid = context.user_data['grid']

        if context.user_data.get('game_over', False):
            query.answer("The game is over. Start a new game to play again.", show_alert=True)
            context.user_data['processing'] = False
            return

        if (x, y) in context.user_data['revealed']:
            query.answer("You've already revealed this cell!", show_alert=True)
            context.user_data['processing'] = False
            return

        num_mines = context.user_data['num_mines']
        total_cells = DEFAULT_SIZE * DEFAULT_SIZE
        num_diamonds = total_cells - num_mines

        remaining_cells = total_cells - len(context.user_data['revealed'])
        logger.info(f"Remaining cells: {remaining_cells}")
        logger.info(f"Remaining mines: {num_mines}")
        remaining_diamonds = remaining_cells - num_mines
        logger.info(f"Remaining diamonds: {remaining_diamonds}")

        base_probability = remaining_diamonds / remaining_cells
        logger.info(f"Base probability: {base_probability:.2f}")
        adjusted_probability = adjust_mine_probability(base_probability, len(context.user_data['revealed']))
        logger.info(f"Adjusted probability: {adjusted_probability:.2f}")
        random_number = random.random()
        logger.info(f'Random number: {random_number:.2f}')

        if random_number > adjusted_probability:
            print("Swapping mines around...", flush=True)
            grid = swap_diamond_with_random_mine(grid, x, y, context.user_data['revealed'])
        logger.info(grid)

        if grid[x][y] == '💣' and not random_number > adjusted_probability:
            print('Swapping mine to diamond', flush=True)
            grid = swap_mine_with_unrevealed_diamond(grid, x, y, context.user_data['revealed'])

        if grid[x][y] == '💣' and random_number > adjusted_probability:
            context.user_data['revealed'] = {(i, j) for i in range(DEFAULT_SIZE) for j in range(DEFAULT_SIZE)}
            context.user_data['game_over'] = True
            message_text = '💥 Oh no! You stepped on a mine! 💣\nGame over! You lost this round.'

            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()

            cursor.execute("SELECT total_games, wins, total_wagered FROM wallet WHERE id = ?", (update.effective_user.id,))
            result = cursor.fetchone()

            if result:
                total_games, wins, total_wagered = result
                total_games += 1
                total_wagered += context.user_data['bet_amount']

                cursor.execute(
                    "UPDATE wallet SET total_games = ?, total_wagered = ? WHERE id = ?",
                    (total_games, total_wagered, update.effective_user.id)
                )

            connection.commit()
            connection.close()

            send_grid(query.message, context, reveal_full=True)
            send_text_grid(query.message, context)
        else:
            print("Good move!", flush=True)
            context.user_data['revealed'].add((x, y))
            send_grid(query.message, context)
            query.answer("Great choice!")

    except Exception as e:
        logging.exception("Error in handle_mine_click:")
        query.answer("An error occurred. Please try again.")
    finally:
        # Reset the processing flag
        context.user_data['processing'] = False




def handle_cashout(query: Update, context: CallbackContext) -> None:
    global bot_active
    if not bot_active:
        return
    if context.user_data.get('game_over', False):
        return

    revealed_cells = context.user_data.get('revealed', set())
    num_diamonds = sum(1 for (i, j) in revealed_cells if context.user_data['grid'][i][j] == '❇️')
    num_bombs = context.user_data['num_mines']
    bet_amount = context.user_data['bet_amount']
    payout = calculate_payout(bet_amount, num_diamonds, num_bombs)

    connection = sqlite3.connect(database_dice)
    cursor = connection.cursor()
    cursor.execute("SELECT balance, wins, total_games, total_earnings, total_wagered FROM wallet WHERE id = ?",
                   (query.from_user.id,))
    balance, wins, total_games, total_earnings, total_wagered = cursor.fetchone()

    new_balance = balance + payout
    wins += 1
    total_games += 1
    total_earnings += payout
    total_wagered += payout

    cursor.execute(
        "UPDATE wallet SET balance = ?, wins = ?, total_games = ?, total_earnings = ?, total_wagered = ? WHERE id = ?",
        (new_balance, wins, total_games, total_earnings, total_wagered, query.from_user.id))

    bot_balance = cursor.execute("SELECT balance FROM wallet WHERE id = ?", (1234,)).fetchone()[0]
    cursor.execute("UPDATE wallet SET balance = ? WHERE id = ?", (bot_balance - payout, 1234))
    connection.commit()
    connection.close()

    context.user_data['revealed'] = {(i, j) for i in range(DEFAULT_SIZE) for j in range(DEFAULT_SIZE)}
    context.user_data['game_over'] = True

    username = query.from_user.username or query.from_user.id
    wins_channel_id = "@diceablewins"
    wins_message = f"@{username} Just won ${payout:.2f} in 💣 Mines!"
    context.bot.send_message(chat_id=wins_channel_id, text=wins_message)

    query.edit_message_text(f'💰 You cashed out! Your payout is ${payout:.2f}.\nGame over!')


def revoke(context: CallbackContext) -> None:
    try:
        job = context.job
        text = job.name
        b = text.split("-")
        addr = b[0]
        ida = b[1]
        connection = sqlite3.connect(database_dice)
        connection.execute("UPDATE wallet SET code = ? WHERE ID = ?", ('0', int(ida)))
        connection.commit()
        url = 'https://api.oxapay.com/merchants/revoke/staticaddress'
        data = {
            'merchant': merchant_key,
            'address': addr
        }
        response = requests.post(url, data=json.dumps(data))
        result = response.json()
        context.bot.send_message(chat_id=ida, text="Transcation Expired")
    except:
        pass



def bal(update, context):
    global bot_active
    if not bot_active:
        return

    if update.message.chat.type != 'group' and update.message.chat.type != 'supergroup':
        update.message.reply_text("You can only run this command in the Diceable Casino group")
        return

    if update.message.chat_id != group_id:
        update.message.reply_text("You can only run this command in the Diceable Casino group")
        return

    userg = update.message.from_user
    if userg.username:
        usaf = userg.username
    elif userg.first_name and userg.last_name:
        usaf = f"{userg.first_name} {userg.last_name}"  # Full name
    elif userg.first_name:
        usaf = userg.first_name  # First name only
    else:
        usaf = f"User {userg.id}"  # Fallback to user ID if no name is available
    connection = sqlite3.connect(database_dice)
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM wallet WHERE id = ?", (update.effective_user.id,))
    jobs = cursor.fetchall()
    if len(jobs) == 0:
        cursor.execute("""
            INSERT INTO wallet (ID, balance, code, amount, name, wins, total_games, total_earnings, total_wagered) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (update.effective_user.id, 0.0, "0", 0.0, usaf, 0, 0, 0.0, 0.0))
        connection.commit()
    cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
    for names in cursor:
        ba = float(names[0])
        balance = f"{ba:.2f}"
    connection.close()
    keyboard = [[InlineKeyboardButton("💳 Deposit", url=f"{telegram_link}?start=deposit"),
                 InlineKeyboardButton("💸 Withdraw", url=f"{telegram_link}?start=withdraw")]]
    reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    context.bot.send_message(chat_id=group_id, text="Your balance: ${}".format(balance),
                             reply_to_message_id=update.message.message_id, reply_markup=reply_markup)


def botbal(update, context):
    global bot_active
    if not bot_active:
        return

    if update.message.chat.type != 'group' and update.message.chat.type != 'supergroup':
        update.message.reply_text("You can only run this command in the Diceable Casino group")
        return

    if update.message.chat_id != group_id:
        update.message.reply_text("You can only run this command in the Diceable Casino group")
        return

    connection = sqlite3.connect(database_dice)
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM wallet WHERE id = ?", (1234,))
    jobs = cursor.fetchall()

    if len(jobs) == 0:
        cursor.execute("""
            INSERT INTO wallet (ID, balance, code, amount, name, wins, total_games, total_earnings, total_wagered) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (1234, 0.0, "0", 0.0, "bot", 0, 0, 0.0, 0.0))
        connection.commit()
    cursor.execute("SELECT balance FROM wallet WHERE id = ?", (1234,))
    for names in cursor:
        ba = float(names[0])
        balance = f"{ba:.2f}"
    connection.close()
    context.bot.send_message(chat_id=group_id, text="💰 Available balance of the bot: ${}".format(balance),
                             reply_to_message_id=update.message.message_id)

def lb(update, context):
    global bot_active
    if not bot_active:
        return

    if update.message.chat.type != 'group' and update.message.chat.type != 'supergroup':
        update.message.reply_text("You can only run this command in the Diceable Casino group")
        return

    if update.message.chat_id != group_id:
        update.message.reply_text("You can only run this command in the Diceable Casino group")
        return

    excluded_user_ids = [1651190900, 1234]

    try:
        userg = update.message.from_user
        usaf = userg.first_name

        connection = sqlite3.connect(database_dice)
        cursor = connection.cursor()

        cursor.execute("SELECT total_earnings, name, ID FROM wallet ORDER BY total_earnings  DESC")
        results = cursor.fetchall()

        tex = "🏆 Leaderboard\n\nMost Won all time\n\n"
        a = 0
        leaderboard_limit = 10

        for names in results:
            if names[2] in excluded_user_ids:
                continue

            a += 1
            te = round(names[0], 2)
            na = names[1]
            tex += "{}) {} - ${:.2f}\n".format(a, na, te)

            if a >= leaderboard_limit:
                break

        cursor.close()
        connection.close()

        context.bot.send_message(chat_id=group_id, text=tex, reply_to_message_id=update.message.message_id)

    except sqlite3.DatabaseError as e:
        print(f"Database error: {e}")
        context.bot.send_message(chat_id=group_id, text="No Data Available",
                                 reply_to_message_id=update.message.message_id)

def stats(update, context):
    global bot_active
    if not bot_active:
        return

    if update.message.chat.type not in ['group', 'supergroup'] or update.message.chat_id != group_id:
        update.message.reply_text("You can only run this command in the Diceable Casino group")
        return

    user = update.message.from_user
    username = user.username if user.username else user.first_name
    user_id = user.id

    connection = sqlite3.connect(database_dice)
    cursor = connection.cursor()

    cursor.execute("SELECT total_games, total_wagered, total_earnings, wins FROM wallet WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    connection.close()

    if result:
        total_games, total_wagered, total_earnings, wins = result
    else:
        total_games, total_wagered, total_earnings, wins = 0, 0.0, 0.0, 0

    win_percentage = (wins / total_games) * 100 if total_games > 0 else 0
    total_earnings_formatted = f"{total_earnings:.2f}"
    total_wagered_formatted = f"${total_wagered:.2f}"

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"📊 **Stats of {username}**\n\n"
            f"**💰Total Wagered**: {total_wagered_formatted}\n"
            f"🎮 **Games Played:** {total_games}\n"
            f"🏆 **Wins:** {wins} ({win_percentage:.2f}%)\n"
            f"💰 **Total Won:** ${total_earnings_formatted}"
        ),
        parse_mode='Markdown'
    )
def dice_handler(update, context):
    global bot_active
    if not bot_active:
        return
    message = update.message

    if message.forward_from or message.forward_from_chat:
        return

    if message.sticker:
        return

    if not message.dice:
        return

    if message.dice.emoji != '🎲':
        return

    val = update.message.dice.value
    conn = sqlite3.connect(database_dicegame)
    cur = conn.cursor()

    cur.execute("SELECT player_2,player_2_name FROM game WHERE turn_number=? AND game_status='started' AND player_1=?",
                (update.effective_user.id, update.effective_user.id))
    jobs = cur.fetchall()

    if len(jobs) != 0:
        for names in jobs:
            p2 = names[0]
            p2n = names[1]

        conn.execute(
            "UPDATE game SET total_turn=?, turn_number=? WHERE game_status='started' AND player_1=? AND player_2=?",
            (val, p2, update.effective_user.id, p2))
        conn.commit()
        conn.close()
        context.bot.send_message(chat_id=group_id, text="{}, your turn!".format(p2n),
                                 reply_to_message_id=update.message.message_id)

        if p2n == "bot":
            message = bot_player.send_dice(chat_id=update.effective_chat.id)
            val = message.dice.value
            conn = sqlite3.connect(database_dicegame)
            cur = conn.cursor()

            cur.execute(
                "SELECT player_1_name,player_1_wins,player_2_name,player_2_wins,total_turn,player_1,player_2,Amount FROM game WHERE turn_number=? AND game_status='started' AND player_2=?",
                (1234, 1234))
            jobs = cur.fetchall()

            if len(jobs) != 0:
                for names in jobs:
                    p1n = names[0]
                    p1w = names[1]
                    p2n = names[2]
                    p2w = names[3]
                    num = names[4]
                    p1 = names[5]
                    p2 = names[6]
                    am = round(names[7] * 1.92, 2)

                if num > val:
                    nw = p1w + 1
                    if nw == 3:
                        conn.execute(
                            "UPDATE game SET total_turn=?, turn_number=?,player_1_wins=?,game_status='completed' WHERE game_status='started' AND player_1=? AND player_2=?",
                            (val, p1, nw, p1, p2))
                        conn.commit()
                        conn.close()

                        connection = sqlite3.connect(database_dice)
                        cursor = connection.cursor()

                        cursor.execute(
                            "SELECT balance,wins,total_games,total_earnings,total_wagered FROM wallet WHERE id=?",
                            (p1,))
                        for names in cursor:
                            balance = names[0]
                            nb = am + balance
                            wins = names[1]
                            wins = wins + 1
                            tg = names[2]
                            tg = tg + 1
                            te = names[3]
                            te = te + am
                            tw = names[4]
                            tw = tw + am

                        cursor.execute("SELECT total_games FROM wallet WHERE id=?", (1234,))
                        for names in cursor:
                            p1tg = names[0]
                            p1tg = p1tg + 1

                        connection.execute(
                            "UPDATE wallet SET balance=?, wins=?, total_games=?, total_earnings=?, total_wagered=? WHERE id=?",
                            (nb, wins, tg, te, tw, p1))
                        connection.commit()

                        connection.execute("UPDATE wallet SET total_games=? WHERE id=?", (p1tg, 1234))
                        connection.commit()
                        connection.close()

                        time.sleep(3.5)
                        context.bot.send_message(chat_id=group_id,
                                                 text="Score\n\n{}: {}\n{}: {}\n\n{} wins and gets ${}!".format(p1n, nw,
                                                                                                                p2n,
                                                                                                                p2w,
                                                                                                                p1n,
                                                                                                                f"{am:.2f}"),
                                                 reply_to_message_id=update.message.message_id)
                        context.bot.send_message(chat_id="@diceablewins", text="@{} just won ${} in 🎲Dice".format(p1n, f"{am:.2f}"))
                    else:
                        conn.execute(
                            "UPDATE game SET total_turn=?, turn_number=?,player_1_wins=? WHERE game_status='started' AND player_1=? AND player_2=?",
                            (val, p1, nw, p1, p2))
                        conn.commit()
                        conn.close()

                        time.sleep(3.5)
                        context.bot.send_message(chat_id=group_id,
                                                 text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, nw, p2n,
                                                                                                         p2w, p1n),
                                                 reply_to_message_id=message.chat_id)

                elif num == val:
                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=? WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, p1, p2))
                    conn.commit()
                    conn.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, p1w, p2n, p2w,
                                                                                                     p1n),
                                             reply_to_message_id=message.chat_id)

                else:
                    nw = p2w + 1
                    if nw == 3:
                        conn.execute(
                            "UPDATE game SET total_turn=?, turn_number=?,player_2_wins=?,game_status='completed' WHERE game_status='started' AND player_1=? AND player_2=?",
                            (val, p1, nw, p1, p2))
                        conn.commit()
                        conn.close()

                        connection = sqlite3.connect(database_dice)
                        cursor = connection.cursor()

                        cursor.execute(
                            "SELECT balance,wins,total_games,total_earnings,total_wagered FROM wallet WHERE id=?",
                            (1234,))
                        for names in cursor:
                            balance = names[0]
                            nb = am + balance
                            wins = names[1]
                            wins = wins + 1
                            tg = names[2]
                            tg = tg + 1
                            te = names[3]
                            te = te + am
                            tw = names[4]
                            tw = tw + am

                        cursor.execute("SELECT total_games FROM wallet WHERE id=?", (p1,))
                        for names in cursor:
                            p1tg = names[0]
                            p1tg += 1

                        connection.execute(
                            "UPDATE wallet SET balance=?, wins=?, total_games=?, total_earnings=?, total_wagered=? WHERE id=?",
                            (nb, wins, tg, te, tw, 1234))
                        connection.commit()

                        connection.execute("UPDATE wallet SET total_games=? WHERE id=?", (p1tg, p1))
                        connection.commit()
                        connection.close()

                        time.sleep(3.5)
                        context.bot.send_message(chat_id=group_id,
                                                 text="Score\n\n{}: {}\n{}: {}\n\n{} wins and gets ${}!".format(p1n,
                                                                                                                p1w,
                                                                                                                p2n, nw,
                                                                                                                p2n,
                                                                                                                f"{am:.2f}"),
                                                 reply_to_message_id=update.message.message_id)
                        context.bot.send_message(chat_id="@diceablewins", text="@{} just won ${} in 🎲Dice".format(p2n, f"{am:.2f}"))
                    else:
                        conn.execute(
                            "UPDATE game SET total_turn=?, turn_number=?,player_2_wins=? WHERE game_status='started' AND player_1=? AND player_2=?",
                            (val, p1, nw, p1, p2))
                        conn.commit()
                        conn.close()

                        time.sleep(3.5)
                        context.bot.send_message(chat_id=group_id,
                                                 text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, p1w, p2n, nw,
                                                                                                         p1n),
                                                 reply_to_message_id=message.chat_id)

    else:
        cur.execute(
            "SELECT player_1_name,player_1_wins,player_2_name,player_2_wins,total_turn,player_1,player_2,Amount FROM game WHERE turn_number=? AND game_status='started' AND player_2=?",
            (update.effective_user.id, update.effective_user.id))
        jobs = cur.fetchall()

        if len(jobs) != 0:
            for names in jobs:
                p1n = names[0]
                p1w = names[1]
                p2n = names[2]
                p2w = names[3]
                num = names[4]
                p1 = names[5]
                p2 = names[6]
                am = round(names[7] * 1.92, 2)

            if num > val:
                nw = p1w + 1
                if nw ==  3:

                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=?,player_1_wins=?,game_status='completed' WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, nw, p1, p2))
                    conn.commit()
                    conn.close()

                    connection = sqlite3.connect(database_dice)
                    cursor = connection.cursor()

                    cursor.execute(
                        "SELECT balance,wins,total_games,total_earnings,total_wagered FROM wallet WHERE id=?",
                        (p1,))
                    for names in cursor:
                        balance = names[0]
                        nb = am + balance
                        wins = names[1]
                        wins = wins + 1
                        tg = names[2]
                        tg = tg + 1
                        te = names[3]
                        te = te + am
                        tw = names[4]
                        tw = tw + am

                    cursor.execute("SELECT total_games FROM wallet WHERE id=?", (update.effective_user.id,))
                    for names in cursor:
                        p1tg = names[0]
                        p1tg = p1tg + 1

                    connection.execute(
                        "UPDATE wallet SET balance=?, wins=?, total_games=?, total_earnings=?, total_wagered=? WHERE id=?",
                        (nb, wins, tg, te, tw, p1))
                    connection.commit()

                    connection.execute("UPDATE wallet SET total_games=? WHERE id=?", (p1tg, update.effective_user.id))
                    connection.commit()
                    connection.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{} wins and gets ${}!".format(p1n, nw,
                                                                                                            p2n, p2w,
                                                                                                            p1n,
                                                                                                            f"{am:.2f}"),
                                             reply_to_message_id=update.message.message_id)
                else:
                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=?,player_1_wins=? WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, nw, p1, p2))
                    conn.commit()
                    conn.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, nw, p2n, p2w,
                                                                                                     p1n),
                                             reply_to_message_id=update.message.message_id)

            elif num == val:
                conn.execute(
                    "UPDATE game SET total_turn=?, turn_number=? WHERE game_status='started' AND player_1=? AND player_2=?",
                    (val, p1, p1, p2))
                conn.commit()
                conn.close()

                time.sleep(3.5)
                context.bot.send_message(chat_id=group_id,
                                         text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, p1w, p2n, p2w,
                                                                                                 p1n),
                                         reply_to_message_id=update.message.message_id)

            else:
                nw = p2w + 1
                if nw == 3:
                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=?,player_2_wins=?,game_status='completed' WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, nw, p1, p2))
                    conn.commit()
                    conn.close()

                    connection = sqlite3.connect(database_dice)
                    cursor = connection.cursor()

                    cursor.execute(
                        "SELECT balance,wins,total_games,total_earnings,total_wagered FROM wallet WHERE id=?",
                        (update.effective_user.id,))
                    for names in cursor:
                        balance = names[0]
                        nb = am + balance
                        wins = names[1]
                        wins = wins + 1
                        tg = names[2]
                        tg = tg + 1
                        te = names[3]
                        te = te + am
                        tw = names[4]
                        tw = tw + am

                    cursor.execute("SELECT total_games FROM wallet WHERE id=?", (p1,))
                    for names in cursor:
                        p1tg = names[0]
                        p1tg += 1

                    connection.execute(
                        "UPDATE wallet SET balance=?, wins=?, total_games=?, total_earnings=?, total_wagered=? WHERE id=?",
                        (nb, wins, tg, te, tw, update.effective_user.id))
                    connection.commit()

                    connection.execute("UPDATE wallet SET total_games=? WHERE id=?", (p1tg, p1))
                    connection.commit()
                    connection.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{} wins and gets ${}!".format(p1n, p1w,
                                                                                                            p2n, nw,
                                                                                                            p2n,
                                                                                                            f"{am:.2f}"),
                                             reply_to_message_id=update.message.message_id)
                else:
                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=?,player_2_wins=? WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, nw, p1, p2))
                    conn.commit()
                    conn.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, p1w, p2n, nw,
                                                                                                     p1n),
                                             reply_to_message_id=update.message.message_id)

        else:
            conn.close()


def tip(update, context):
    if update.message.chat.type != 'group' and update.message.chat.type != 'supergroup':
        update.message.reply_text("You can only run this command in the Diceable Casino  group")
        return

    if update.message.chat_id != group_id:
        update.message.reply_text("You can only run this command in the Diceable Casino  group")
        return
    try:
        msg = update.message.text
        if "/tip" in msg:
            userg = update.message.from_user
            try:
                usaf = userg.username
            except:
                usaf = userg.first_name
            ac = update.message.chat.id
            if ac == group_id:
                try:
                    msg_parts = msg.split("/tip")
                    if len(msg_parts) != 2:
                        raise ValueError("Invalid command format")

                    try:
                        am = float(msg_parts[1].strip())
                    except ValueError:
                        print("Invalid amount! Please enter a valid number.")
                        return

                    if am <= 0:
                        print("Tip amount must be greater than zero.")
                        return

                    MAX_TIP_AMOUNT = 1000.0
                    if am > MAX_TIP_AMOUNT:
                        print(f"Tip amount exceeds maximum limit of ${MAX_TIP_AMOUNT}.")
                        return

                    fromid = update.message.reply_to_message.from_user.id
                    if update.effective_user.id == fromid:
                        print("You cannot tip yourself!")
                        return

                    fromname = update.message.reply_to_message.from_user.first_name

                    connection = sqlite3.connect(database_dice)
                    cursor = connection.cursor()

                    cursor.execute("SELECT balance FROM wallet WHERE id=?", (update.effective_user.id,))
                    balance_data = cursor.fetchone()
                    if not balance_data:
                        print("No wallet found for the user.")
                        return

                    balance = balance_data[0]

                    if balance >= am:
                        new_balance = balance - am

                        cursor.execute("SELECT balance FROM wallet WHERE id=?", (fromid,))
                        receiver_balance_data = cursor.fetchone()

                        if receiver_balance_data:
                            new_receiver_balance = receiver_balance_data[0] + am
                        else:
                            new_receiver_balance = am
                            cursor.execute(
                                "INSERT INTO wallet (ID, balance, code, amount, name, wins, total_games, total_earnings, total_wagered) \
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (fromid, 0.0, "0", 0.0, fromname, 0, 0, 0.0, 0.0)
                            )

                        cursor.execute("UPDATE wallet SET balance=? WHERE id=?", (new_balance, update.effective_user.id))
                        cursor.execute("UPDATE wallet SET balance=? WHERE id=?", (new_receiver_balance, fromid))

                        connection.commit()
                        connection.close()

                        context.bot.send_message(chat_id=group_id,
                                                 text="🎁 Tip successful! {} receives ${}".format(fromname, f"{am:.2f}"),
                                                 reply_to_message_id=update.message.message_id)
                    else:
                        print("Insufficient balance.")
                        return

                except Exception as e:
                    print(f"An error occurred: {str(e)}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
def dice(update, context):
    global bot_active
    if not bot_active:
        return

    if update.message.chat_id != group_id:
        return

    userg = update.message.from_user
    if userg.username:
        usaf = userg.username
    elif userg.first_name and userg.last_name:
        usaf = f"{userg.first_name} {userg.last_name}" 
    elif userg.first_name:
        usaf = userg.first_name 
    else:
        usaf = f"User {userg.id}" 

    connection = sqlite3.connect(database_dice)
    cursor = connection.cursor()

    cursor.execute("SELECT id FROM wallet WHERE id = ?", (update.effective_user.id,))
    jobs = cursor.fetchall()
    if len(jobs) == 0:
        cursor.execute("INSERT INTO wallet (ID, balance, code, amount, name, wins, total_games, total_earnings, total_wagered) \
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (update.effective_user.id, 0.0, "0", 0.0, usaf, 0, 0, 0.0, 0.0))
        connection.commit()

    cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
    result = cursor.fetchone()
    if not result:
        balance = 0
    else:
        balance = result[0]

    try:
        msg = update.message.text
        am = msg.split("/dice")

        if am[1].strip().lower() == "all":
            am = min(balance, 25)
        else:
            am = float(am[1])

        if am < 0.5:
            context.bot.send_message(chat_id=group_id, text="Minimum bet is $0.5", reply_to_message_id=update.message.message_id)
            return
        if am > 25:
            context.bot.send_message(chat_id=group_id, text="Maximum bet is $25", reply_to_message_id=update.message.message_id)
            return

        if balance >= am:
            conn = sqlite3.connect(database_dicegame)
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM game WHERE (player_1 = ? OR player_2 = ?) AND game_status = ?",
                           (update.effective_user.id, update.effective_user.id, "pending"))
            jobs = cursor.fetchall()

            if len(jobs) == 0:
                conn.execute("INSERT INTO game (game_id, player_1, player_2, total_turn, turn_number, game_status, winner, Amount, player_1_name, player_2_name, player_1_wins, player_2_wins) \
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                update.message.message_id, update.effective_user.id, 0, 0, update.effective_user.id, "pending", 0, am,
                usaf, '0', 0, 0))
                conn.commit()
                conn.close()

                keyboard = [[InlineKeyboardButton("✅ Confirm",
                                                  callback_data="confirm-{}-{}".format(update.message.message_id, am)),
                             InlineKeyboardButton("❌ Cancel",
                                                  callback_data="cancel-{}".format(update.message.message_id))]]
                reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

                context.bot.send_message(chat_id=group_id,
                                         text="Game Confirmation\n\nYour bet: ${}\nWin chance: 50/50\nWin multiplier: 1.92x".format(
                                             f"{am:.2f}"), reply_to_message_id=update.message.message_id,
                                         reply_markup=reply_markup)
            else:
                conn.close()
                context.bot.send_message(chat_id=group_id, text="Please finish your previous game to start a new game.")
        else:
            connection.close()
            context.bot.send_message(chat_id=group_id, text="Not enough balance", reply_to_message_id=update.message.message_id)
    except Exception as e:
        print(f"Error With Dice: {e}", flush=True)
        connection.close()
        context.bot.send_message(chat_id=group_id, text="Usage: /dice <betamount>", reply_to_message_id=update.message.message_id)

def wth(update, context):
    global bot_active
    if not bot_active:
        return
    if update.message.chat.type == 'private':
        msg = update.message.text
        msg = msg.split("-")

        try:
            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()
            am = float(msg[1])
            ad = msg[0]
            if is_valid_erc20_address(ad):

                if am > 4:
                    cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
                    for names in cursor:
                        balance = names[0]
                    if balance > am:
                        nb = balance - am

                        try:
                            am = am * 0.99
                            url = 'https://api.oxapay.com/exchange/calculate'
                            data = {
                                'amount': am,
                                'fromCurrency': "USDT",
                                'toCurrency': 'LTC'
                            }
                            response = requests.post(url, data=json.dumps(data))
                            result = response.json()
                            toam = result['toAmount']
                            toam = float(toam)
                            url = 'https://api.oxapay.com/api/send'
                            data = {
                                'key': payout_key,
                                'address': ad,
                                'amount': toam,
                                'currency': 'LTC'
                            }
                            response = requests.post(url, data=json.dumps(data))
                            result = response.json()
                            msg = result['message']
                            if "Successful" in msg:
                                keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
                                reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                    one_time_keyboard=True)
                                connection.execute("UPDATE wallet SET balance = ? WHERE ID = ?",
                                                   (nb, int(update.effective_user.id)))
                                connection.commit()
                                connection.close()
                                context.bot.send_message(chat_id=update.effective_user.id,
                                                         text="Your Withdrawl is sucessfull\n\nPlease feel free to leave a review here -> @DiceableVouches".format(balance),
                                                         reply_markup=reply_markup)
                                return ConversationHandler.END
                            else:
                                connection.close()
                                keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
                                reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True,
                                                                    one_time_keyboard=True)
                                context.bot.send_message(chat_id=update.effective_user.id,
                                                         text="Your Withdrawl is unsucessfull\n\nPlease try again later..".format(
                                                             balance), reply_markup=reply_markup)
                                return ConversationHandler.END

                        except:
                            connection.close()
                            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
                            reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                            context.bot.send_message(chat_id=update.effective_user.id,
                                                     text="Your Withdrawl is unsucessfull\n\nPlease try again later".format(
                                                         balance), reply_markup=reply_markup)
                            return ConversationHandler.END
                    else:
                        connection.close()
                        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
                        reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                        context.bot.send_message(chat_id=update.effective_user.id,
                                                 text="Not enough balance your balance is ${}".format(balance),
                                                 reply_markup=reply_markup)
                        return WTH

                else:
                    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
                    reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                    context.bot.send_message(chat_id=update.effective_user.id,
                                             text="Minimum withdrawl is 5 USDT please send amount more than 5",
                                             reply_markup=reply_markup)
                    return WTH
            else:
                keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                context.bot.send_message(chat_id=update.effective_user.id, text="Invalid LTC Address ",
                                         reply_markup=reply_markup)
                return WTH

        except:

            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="200")]]
            reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            context.bot.send_message(chat_id=update.effective_user.id, text="Invalid format!",
                                     reply_markup=reply_markup)
            return WTH


import logging

def send_message(context: CallbackContext):
    global bot_active
    if not bot_active:
        return
    
    logger = logging.getLogger(__name__)
    
    try:
        connection = sqlite3.connect(database_dice)
        cursor = connection.cursor()
        cursor.execute("SELECT code, id FROM wallet")
        wallets = cursor.fetchall()
        
        logger.info(f"Checking deposits for {len(wallets)} wallets.")
        
        for wallet in wallets:
            deposit_address, user_id = wallet
            if deposit_address != "0":
                try:
                    url = 'https://api.oxapay.com/merchants/list'
                    data = {
                        'merchant': merchant_key,
                        'address': deposit_address,
                    }
                    response = requests.post(url, data=json.dumps(data), timeout=10)
                    response.raise_for_status()
                    result = response.json()
                    
                    transactions = result.get('data', [])
                    if transactions:
                        transaction = transactions[0] 
                        amount_received = transaction.get("payAmount")
                        currency = transaction.get('payCurrency')
                        
                        if amount_received is None or currency is None:
                            logger.warning(f"Transaction data incomplete for user {user_id}. Skipping.")
                            continue
                        
                        try:
                            amount_received = float(amount_received)
                        except ValueError:
                            logger.warning(f"Invalid payAmount format for user {user_id}: {amount_received}. Skipping.")
                            continue
                        
                        # Convert to USDT if necessary
                        if currency != "USDT":
                            conversion_url = 'https://api.oxapay.com/exchange/calculate'
                            conversion_data = {
                                'amount': amount_received,
                                'fromCurrency': currency,
                                'toCurrency': 'USDT'
                            }
                            conversion_response = requests.post(conversion_url, data=json.dumps(conversion_data), timeout=10)
                            conversion_response.raise_for_status()
                            conversion_result = conversion_response.json()
                            
                            toam = conversion_result.get('toAmount')
                            if toam is None:
                                logger.warning(f"Conversion failed for user {user_id}. 'toAmount' not found.")
                                continue
                            
                            try:
                                toam = float(toam)
                            except ValueError:
                                logger.warning(f"Invalid toAmount format for user {user_id}: {toam}. Skipping.")
                                continue
                        else:
                            toam = amount_received
                        
                        cursor.execute("SELECT balance FROM wallet WHERE id = ?", (user_id,))
                        balance_data = cursor.fetchone()
                        if balance_data:
                            current_balance = float(balance_data[0])
                            new_balance = current_balance + toam
                            
                            cursor.execute("UPDATE wallet SET balance = ?, code = '0' WHERE id = ?", (new_balance, user_id))
                            connection.commit()
                            
                            logger.info(f"Updated balance for user {user_id}: +${toam:.2f} (Total: ${new_balance:.2f})")
                            
                            try:
                                context.bot.send_message(
                                    chat_id=user_id,
                                    text=f"✅ *Deposit Confirmed!*\n\nYou've deposited `${toam:.2f}` and your new balance is `${new_balance:.2f}`.",
                                    parse_mode=ParseMode.MARKDOWN
                                )
                                logger.info(f"Sent deposit confirmation to user {user_id}.")
                            except Exception as e:
                                logger.error(f"Failed to send message to user {user_id}: {e}")
                        else:
                            logger.warning(f"No balance record found for user {user_id}.")
                    
                    else:
                        logger.debug(f"No transactions found for address {deposit_address}.")
                
                except requests.exceptions.RequestException as req_err:
                    logger.error(f"API request error for user {user_id} at address {deposit_address}: {req_err}")
                except KeyError as key_err:
                    logger.error(f"Key error processing deposit for user {user_id}: {key_err}")
                except Exception as e:
                    logger.error(f"Unexpected error processing deposit for user {user_id}: {e}")
        
        connection.close()
        logger.info("Completed deposit checks.")
    
    except sqlite3.Error as db_err:
        logger.error(f"Database error: {db_err}")
    except Exception as e:
        logger.error(f"Unexpected error in send_message: {e}")


game_in_progress = False
def start_blackjack(update: Update, context: CallbackContext):
    """Start a Blackjack game."""
    global game_in_progress
    global bot_active
    if not bot_active:
        return
    if game_in_progress:
        update.message.reply_text("⚠️ A Blackjack game is already in progress. Please wait for it to finish.")
        return

    if len(context.args) != 1:
        update.message.reply_text("Usage: /blackjack <bet_amount>")
        return

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name

    connection = sqlite3.connect(database_dice)
    cursor = connection.cursor()
    cursor.execute("SELECT balance FROM wallet WHERE id = ?", (user_id,))
    result = cursor.fetchone()

    if not result:
        update.message.reply_text("You do not have an account or sufficient balance to play.")
        return

    balance = result[0] 
    connection.close()

    try:

        if context.args[0].lower() == "all":
            bet_amount = min(balance, 25)
        else:
            bet_amount = float(context.args[0]) 

        if bet_amount < 1:
            update.message.reply_text("The minimum bet is $1.")
            return
        if bet_amount > 25:
            update.message.reply_text("The maximum bet is $25.")
            return
        if bet_amount > balance:
            update.message.reply_text("It seems your balance isn't enough for this bet.")
            return

    except ValueError:
        update.message.reply_text("Bet amount must be a number or 'all'.")
        return

    if update.message.chat.type != 'group' and update.message.chat.type != 'supergroup':
        update.message.reply_text("Blackjack can only be played in the designated group.")
        return

    if update.message.chat_id != group_id:
        update.message.reply_text("You can only play Blackjack in the authorized group.")
        return

    game_state, error = start_blackjack_game(bet_amount, user_id, database_dice)
    if error:
        update.message.reply_text(error)
        return

    context.user_data['blackjack_game'] = game_state
    context.user_data['game_player'] = user_id
    game_in_progress = True
    dealer_hand_message = format_hand_with_suits(game_state['dealer_hand'], reveal_dealer=False)
    player_total = calculate_hand_total(game_state['player_hand'])
    dealer_total = calculate_hand_total(game_state['dealer_hand'])

    player_hand_message = format_player_hand(user_name, game_state['player_hand'], player_total)

    dealer_message = update.message.reply_text(
        f"The game starts now. 🎲\n\nDealer's cards:\n\n{dealer_hand_message}"
    )
    time.sleep(0.5)

    context.user_data['dealer_message_id'] = dealer_message.message_id


    if player_total == 21 and dealer_total == 21:
        time.sleep(1)
        update.message.reply_text(f"{player_hand_message}\n\nBoth you and the dealer have Blackjack! It's a tie (push). Bet will be refunded.")
        payout(bet_amount, user_id, database_dice, player_won=False,draw=True)
        reveal_dealer_cards(update, context) 
        game_in_progress = False
        return

    if player_total == 21:
        time.sleep(1)
        update.message.reply_text(f"{player_hand_message}\n\nYou got Blackjack! You win ${game_state['bet_amount'] * multiplier_blackjack}! 🎉")
        payout(bet_amount, user_id, database_dice, player_won=True)
        reveal_dealer_cards(update, context)
        game_in_progress = False
        return


    player_message = update.message.reply_text(
        f"{player_hand_message}\n\nDo you want to hit or stand?",
        reply_markup=generate_hit_stand_buttons()
    )


    context.user_data['player_message_id'] = player_message.message_id


import time

def hit(update: Update, context: CallbackContext):
    global game_in_progress
    """Handle when the player hits."""
    user_data = context.user_data
    user_id = update.callback_query.from_user.id

    if user_id != user_data.get('game_player'):
        update.callback_query.answer("You are not playing this game!", show_alert=True)
        return

    if user_data['blackjack_game'].get('game_over', False):
        update.callback_query.answer("The game is over.", show_alert=True)
        return

    current_time = time.time()
    last_action_time = user_data.get('last_action_time', 0)
    time_since_last_action = current_time - last_action_time
    MIN_ACTION_INTERVAL = 0.5 

    if time_since_last_action < MIN_ACTION_INTERVAL:
        update.callback_query.answer("⏳ Please wait a moment before your next action.")
        return

    if user_data.get('processing', False):
        update.callback_query.answer("Please wait, processing your previous move.")
        return

    disable_buttons(update.callback_query.message.chat_id, user_data['player_message_id'], context)

    user_data['processing'] = True
    user_data['last_action_time'] = current_time 

    try:
        player_hand = user_data['blackjack_game']['player_hand']

        new_card = draw_card()
        player_hand.append(new_card)
        user_data['blackjack_game']['player_hand'] = player_hand

        player_total = calculate_hand_total(player_hand)

        if player_total > 21:
            context.bot.edit_message_text(
                chat_id=update.callback_query.message.chat_id,
                message_id=user_data['player_message_id'],
                text=f"You busted with a total of {player_total}! 😢\n\n{format_player_hand(update.effective_user.first_name, player_hand, player_total)}",
            )
            reveal_dealer_cards(update, context)
            payout(user_data['blackjack_game']['bet_amount'], user_id, database_dice, player_won=False)
            game_in_progress = False
            user_data['blackjack_game']['game_over'] = True

            return

        if player_total == 21:
            dealer_total = calculate_hand_total(user_data['blackjack_game']['dealer_hand'])
            handle_dealer_turn(user_data, update.callback_query, player_total, dealer_total, context)
            return

        context.bot.edit_message_text(
            chat_id=update.callback_query.message.chat_id,
            message_id=user_data['player_message_id'],
            text=f"{format_player_hand(update.effective_user.first_name, player_hand, player_total)}\n\nDo you want to hit or stand?",
            reply_markup=generate_hit_stand_buttons()
        )

    except Exception as e:
        logging.exception("Error in hit function:")
        update.callback_query.answer("An error occurred. Please try again.")
    finally:
        user_data['processing'] = False

def reveal_dealer_cards(update: Update, context: CallbackContext):
    """Reveals the dealer's full hand at the end of the game."""

    user_data = context.user_data
    dealer_hand = user_data['blackjack_game']['dealer_hand']

    dealer_hand_reveal_message = format_hand_with_suits(dealer_hand, reveal_dealer=True)

    if update.message:
        chat_id = update.message.chat_id
    else:
        chat_id = update.callback_query.message.chat_id

    context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=user_data['dealer_message_id'],
        text=f"The game starts now. 🎲\n\nDealer's cards:\n\n{dealer_hand_reveal_message}"
    )

def handle_dealer_turn(game_state, query, player_total, dealer_total, context):
    """Handles the dealer's turn after the player stands or reaches 21."""
    global game_in_progress

    dealer_hand_message = format_hand_with_suits(game_state['blackjack_game']['dealer_hand'], reveal_dealer=True)
    query.edit_message_text(f"Dealer's hand:\n{dealer_hand_message}")

    while dealer_total < 17:
        game_state['blackjack_game']['dealer_hand'].append(draw_card())
        dealer_total = calculate_hand_total(game_state['blackjack_game']['dealer_hand'])

    if dealer_total > 21:
        result_text = f"Congratulations! The dealer busted with {dealer_total}. You win ${multiplier_blackjack * game_state['blackjack_game']['bet_amount']}!"
        payout(game_state['blackjack_game']['bet_amount'], game_state['game_player'], database_dice, player_won=True)
    elif dealer_total > player_total:
        result_text = f"Sorry, you lost ${game_state['blackjack_game']['bet_amount']}. The dealer wins with {dealer_total} against your {player_total}."
        payout(game_state['blackjack_game']['bet_amount'], game_state['game_player'], database_dice, player_won=False)
    elif dealer_total == player_total:
        result_text = f"It's a draw! Both you and the dealer have {player_total}."
        payout(game_state['blackjack_game']['bet_amount'], game_state['game_player'], database_dice, player_won=False, draw=True)
    else:
        result_text = f"Congratulations! You win ${multiplier_blackjack * game_state['blackjack_game']['bet_amount']} with a total of {player_total} against the dealer's {dealer_total}!"
        payout(game_state['blackjack_game']['bet_amount'], game_state['game_player'], database_dice, player_won=True)

    game_state['blackjack_game']['game_over'] = True
    game_in_progress = False

    query.edit_message_text(result_text)

    user_data = context.user_data
    context.bot.edit_message_reply_markup(
        chat_id=query.message.chat_id,
        message_id=user_data['player_message_id'],
        reply_markup=None 
    )



def generate_hit_stand_buttons():
    """Generate hit/stand buttons."""
    keyboard = [
        [InlineKeyboardButton("Hit", callback_data="hit")],
        [InlineKeyboardButton("Stand", callback_data="stand")]
    ]
    return InlineKeyboardMarkup(keyboard)

def reset_blackjack_game(update: Update, context: CallbackContext):
    """Reset the Blackjack game if the user is an admin."""
    global game_in_progress

    chat_id = update.message.chat_id
    user_id = update.effective_user.id

    chat_member = context.bot.get_chat_member(chat_id, user_id)

    if chat_member.status not in [ChatMember.ADMINISTRATOR, ChatMember.CREATOR]:
        update.message.reply_text("Only admins can reset the game.")
        return

    game_in_progress = False

    update.message.reply_text("The Blackjack game has been reset. A new game can now be started.")
def stand(update: Update, context: CallbackContext):
    """Handle when the player stands."""
    user_data = context.user_data
    user_id = update.callback_query.from_user.id

    if user_id != user_data.get('game_player'):
        update.callback_query.answer("You are not playing this game!", show_alert=True)
        return

    if user_data['blackjack_game'].get('game_over', False):
        update.callback_query.answer("The game is over.", show_alert=True)
        return

    current_time = time.time()
    last_action_time = user_data.get('last_action_time', 0)
    time_since_last_action = current_time - last_action_time
    MIN_ACTION_INTERVAL = 0.5 

    if time_since_last_action < MIN_ACTION_INTERVAL:
        update.callback_query.answer("⏳ Please wait a moment before your next action.")
        return

    if user_data.get('processing', False):
        update.callback_query.answer("Please wait, processing your previous move.")
        return

    disable_buttons(update.callback_query.message.chat_id, user_data['player_message_id'], context)

    user_data['processing'] = True
    user_data['last_action_time'] = current_time

    try:
        player_hand = user_data['blackjack_game']['player_hand']
        dealer_hand = user_data['blackjack_game']['dealer_hand']

        player_total = calculate_hand_total(player_hand)
        dealer_total = calculate_hand_total(dealer_hand)
        handle_dealer_turn(user_data, update.callback_query, player_total, dealer_total, context)
        reveal_dealer_cards(update, context) 

    except Exception as e:
        logging.exception("Error in stand function:")
    finally:
        user_data['processing'] = False


def help_command(update: Update, context: CallbackContext) -> None:
    global bot_active
    if not bot_active:
        return

    help_text = (
        "📖 **Instructions**\n\n"
        "📥 **Depositing Funds:**\n"
        "To deposit money, type `/depo` and follow the prompts.\n\n"
        "📤 **Withdrawing Funds:**\n"
        "To withdraw money, type `/withdraw` and follow the prompts.\n\n"
        "🎲 **Playing Dice**\n"
        "Type `/dice` along with your bet amount. For example: `/dice 5`.\n\n"
        "💣 **Playing Mines**\n"
        "Type `/mines` with the amount you’d like to bet and the number of mines. Ex. `/mines 1 4`\n\n"
        "♣️ **Playing Blackjack**\n"
        "Type `/bj` followed by your wager amount. Ex. `/bj 1`\n\n"
        "🛠 **Need Help?**\n"
        "For assistance, reach out to **@Justifyable**."
    )

    user = update.message.from_user
    user_id = user.id

    try:
        context.bot.send_message(chat_id=user_id, text=help_text, parse_mode='Markdown')

        confirmation_text = f"{user.first_name}, I've sent you the help instructions in your DMs! 📩"
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=confirmation_text,
                                 reply_to_message_id=update.message.message_id)

    except Exception as e:
        logging.error(f"Error sending DM to user {user_id}: {e}")

        error_text = (
            f"{user.first_name}, I couldn't send you a DM. "
            f"Please make sure you've started a conversation with me. Click [here](tg://resolve?domain={context.bot.username}) to start."
        )
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=error_text,
                                 parse_mode='Markdown',
                                 disable_web_page_preview=True,
                                 reply_to_message_id=update.message.message_id)
def withdraw_command(update, context):
    """Handles the /withdraw command."""
    global bot_active
    if not bot_active:
        return

    bot_username = context.bot.username

    if update.message.chat.type in ['group', 'supergroup']:
        keyboard = [
            [InlineKeyboardButton("💸 Withdraw", url=f"https://t.me/{bot_username}?start=withdraw")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(
            chat_id=update.message.chat_id,
            text="To withdraw funds, please click the button below and follow the instructions in the bot's DM.",
            reply_markup=reply_markup
        )
    else:
        connection = sqlite3.connect(database_dice)
        cursor = connection.cursor()
        cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
        result = cursor.fetchone()
        if result:
            ba = result[0]
            balance = f"{ba:.2f}"
        else:
            ba = 0.0
            balance = "0.00"
        connection.close()

        keyboard = [[InlineKeyboardButton("◀️ Back", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

        if ba > 4.5:
            context.bot.send_message(
                chat_id=update.effective_user.id,
                text=(
                    "💸 **Withdraw LTC**\n\n"
                    "**Important:**\n"
                    "- Minimum withdrawal: $5\n"
                    "- Network fee: 1%\n\n"
                    "Please provide your LTC wallet address and the amount you'd like to withdraw in LTC.\n\n"
                    "**Example:**\n"
                    "`ltcaddy-12`"
                ),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return WTH
        else:
            context.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"The minimum withdrawal is $5, but your balance is only ${balance}",
                reply_markup=reply_markup
            )



def deposit_command(update, context):
    """Handles the /depo command."""
    global bot_active
    if not bot_active:
        return

    bot_username = context.bot.username

    if update.message.chat.type in ['group', 'supergroup']:
        keyboard = [
            [InlineKeyboardButton("💳 Deposit", url=f"https://t.me/{bot_username}?start=deposit")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(
            chat_id=update.message.chat_id,
            text="To deposit funds, please click the button below and follow the instructions in the bot's DM.",
            reply_markup=reply_markup
        )
    else:
        keyboard = [
            [InlineKeyboardButton("Ethereum", callback_data="ETH")],
            [InlineKeyboardButton("Litecoin", callback_data="LTC"), InlineKeyboardButton("Tron TRC20", callback_data="TRX")],
            [InlineKeyboardButton("USDT BEP20", callback_data="USDT"), InlineKeyboardButton("BNB BEP20", callback_data="BNB")],
            [InlineKeyboardButton("USDC ERC20", callback_data="USDC")],
            [InlineKeyboardButton("Toncoin", callback_data="TON"), InlineKeyboardButton("Back", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

        context.bot.send_message(
            chat_id=update.effective_user.id,
            text="Please choose the coin you'd like to deposit.",
            reply_markup=reply_markup
        )

def disable_buttons(chat_id, message_id, context):
    """Disable buttons by removing the reply markup."""
    try:
        context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
    except Exception as e:
        logging.exception("Error disabling buttons:")

database_dice = os.getenv('DATABASE_DICE')
if not database_dice:
    raise ValueError("DATABASE_DICE is missing from the environment variables.")

conn = sqlite3.connect(database_dice, check_same_thread=False)
c = conn.cursor()
c.execute('''
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
''')
c.execute('''
    CREATE TABLE IF NOT EXISTS rain_participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rain_id TEXT,
        user_id INTEGER,
        username TEXT,
        FOREIGN KEY (rain_id) REFERENCES rains (rain_id)
    )
''')
conn.commit()

def is_user_admin(bot, update):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        logging.error(f"Error checking admin status: {e}")
        return False
import uuid
from datetime import datetime, timedelta

def is_user_admin(bot, update):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['administrator', 'creator']
    except Exception as e:
        logging.error(f"Error checking admin status: {e}")
        return False




def rain(update, context):
    user_id = update.effective_user.id

    if user_id != admin_id:
        update.message.reply_text("❌ You are not authorized to use this command.")
        return

    args = context.args
    if len(args) != 3:
        update.message.reply_text("Usage: /rain <amount> <minimum_wagered> <duration_in_minutes>")
        return

    try:
        amount = float(args[0])
        min_wagered = float(args[1])
        duration_minutes = int(args[2])

        if amount <= 0 or min_wagered < 0 or duration_minutes <= 0:
            raise ValueError
    except (ValueError, TypeError):
        update.message.reply_text("⚠️ Please provide valid numbers for amount, minimum wagered, and duration.")
        return

    rain_id = str(uuid.uuid4())
    chat_id = update.message.chat.id
    start_time = datetime.utcnow()
    end_time = start_time + timedelta(minutes=duration_minutes)

    admin_user = update.message.from_user
    host_username = admin_user.username or admin_user.first_name or 'Host'

    rain_data = {
        'rain_id': rain_id,
        'admin_id': admin_id,
        'amount': amount,
        'min_wagered': min_wagered,
        'start_time': start_time.isoformat(),
        'end_time': end_time.isoformat(),
        'chat_id': chat_id,
        'message_id': None,
        'host_username': host_username,
    }

    with conn:
        c.execute('''
            INSERT INTO rains (rain_id, admin_id, amount, min_wagered, start_time, end_time, chat_id, host_username)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            rain_id,
            admin_id,
            amount,
            min_wagered,
            rain_data['start_time'],
            rain_data['end_time'],
            chat_id,
            host_username,
        ))
        conn.commit()

    rain_message = generate_rain_message(rain_id)
    button = InlineKeyboardMarkup([
        [InlineKeyboardButton(text="🌧 Participate in Rain!", callback_data=f'participate_rain_{rain_id}')]
    ])
    sent_message = context.bot.send_message(
        chat_id=chat_id,
        text=rain_message,
        reply_markup=button,
        parse_mode=ParseMode.MARKDOWN
    )
    rain_data['message_id'] = sent_message.message_id

    with conn:
        c.execute('''
            UPDATE rains SET message_id = ? WHERE rain_id = ?
        ''', (sent_message.message_id, rain_id))
        conn.commit()

    context.job_queue.run_repeating(
        update_rain_message,
        interval=60,  
        first=60,
        context={'rain_id': rain_id},
        name=f"update_rain_{rain_id}"
    )
    context.job_queue.run_once(
        end_rain,
        when=(end_time - start_time).total_seconds(),
        context={'rain_id': rain_id},
        name=f"end_rain_{rain_id}"
    )

def generate_rain_message(rain_id):
    with conn:
        c.execute('SELECT * FROM rains WHERE rain_id = ?', (rain_id,))
        rain = c.fetchone()

    if not rain:
        return "❌ Rain event not found."

    rain_dict = {
        'rain_id': rain[0],
        'admin_id': rain[1],
        'amount': rain[2],
        'min_wagered': rain[3],
        'start_time': rain[4],
        'end_time': rain[5],
        'chat_id': rain[6],
        'message_id': rain[7],
        'host_username': rain[8],
    }

    with conn:
        c.execute('SELECT COUNT(*) FROM rain_participants WHERE rain_id = ?', (rain_id,))
        participant_count = c.fetchone()[0]

    now = datetime.utcnow()
    end_time = datetime.fromisoformat(rain_dict['end_time'])
    time_left = end_time - now
    total_seconds = int(time_left.total_seconds())
    if total_seconds <= 0:
        time_left_str = "0s"
    else:
        minutes_left, seconds_left = divmod(total_seconds, 60)
        time_left_str = f"{minutes_left}m {seconds_left}s" if minutes_left > 0 else f"{seconds_left}s"

    host_username = rain_dict.get('host_username', 'Host')

    rain_message = (
        f"💰 *Rain Event Started!*\n\n"
        f"💸 *Amount:* ${rain_dict['amount']}\n"
        f"👤 *Hosted By:* @{host_username}\n"
        f"🔒 *Minimum Wagered Required:* ${rain_dict['min_wagered']}\n"
        f"⏰ *Ends In:* {time_left_str}\n"
        f"👥 *Participants:* {participant_count}\n\n"
        "Click the button below to participate!"
    )
    return rain_message

def update_rain_message(context: CallbackContext):
    job = context.job
    rain_id = job.context['rain_id']
    with conn:
        c.execute('SELECT * FROM rains WHERE rain_id = ?', (rain_id,))
        rain_row = c.fetchone()

    if not rain_row:
        jobs = context.job_queue.get_jobs_by_name(job.name)
        for j in jobs:
            j.schedule_removal()
        return

    rain = {
        'rain_id': rain_row[0],
        'admin_id': rain_row[1],
        'amount': rain_row[2],
        'min_wagered': rain_row[3],
        'start_time': rain_row[4],
        'end_time': rain_row[5],
        'chat_id': rain_row[6],
        'message_id': rain_row[7],
        'host_username': rain_row[8],
    }

    rain_message = generate_rain_message(rain_id)
    button = InlineKeyboardMarkup([
        [InlineKeyboardButton(text="🌧 Participate in Rain!", callback_data=f'participate_rain_{rain_id}')]
    ])

    try:
        context.bot.edit_message_text(
            chat_id=rain['chat_id'],
            message_id=rain['message_id'],
            text=rain_message,
            reply_markup=button,
            parse_mode=ParseMode.MARKDOWN
        )
    except BadRequest as e:
        logging.error(f"Error updating rain message: {e}")


def participate_rain_callback(update, context):
    query = update.callback_query
    user = query.from_user
    rain_id = query.data[len('participate_rain_'):]

    with conn:
        c.execute('SELECT * FROM rains WHERE rain_id = ?', (rain_id,))
        rain_row = c.fetchone()

    if not rain_row:
        query.answer("❌ This rain does not exist or has ended.", show_alert=True)
        return

    rain = {
        'rain_id': rain_row[0],
        'admin_id': rain_row[1],
        'amount': rain_row[2],
        'min_wagered': rain_row[3],
        'start_time': rain_row[4],
        'end_time': rain_row[5],
        'chat_id': rain_row[6],
        'message_id': rain_row[7],
        'host_username': rain_row[8],
    }

    now = datetime.utcnow()
    end_time = datetime.fromisoformat(rain['end_time'])
    if now >= end_time:
        query.answer("❌ This rain has already ended.", show_alert=True)
        return

    with conn:
        c.execute('SELECT total_wagered FROM wallet WHERE ID = ?', (user.id,))
        result = c.fetchone()
        if result:
            total_wagered = result[0]
        else:
            total_wagered = 0.0 

    if total_wagered < rain['min_wagered']:
        query.answer(
            f"⚠️ You need to have wagered at least ${rain['min_wagered']} to participate.",
            show_alert=True
        )
        return

    with conn:
        c.execute('SELECT 1 FROM rain_participants WHERE rain_id = ? AND user_id = ?', (rain_id, user.id))
        exists = c.fetchone()

    if exists:
        query.answer("⚠️ You have already joined this rain.", show_alert=True)
        return

    if user.first_name and '@diceablecasino' not in user.first_name.lower():
        query.answer("⚠️ First name must contain '@DiceableCasino'.", show_alert=True)
        return

    with conn:
        c.execute('''
            INSERT INTO rain_participants (rain_id, user_id, username)
            VALUES (?, ?, ?)
        ''', (rain_id, user.id, user.username))
        conn.commit()

    query.answer("✅ You've successfully joined the rain!")
    update_rain_message(context)


def end_rain(context: CallbackContext):
    job = context.job
    rain_id = job.context['rain_id']
    with conn:
        c.execute('SELECT * FROM rains WHERE rain_id = ?', (rain_id,))
        rain_row = c.fetchone()

    if not rain_row:
        return 

    rain = {
        'rain_id': rain_row[0],
        'admin_id': rain_row[1],
        'amount': rain_row[2],
        'min_wagered': rain_row[3],
        'start_time': rain_row[4],
        'end_time': rain_row[5],
        'chat_id': rain_row[6],
        'message_id': rain_row[7],
        'host_username': rain_row[8],
    }

    with conn:
        c.execute('SELECT user_id, username FROM rain_participants WHERE rain_id = ?', (rain_id,))
        participants = c.fetchall()

    if not participants:
        context.bot.send_message(
            chat_id=rain['chat_id'],
            text=f"❌ No one participated in the rain with ID `{rain_id}`.",
            parse_mode=ParseMode.MARKDOWN
        )
        with conn:
            c.execute('DELETE FROM rains WHERE rain_id = ?', (rain_id,))
            conn.commit()
        return

    share = rain['amount'] / len(participants)
    share = round(share, 2)
    participant_mentions = []

    with conn:
        for user_id, username in participants:
            c.execute('SELECT balance FROM wallet WHERE ID = ?', (user_id,))
            result = c.fetchone()
            if result:
                balance = result[0]
                new_balance = balance + share
                c.execute('UPDATE wallet SET balance = ? WHERE ID = ?', (new_balance, user_id))
                participant_mentions.append(
                    f"[{username or 'User'}](tg://user?id={user_id})"
                )
                logging.info(f"✅ Updated balance for user {user_id}")
            else:
                c.execute('''
                    INSERT INTO wallet (ID, name, balance, total_wagered, total_earnings, wins, total_games)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, username, share, 0.0, 0.0, 0, 0))
                participant_mentions.append(
                    f"[{username or 'User'}](tg://user?id={user_id})"
                )
                logging.info(f"✅ Created new wallet and updated balance for user {user_id}")
        conn.commit()

    if participant_mentions:
        participant_text = ', '.join(participant_mentions)
        end_message = (
            f"🌈 *Rain Ended!*\n\n"
            f"💸 *Total Amount:* ${rain['amount']}\n"
            f"👥 *Participants:* {len(participants)}\n"
            f"💰 *Amount per Participant:* ${share}\n\n"
            f"Balances have been updated for: {participant_text}"
        )
        context.bot.send_message(
            chat_id=rain['chat_id'],
            text=end_message,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        context.bot.send_message(
            chat_id=rain['chat_id'],
            text="❌ Failed to update balances for participants."
        )

    with conn:
        c.execute('DELETE FROM rain_participants WHERE rain_id = ?', (rain_id,))
        c.execute('DELETE FROM rains WHERE rain_id = ?', (rain_id,))
        conn.commit()

    jobs = context.job_queue.get_jobs_by_name(f"update_rain_{rain_id}")
    for j in jobs:
        j.schedule_removal()
    jobs = context.job_queue.get_jobs_by_name(f"end_rain_{rain_id}")
    for j in jobs:
        j.schedule_removal()

def listrains(update, context):
    with conn:
        c.execute('SELECT * FROM rains')
        rains = c.fetchall()

    if not rains:
        update.message.reply_text("❌ There are no active rains at the moment.")
        return

    message_text = "🌧 *Active Rains:*\n\n"
    for rain_row in rains:
        rain_id = rain_row[0]
        rain = {
            'rain_id': rain_row[0],
            'admin_id': rain_row[1],
            'amount': rain_row[2],
            'min_wagered': rain_row[3],
            'start_time': rain_row[4],
            'end_time': rain_row[5],
            'chat_id': rain_row[6],
            'message_id': rain_row[7],
            'host_username': rain_row[8],
        }
        now = datetime.utcnow()
        end_time = datetime.fromisoformat(rain['end_time'])
        time_left = end_time - now
        total_seconds = int(time_left.total_seconds())
        if total_seconds <= 0:
            time_left_str = "0s"
        else:
            minutes_left, seconds_left = divmod(total_seconds, 60)
            time_left_str = f"{minutes_left}m {seconds_left}s" if minutes_left > 0 else f"{seconds_left}s"

        message_text += (
            f"- *Rain ID:* `{rain_id}`\n"
            f"  *Amount:* ${rain['amount']}\n"
            f"  *Minimum Wagered:* ${rain['min_wagered']}\n"
            f"  *Ends In:* {time_left_str}\n\n"
        )
    update.message.reply_text(message_text, parse_mode=ParseMode.MARKDOWN)

def rain_error_handler(update, context):
    logging.error(f"❌ An error occurred: {context.error}")
def set_user_balance(user_id, new_balance):
    """Sets the balance of a user in the database."""
    try:
        connection = sqlite3.connect(database_dice)
        cursor = connection.cursor()
        cursor.execute("UPDATE wallet SET balance = ? WHERE ID = ?", (new_balance, user_id))
        
        # Check if any rows were updated (i.e., the user was found)
        if cursor.rowcount == 0:
            return f"No user found with ID {user_id}."
        else:
            connection.commit()
            return f"Balance for user ID {user_id} updated to {new_balance}."
    except sqlite3.Error as e:
        return f"An error occurred: {e}"
    finally:
        connection.close()

def setbal_command(update: Update, context: CallbackContext):
    """Handles the /setbal command."""
    user_id = update.effective_user.id

    
    if user_id != admin_id:
        update.message.reply_text("You don't have permission to use this command.")
        return

    
    if update.message.reply_to_message:
        try:
            
            target_user_id = update.message.reply_to_message.from_user.id

            
            if context.args:
                new_balance = float(context.args[0])

                
                result_message = set_user_balance(target_user_id, new_balance)
                update.message.reply_text(result_message)
            else:
                update.message.reply_text("Please provide an amount, like /setbal <amount>.")
        except ValueError:
            update.message.reply_text("Invalid amount. Please provide a valid numeric value.")
    else:
        update.message.reply_text("Please reply to a user's message with /setbal <amount>.")
def showbal_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if user_id != admin_id:
        update.message.reply_text("You don't have permission to use this command.")
        return

    if update.message.reply_to_message:
        try:
            target_user = update.message.reply_to_message.from_user
            target_user_id = target_user.id
            target_username = target_user.username

            connection = sqlite3.connect(database_dice)
            cursor = connection.cursor()
            cursor.execute("SELECT balance FROM wallet WHERE ID = ?", (target_user_id,))
            result = cursor.fetchone()

            if result:
                balance = result[0]
                if target_username:
                    update.message.reply_text(f"@{target_username} Balance is: ${balance}")
                else:
                    update.message.reply_text(f"User with ID {target_user_id} has no username. Balance: ${balance}")
            else:
                update.message.reply_text(f"No user found with ID {target_user_id}.")
            
            connection.close()
        except sqlite3.Error as e:
            update.message.reply_text(f"An error occurred: {e}")
    else:
        update.message.reply_text("Please reply to a user's message with /showbal.")
def add_stats(update: Update, context: CallbackContext):
    if update.effective_user.id != admin_id:
        update.message.reply_text("You don't have permission to use this command.")
        return
    
    if len(context.args) != 2:
        update.message.reply_text("Usage: /addstats <userid> <total_won>")
        return

    try:
        userid = int(context.args[0])
        total_won = float(context.args[1])

        connection = sqlite3.connect("dice.db")
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE wallet
            SET total_earnings = ?
            WHERE ID = ?
        """, (total_won, userid))
        
        connection.commit()
        connection.close()
        
        update.message.reply_text("Total earnings set successfully.")
        
    except (ValueError, IndexError):
        update.message.reply_text("Invalid input. Ensure correct format and data types.")
    except Exception as e:
        update.message.reply_text(f"Error: {e}")
def dr(update: Update, context: CallbackContext) -> None:
    if bot_active:
        start_dice_roulette(update, context)
    else:
        return
def set_bot_balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id != admin_id:
        return
    
    try:
        amount = float(context.args[0])
    except (IndexError, ValueError):
        update.message.reply_text("Usage: /setbotbal <amount>")
        return

    conn = sqlite3.connect('dice.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE wallet SET balance = ? WHERE ID = 1234", (amount,))
    conn.commit()
    conn.close()
def senddb(update, context):
    if update.effective_user.id == admin_id and update.effective_chat.type == 'private':
        try:
            file_path = 'dice.db'
            last_modified_time = os.path.getmtime(file_path)
            last_modified_date = datetime.utcfromtimestamp(last_modified_time).strftime('%Y-%m-%d %H:%M:%S')
            caption = f"Last updated: {last_modified_date}"
            context.bot.send_document(chat_id=update.effective_chat.id, document=open(file_path, 'rb'), caption=caption)
        except FileNotFoundError:
            update.message.reply_text("Database file not found.")
    else:
        return

def dh(update: Update, context: CallbackContext) -> None:
    if bot_active:
        start_dh(update, context)
    else:
        return

def handle_dh_choice_command(update, context):
    global bot_active
    if not bot_active:
        update.callback_query.answer("The bot is currently inactive. Please try again later.")
        return
    handle_dh_choice(update, context)

def reset_hilo_command(update, context):
    reset_hilo(update, context)

def trio(update: Update, context: CallbackContext) -> None:
    if bot_active:
        start_trio_game(update, context)
    else:
        return
def drain_command(update: Update, context: CallbackContext):
    user_id = update.effective_user.id

    if user_id != admin_id:
        update.message.reply_text("You don't have permission to use this command.")
        return

    if update.message.reply_to_message:
        target_user_id = update.message.reply_to_message.from_user.id
        result_message = set_user_balance(target_user_id, 0)
        update.message.reply_text(f"User's balance has been drained to 0.\n{result_message}")
    else:
        update.message.reply_text("Please reply to a user's message with /drain to set their balance to 0.")

def deleterain(update, context):
    user_id = update.effective_user.id

    if user_id != admin_id:
        update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not context.args:
        update.message.reply_text("Usage: /deleterain <rainid>")
        return

    rain_id = context.args[0]

    try:
        with conn:
            c = conn.cursor()
            c.execute('SELECT * FROM rains WHERE rain_id = ?', (rain_id,))
            rain = c.fetchone()

            if not rain:
                update.message.reply_text(f"❌ No rain found with ID: {rain_id}")
                return

            c.execute('DELETE FROM rains WHERE rain_id = ?', (rain_id,))
            conn.commit()

        update.message.reply_text(f"✅ Rain with ID {rain_id} has been deleted.")
    except Exception as e:
        update.message.reply_text(f"❌ An error occurred while deleting the rain: {str(e)}")
def resetdice(update, context):
    user_id = update.effective_user.id

    if user_id != admin_id:
        update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if not context.args:
        update.message.reply_text("Usage: /resetdice <userid>")
        return

    target_user_id = int(context.args[0])

    try:
        conn = sqlite3.connect(database_dicegame)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM game WHERE (player_1 = ? OR player_2 = ?) AND game_status = ?", 
                       (target_user_id, target_user_id, "pending"))
        active_game = cursor.fetchone()

        if not active_game:
            update.message.reply_text(f"❌ No active game found for user {target_user_id}.")
            conn.close()
            return

        cursor.execute("DELETE FROM game WHERE (player_1 = ? OR player_2 = ?) AND game_status = ?", 
                       (target_user_id, target_user_id, "pending"))
        conn.commit()
        conn.close()

        update.message.reply_text(f"✅ The dice game for user {target_user_id} has been reset and deleted.")
    except Exception as e:
        update.message.reply_text(f"❌ An error occurred: {str(e)}")


def bowl(update, context):
    global bot_active
    if not bot_active:
        return

    if update.message.chat_id != group_id:
        return

    userg = update.message.from_user
    if userg.username:
        usaf = userg.username
    elif userg.first_name and userg.last_name:
        usaf = f"{userg.first_name} {userg.last_name}"
    elif userg.first_name:
        usaf = userg.first_name
    else:
        usaf = f"User {userg.id}"

    connection = sqlite3.connect(database_dice)
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM wallet WHERE id = ?", (update.effective_user.id,))
    jobs = cursor.fetchall()
    if len(jobs) == 0:
        cursor.execute("INSERT INTO wallet (ID, balance, code, amount, name, wins, total_games, total_earnings, total_wagered) \
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (update.effective_user.id, 0.0, "0", 0.0, usaf, 0, 0, 0.0, 0.0))
        connection.commit()

    cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
    result = cursor.fetchone()
    if not result:
        balance = 0
    else:
        balance = result[0]

    try:
        msg = update.message.text
        am = msg.split("/bowl")

        if am[1].strip().lower() == "all":
            am = min(balance, 25)  # Bet the entire balance but cap at $25
        else:
            am = float(am[1])

        if am < 0.5:
            context.bot.send_message(chat_id=group_id, text="Minimum bet is $0.5",
                                     reply_to_message_id=update.message.message_id)
            return
        if am > 25:  # Maximum bet of $25
            context.bot.send_message(chat_id=group_id, text="Maximum bet is $25",
                                     reply_to_message_id=update.message.message_id)
            return

        if balance >= am:
            conn = sqlite3.connect(database_bowlgame)
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM game WHERE (player_1 = ? OR player_2 = ?) AND game_status = ?",
                           (update.effective_user.id, update.effective_user.id, "pending"))
            jobs = cursor.fetchall()

            if len(jobs) == 0:
                conn.execute("INSERT INTO game (game_id, player_1, player_2, total_turn, turn_number, game_status, winner, Amount, player_1_name, player_2_name, player_1_wins, player_2_wins) \
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                update.message.message_id, update.effective_user.id, 0, 0, update.effective_user.id, "pending", 0, am,
                usaf, '0', 0, 0))
                conn.commit()
                conn.close()

                keyboard = [[InlineKeyboardButton("✅ Confirm",
                                                  callback_data="bowlconfirm-{}-{}".format(update.message.message_id, am)),
                             InlineKeyboardButton("❌ Cancel",
                                                  callback_data="bowlcancel-{}".format(update.message.message_id))]]
                reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

                context.bot.send_message(chat_id=group_id,
                                         text="Game Confirmation\n\nYour bet: ${}\nWin chance: 50/50\nWin multiplier: 1.92x".format(
                                             f"{am:.2f}"), reply_to_message_id=update.message.message_id,
                                         reply_markup=reply_markup)
            else:
                conn.close()
                context.bot.send_message(chat_id=group_id, text="Please finish your previous game to start a new game.")
        else:
            connection.close()
            context.bot.send_message(chat_id=group_id, text="Not enough balance",
                                     reply_to_message_id=update.message.message_id)
    except Exception as e:
        print(f"Error With Bowl: {e}",flush=True)
        connection.close()
        context.bot.send_message(chat_id=group_id, text="Usage: /bowl  <betamount>",
                                 reply_to_message_id=update.message.message_id)

def bowl_handler(update, context):
    global bot_active
    if not bot_active:
        return

    if update.message.chat_id != group_id:
        return

    message = update.message

    if message.forward_from or message.forward_from_chat:
        return

    if message.sticker:
        return

    if not message.dice:
        return

    if message.dice.emoji != '🎳':
        return
    val = update.message.dice.value
    conn = sqlite3.connect(database_bowlgame)
    cur = conn.cursor()

    cur.execute("SELECT player_2,player_2_name FROM game WHERE turn_number=? AND game_status='started' AND player_1=?",
                (update.effective_user.id, update.effective_user.id))
    jobs = cur.fetchall()

    if len(jobs) != 0:
        for names in jobs:
            p2 = names[0]
            p2n = names[1]

        conn.execute(
            "UPDATE game SET total_turn=?, turn_number=? WHERE game_status='started' AND player_1=? AND player_2=?",
            (val, p2, update.effective_user.id, p2))
        conn.commit()
        conn.close()
        context.bot.send_message(chat_id=group_id, text="{}, your turn!".format(p2n),
                                 reply_to_message_id=update.message.message_id)

        if p2n == "bot":
            message = bot_player.send_dice(chat_id=update.effective_chat.id, emoji="🎳") 
            val = message.dice.value
            conn = sqlite3.connect(database_bowlgame)
            cur = conn.cursor()

            cur.execute(
                "SELECT player_1_name,player_1_wins,player_2_name,player_2_wins,total_turn,player_1,player_2,Amount FROM game WHERE turn_number=? AND game_status='started' AND player_2=?",
                (1234, 1234))
            jobs = cur.fetchall()

            if len(jobs) != 0:
                for names in jobs:
                    p1n = names[0]
                    p1w = names[1]
                    p2n = names[2]
                    p2w = names[3]
                    num = names[4]
                    p1 = names[5]
                    p2 = names[6]
                    am = round(names[7] * 1.92, 2)

                if num > val:
                    nw = p1w + 1
                    if nw == 3:
                        conn.execute(
                            "UPDATE game SET total_turn=?, turn_number=?,player_1_wins=?,game_status='completed' WHERE game_status='started' AND player_1=? AND player_2=?",
                            (val, p1, nw, p1, p2))
                        conn.commit()
                        conn.close()

                        connection = sqlite3.connect(database_dice)
                        cursor = connection.cursor()

                        cursor.execute(
                            "SELECT balance,wins,total_games,total_earnings,total_wagered FROM wallet WHERE id=?",
                            (p1,))
                        for names in cursor:
                            balance = names[0]
                            nb = am + balance
                            wins = names[1]
                            wins = wins + 1
                            tg = names[2]
                            tg = tg + 1
                            te = names[3]
                            te = te + am
                            tw = names[4]
                            tw = tw + am

                        cursor.execute("SELECT total_games FROM wallet WHERE id=?", (1234,))
                        for names in cursor:
                            p1tg = names[0]
                            p1tg = p1tg + 1

                        connection.execute(
                            "UPDATE wallet SET balance=?, wins=?, total_games=?, total_earnings=?, total_wagered=? WHERE id=?",
                            (nb, wins, tg, te, tw, p1))
                        connection.commit()

                        connection.execute("UPDATE wallet SET total_games=? WHERE id=?", (p1tg, 1234))
                        connection.commit()
                        connection.close()

                        time.sleep(3.5)
                        context.bot.send_message(chat_id=group_id,
                                                 text="Score\n\n{}: {}\n{}: {}\n\n{} wins and gets ${}!".format(p1n, nw,
                                                                                                                p2n,
                                                                                                                p2w,
                                                                                                                p1n,
                                                                                                                f"{am:.2f}"),
                                                 reply_to_message_id=update.message.message_id)
                    else:
                        conn.execute(
                            "UPDATE game SET total_turn=?, turn_number=?,player_1_wins=? WHERE game_status='started' AND player_1=? AND player_2=?",
                            (val, p1, nw, p1, p2))
                        conn.commit()
                        conn.close()

                        time.sleep(3.5)
                        context.bot.send_message(chat_id=group_id,
                                                 text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, nw, p2n,
                                                                                                         p2w, p1n),
                                                 reply_to_message_id=message.chat_id)

                elif num == val:
                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=? WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, p1, p2))
                    conn.commit()
                    conn.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, p1w, p2n, p2w,
                                                                                                     p1n),
                                             reply_to_message_id=message.chat_id)

                else:
                    nw = p2w + 1
                    if nw == 3:
                        conn.execute(
                            "UPDATE game SET total_turn=?, turn_number=?,player_2_wins=?,game_status='completed' WHERE game_status='started' AND player_1=? AND player_2=?",
                            (val, p1, nw, p1, p2))
                        conn.commit()
                        conn.close()

                        connection = sqlite3.connect(database_dice)
                        cursor = connection.cursor()

                        cursor.execute(
                            "SELECT balance,wins,total_games,total_earnings,total_wagered FROM wallet WHERE id=?",
                            (1234,))
                        for names in cursor:
                            balance = names[0]
                            nb = am + balance
                            wins = names[1]
                            wins = wins + 1
                            tg = names[2]
                            tg = tg + 1
                            te = names[3]
                            te = te + am
                            tw = names[4]
                            tw = tw + am

                        cursor.execute("SELECT total_games FROM wallet WHERE id=?", (p1,))
                        for names in cursor:
                            p1tg = names[0]
                            p1tg = p1tg + 1

                        connection.execute(
                            "UPDATE wallet SET balance=?, wins=?, total_games=?, total_earnings=?, total_wagered=? WHERE id=?",
                            (nb, wins, tg, te, tw, 1234))
                        connection.commit()

                        connection.execute("UPDATE wallet SET total_games=? WHERE id=?", (p1tg, p1))
                        connection.commit()
                        connection.close()

                        time.sleep(3.5)
                        context.bot.send_message(chat_id=group_id,
                                                 text="Score\n\n{}: {}\n{}: {}\n\n{} wins and gets ${}!".format(p1n,
                                                                                                                p1w,
                                                                                                                p2n, nw,
                                                                                                                p2n,
                                                                                                                f"{am:.2f}"),
                                                 reply_to_message_id=update.message.message_id)
                    else:
                        conn.execute(
                            "UPDATE game SET total_turn=?, turn_number=?,player_2_wins=? WHERE game_status='started' AND player_1=? AND player_2=?",
                            (val, p1, nw, p1, p2))
                        conn.commit()
                        conn.close()

                        time.sleep(3.5)
                        context.bot.send_message(chat_id=group_id,
                                                 text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, p1w, p2n,
                                                                                                         nw, p1n),
                                                 reply_to_message_id=message.chat_id)

    else:
        cur.execute(
            "SELECT player_1_name,player_1_wins,player_2_name,player_2_wins,total_turn,player_1,player_2,Amount FROM game WHERE turn_number=? AND game_status='started' AND player_2=?",
            (update.effective_user.id, update.effective_user.id))
        jobs = cur.fetchall()

        if len(jobs) != 0:
            for names in jobs:
                p1n = names[0]
                p1w = names[1]
                p2n = names[2]
                p2w = names[3]
                num = names[4]
                p1 = names[5]
                p2 = names[6]
                print(names[7])
                am = round(names[7] * 1.92, 2)

            if num > val:
                nw = p1w + 1
                if nw == 3:
                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=?,player_1_wins=?,game_status='completed' WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, nw, p1, p2))
                    conn.commit()
                    conn.close()

                    connection = sqlite3.connect(database_dice)
                    cursor = connection.cursor()

                    cursor.execute(
                        "SELECT balance,wins,total_games,total_earnings,total_wagered FROM wallet WHERE id=?",
                        (p1,))
                    for names in cursor:
                        balance = names[0]
                        nb = am + balance
                        wins = names[1]
                        wins = wins + 1
                        tg = names[2]
                        tg = tg + 1
                        te = names[3]
                        te = te + am
                        tw = names[4]
                        tw = tw + am

                    cursor.execute("SELECT total_games FROM wallet WHERE id=?", (update.effective_user.id,))
                    for names in cursor:
                        p1tg = names[0]
                        p1tg = p1tg + 1

                    connection.execute(
                        "UPDATE wallet SET balance=?, wins=?, total_games=?, total_earnings=?, total_wagered=? WHERE id=?",
                        (nb, wins, tg, te, tw, p1))
                    connection.commit()

                    connection.execute("UPDATE wallet SET total_games=? WHERE id=?", (p1tg, update.effective_user.id))
                    connection.commit()
                    connection.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{} wins and gets ${}!".format(p1n, nw,
                                                                                                            p2n, p2w,
                                                                                                            p1n,
                                                                                                            f"{am:.2f}"),
                                             reply_to_message_id=update.message.message_id)
                else:
                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=?,player_1_wins=? WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, nw, p1, p2))
                    conn.commit()
                    conn.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, nw, p2n, p2w,
                                                                                                     p1n),
                                             reply_to_message_id=update.message.message_id)

            elif num == val:
                conn.execute(
                    "UPDATE game SET total_turn=?, turn_number=? WHERE game_status='started' AND player_1=? AND player_2=?",
                    (val, p1, p1, p2))
                conn.commit()
                conn.close()

                time.sleep(3.5)
                context.bot.send_message(chat_id=group_id,
                                         text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, p1w, p2n, p2w,
                                                                                                 p1n),
                                         reply_to_message_id=update.message.message_id)

            else:
                nw = p2w + 1
                if nw == 3:
                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=?,player_2_wins=?,game_status='completed' WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, nw, p1, p2))
                    conn.commit()
                    conn.close()

                    connection = sqlite3.connect(database_dice)
                    cursor = connection.cursor()

                    cursor.execute(
                        "SELECT balance,wins,total_games,total_earnings,total_wagered FROM wallet WHERE id=?",
                        (update.effective_user.id,))
                    for names in cursor:
                        balance = names[0]
                        nb = am + balance
                        wins = names[1]
                        wins = wins + 1
                        tg = names[2]
                        tg = tg + 1
                        te = names[3]
                        te = te + am
                        tw = names[4]
                        tw = tw + am

                    cursor.execute("SELECT total_games FROM wallet WHERE id=?", (p1,))
                    for names in cursor:
                        p1tg = names[0]
                        p1tg += 1

                    connection.execute(
                        "UPDATE wallet SET balance=?, wins=?, total_games=?, total_earnings=?, total_wagered=? WHERE id=?",
                        (nb, wins, tg, te, tw, update.effective_user.id))
                    connection.commit()

                    connection.execute("UPDATE wallet SET total_games=? WHERE id=?", (p1tg, p1))
                    connection.commit()
                    connection.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{} wins and gets ${}!".format(p1n, p1w,
                                                                                                            p2n, nw,
                                                                                                            p2n,
                                                                                                            f"{am:.2f}"),
                                             reply_to_message_id=update.message.message_id)
                else:
                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=?,player_2_wins=? WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, nw, p1, p2))
                    conn.commit()
                    conn.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, p1w, p2n, nw,
                                                                                                     p1n),
                                             reply_to_message_id=update.message.message_id)

        else:
            conn.close()


def dart(update, context):
    global bot_active
    if not bot_active:
        return

    if update.message.chat_id != group_id:
        return

    userg = update.message.from_user
    if userg.username:
        usaf = userg.username
    elif userg.first_name and userg.last_name:
        usaf = f"{userg.first_name} {userg.last_name}"
    elif userg.first_name:
        usaf = userg.first_name
    else:
        usaf = f"User {userg.id}"

    connection = sqlite3.connect(database_dice)
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM wallet WHERE id = ?", (update.effective_user.id,))
    jobs = cursor.fetchall()
    if len(jobs) == 0:
        cursor.execute("INSERT INTO wallet (ID, balance, code, amount, name, wins, total_games, total_earnings, total_wagered) \
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (update.effective_user.id, 0.0, "0", 0.0, usaf, 0, 0, 0.0, 0.0))
        connection.commit()

    cursor.execute("SELECT balance FROM wallet WHERE id = ?", (update.effective_user.id,))
    result = cursor.fetchone()
    if not result:
        balance = 0
    else:
        balance = result[0]

    try:
        msg = update.message.text
        am = msg.split("/dart")

        if am[1].strip().lower() == "all":
            am = min(balance, 25)  # Bet the entire balance but cap at $25
        else:
            am = float(am[1])

        if am < 0.5:
            context.bot.send_message(chat_id=group_id, text="Minimum bet is $0.5",
                                     reply_to_message_id=update.message.message_id)
            return
        if am > 25:  # Maximum bet of $25
            context.bot.send_message(chat_id=group_id, text="Maximum bet is $25",
                                     reply_to_message_id=update.message.message_id)
            return

        if balance >= am:
            conn = sqlite3.connect(database_dartgame)
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM game WHERE (player_1 = ? OR player_2 = ?) AND game_status = ?",
                           (update.effective_user.id, update.effective_user.id, "pending"))
            jobs = cursor.fetchall()

            if len(jobs) == 0:
                conn.execute("INSERT INTO game (game_id, player_1, player_2, total_turn, turn_number, game_status, winner, Amount, player_1_name, player_2_name, player_1_wins, player_2_wins) \
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                update.message.message_id, update.effective_user.id, 0, 0, update.effective_user.id, "pending", 0, am,
                usaf, '0', 0, 0))
                conn.commit()
                conn.close()

                keyboard = [[InlineKeyboardButton("✅ Confirm",
                                                  callback_data="dartconfirm-{}-{}".format(update.message.message_id, am)),
                             InlineKeyboardButton("❌ Cancel",
                                                  callback_data="dartcancel-{}".format(update.message.message_id))]]
                reply_markup = InlineKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

                context.bot.send_message(chat_id=group_id,
                                         text="Game Confirmation\n\nYour bet: ${}\nWin chance: 50/50\nWin multiplier: 1.92x".format(
                                             f"{am:.2f}"), reply_to_message_id=update.message.message_id,
                                         reply_markup=reply_markup)
            else:
                conn.close()
                context.bot.send_message(chat_id=group_id, text="Please finish your previous game to start a new game.")
        else:
            connection.close()
            context.bot.send_message(chat_id=group_id, text="Not enough balance",
                                     reply_to_message_id=update.message.message_id)
    except Exception as e:
        print(f"Error With Dart: {e}",flush=True)
        connection.close()
        context.bot.send_message(chat_id=group_id, text="Usage: /dart <betamount>",
reply_to_message_id=update.message.message_id)                                

def dart_handler(update, context):
    global bot_active
    if not bot_active:
        return

    if update.message.chat_id != group_id:
        return

    message = update.message

    if message.forward_from or message.forward_from_chat:
        return

    if message.sticker:
        return

    if not message.dice:
        return

    if message.dice.emoji != '🎯':
        return
    val = update.message.dice.value
    conn = sqlite3.connect(database_dartgame)
    cur = conn.cursor()

    cur.execute("SELECT player_2,player_2_name FROM game WHERE turn_number=? AND game_status='started' AND player_1=?",
                (update.effective_user.id, update.effective_user.id))
    jobs = cur.fetchall()

    if len(jobs) != 0:
        for names in jobs:
            p2 = names[0]
            p2n = names[1]

        conn.execute(
            "UPDATE game SET total_turn=?, turn_number=? WHERE game_status='started' AND player_1=? AND player_2=?",
            (val, p2, update.effective_user.id, p2))
        conn.commit()
        conn.close()
        context.bot.send_message(chat_id=group_id, text="{}, your turn!".format(p2n),
                                 reply_to_message_id=update.message.message_id)

        if p2n == "bot":
            message = bot_player.send_dice(chat_id=update.effective_chat.id, emoji="🎯")
            val = message.dice.value
            conn = sqlite3.connect(database_dartgame)
            cur = conn.cursor()

            cur.execute(
                "SELECT player_1_name,player_1_wins,player_2_name,player_2_wins,total_turn,player_1,player_2,Amount FROM game WHERE turn_number=? AND game_status='started' AND player_2=?",
                (1234, 1234))
            jobs = cur.fetchall()

            if len(jobs) != 0:
                for names in jobs:
                    p1n = names[0]
                    p1w = names[1]
                    p2n = names[2]
                    p2w = names[3]
                    num = names[4]
                    p1 = names[5]
                    p2 = names[6]
                    am = round(names[7] * 1.92, 2)

                if num > val:
                    nw = p1w + 1
                    if nw == 3:
                        conn.execute(
                            "UPDATE game SET total_turn=?, turn_number=?,player_1_wins=?,game_status='completed' WHERE game_status='started' AND player_1=? AND player_2=?",
                            (val, p1, nw, p1, p2))
                        conn.commit()
                        conn.close()

                        connection = sqlite3.connect(database_dice)
                        cursor = connection.cursor()

                        cursor.execute(
                            "SELECT balance,wins,total_games,total_earnings,total_wagered FROM wallet WHERE id=?",
                            (p1,))
                        for names in cursor:
                            balance = names[0]
                            nb = am + balance
                            wins = names[1]
                            wins = wins + 1
                            tg = names[2]
                            tg = tg + 1
                            te = names[3]
                            te = te + am
                            tw = names[4]
                            tw = tw + am

                        cursor.execute("SELECT total_games FROM wallet WHERE id=?", (1234,))
                        for names in cursor:
                            p1tg = names[0]
                            p1tg = p1tg + 1

                        connection.execute(
                            "UPDATE wallet SET balance=?, wins=?, total_games=?, total_earnings=?, total_wagered=? WHERE id=?",
                            (nb, wins, tg, te, tw, p1))
                        connection.commit()

                        connection.execute("UPDATE wallet SET total_games=? WHERE id=?", (p1tg, 1234))
                        connection.commit()
                        connection.close()

                        time.sleep(3.5)
                        context.bot.send_message(chat_id=group_id,
                                                 text="Score\n\n{}: {}\n{}: {}\n\n{} wins and gets ${}!".format(p1n, nw,
                                                                                                                p2n,
                                                                                                                p2w,
                                                                                                                p1n,
                                                                                                                f"{am:.2f}"),
                                                 reply_to_message_id=update.message.message_id)
                    else:
                        conn.execute(
                            "UPDATE game SET total_turn=?, turn_number=?,player_1_wins=? WHERE game_status='started' AND player_1=? AND player_2=?",
                            (val, p1, nw, p1, p2))
                        conn.commit()
                        conn.close()

                        time.sleep(3.5)
                        context.bot.send_message(chat_id=group_id,
                                                 text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, nw, p2n,
                                                                                                         p2w, p1n),
                                                 reply_to_message_id=message.chat_id)

                elif num == val:
                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=? WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, p1, p2))
                    conn.commit()
                    conn.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, p1w, p2n, p2w,
                                                                                                     p1n),
                                             reply_to_message_id=message.chat_id)

                else:
                    nw = p2w + 1
                    if nw == 3:
                        conn.execute(
                            "UPDATE game SET total_turn=?, turn_number=?,player_2_wins=?,game_status='completed' WHERE game_status='started' AND player_1=? AND player_2=?",
                            (val, p1, nw, p1, p2))
                        conn.commit()
                        conn.close()

                        connection = sqlite3.connect(database_dice)
                        cursor = connection.cursor()

                        cursor.execute(
                            "SELECT balance,wins,total_games,total_earnings,total_wagered FROM wallet WHERE id=?",
                            (1234,))
                        for names in cursor:
                            balance = names[0]
                            nb = am + balance
                            wins = names[1]
                            wins = wins + 1
                            tg = names[2]
                            tg = tg + 1
                            te = names[3]
                            te = te + am
                            tw = names[4]
                            tw = tw + am

                        cursor.execute("SELECT total_games FROM wallet WHERE id=?", (p1,))
                        for names in cursor:
                            p1tg = names[0]
                            p1tg = p1tg + 1

                        connection.execute(
                            "UPDATE wallet SET balance=?, wins=?, total_games=?, total_earnings=?, total_wagered=? WHERE id=?",
                            (nb, wins, tg, te, tw, 1234))
                        connection.commit()

                        connection.execute("UPDATE wallet SET total_games=? WHERE id=?", (p1tg, p1))
                        connection.commit()
                        connection.close()

                        time.sleep(3.5)
                        context.bot.send_message(chat_id=group_id,
                                                 text="Score\n\n{}: {}\n{}: {}\n\n{} wins and gets ${}!".format(p1n,
                                                                                                                p1w,
                                                                                                                p2n, nw,
                                                                                                                p2n,
                                                                                                                f"{am:.2f}"),
                                                 reply_to_message_id=update.message.message_id)
                    else:
                        conn.execute(
                            "UPDATE game SET total_turn=?, turn_number=?,player_2_wins=? WHERE game_status='started' AND player_1=? AND player_2=?",
                            (val, p1, nw, p1, p2))
                        conn.commit()
                        conn.close()

                        time.sleep(3.5)
                        context.bot.send_message(chat_id=group_id,
                                                 text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, p1w, p2n,
                                                                                                         nw, p1n),
                                                 reply_to_message_id=message.chat_id)

    else:
        cur.execute(
            "SELECT player_1_name,player_1_wins,player_2_name,player_2_wins,total_turn,player_1,player_2,Amount FROM game WHERE turn_number=? AND game_status='started' AND player_2=?",
            (update.effective_user.id, update.effective_user.id))
        jobs = cur.fetchall()

        if len(jobs) != 0:
            for names in jobs:
                p1n = names[0]
                p1w = names[1]
                p2n = names[2]
                p2w = names[3]
                num = names[4]
                p1 = names[5]
                p2 = names[6]
                print(names[7])
                am = round(names[7] * 1.92, 2)

            if num > val:
                nw = p1w + 1
                if nw == 3:
                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=?,player_1_wins=?,game_status='completed' WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, nw, p1, p2))
                    conn.commit()
                    conn.close()

                    connection = sqlite3.connect(database_dice)
                    cursor = connection.cursor()

                    cursor.execute(
                        "SELECT balance,wins,total_games,total_earnings,total_wagered FROM wallet WHERE id=?",
                        (p1,))
                    for names in cursor:
                        balance = names[0]
                        nb = am + balance
                        wins = names[1]
                        wins = wins + 1
                        tg = names[2]
                        tg = tg + 1
                        te = names[3]
                        te = te + am
                        tw = names[4]
                        tw = tw + am

                    cursor.execute("SELECT total_games FROM wallet WHERE id=?", (update.effective_user.id,))
                    for names in cursor:
                        p1tg = names[0]
                        p1tg = p1tg + 1

                    connection.execute(
                        "UPDATE wallet SET balance=?, wins=?, total_games=?, total_earnings=?, total_wagered=? WHERE id=?",
                        (nb, wins, tg, te, tw, p1))
                    connection.commit()

                    connection.execute("UPDATE wallet SET total_games=? WHERE id=?", (p1tg, update.effective_user.id))
                    connection.commit()
                    connection.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{} wins and gets ${}!".format(p1n, nw,
                                                                                                            p2n, p2w,
                                                                                                            p1n,
                                                                                                            f"{am:.2f}"),
                                             reply_to_message_id=update.message.message_id)
                else:
                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=?,player_1_wins=? WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, nw, p1, p2))
                    conn.commit()
                    conn.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, nw, p2n, p2w,
                                                                                                     p1n),
                                             reply_to_message_id=update.message.message_id)

            elif num == val:
                conn.execute(
                    "UPDATE game SET total_turn=?, turn_number=? WHERE game_status='started' AND player_1=? AND player_2=?",
                    (val, p1, p1, p2))
                conn.commit()
                conn.close()

                time.sleep(3.5)
                context.bot.send_message(chat_id=group_id,
                                         text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, p1w, p2n, p2w,
                                                                                                 p1n),
                                         reply_to_message_id=update.message.message_id)

            else:
                nw = p2w + 1
                if nw == 3:
                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=?,player_2_wins=?,game_status='completed' WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, nw, p1, p2))
                    conn.commit()
                    conn.close()

                    connection = sqlite3.connect(database_dice)
                    cursor = connection.cursor()

                    cursor.execute(
                        "SELECT balance,wins,total_games,total_earnings,total_wagered FROM wallet WHERE id=?",
                        (update.effective_user.id,))
                    for names in cursor:
                        balance = names[0]
                        nb = am + balance
                        wins = names[1]
                        wins = wins + 1
                        tg = names[2]
                        tg = tg + 1
                        te = names[3]
                        te = te + am
                        tw = names[4]
                        tw = tw + am

                    cursor.execute("SELECT total_games FROM wallet WHERE id=?", (p1,))
                    for names in cursor:
                        p1tg = names[0]
                        p1tg += 1

                    connection.execute(
                        "UPDATE wallet SET balance=?, wins=?, total_games=?, total_earnings=?, total_wagered=? WHERE id=?",
                        (nb, wins, tg, te, tw, update.effective_user.id))
                    connection.commit()

                    connection.execute("UPDATE wallet SET total_games=? WHERE id=?", (p1tg, p1))
                    connection.commit()
                    connection.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{} wins and gets ${}!".format(p1n, p1w,
                                                                                                            p2n, nw,
                                                                                                            p2n,
                                                                                                            f"{am:.2f}"),
                                             reply_to_message_id=update.message.message_id)
                else:
                    conn.execute(
                        "UPDATE game SET total_turn=?, turn_number=?,player_2_wins=? WHERE game_status='started' AND player_1=? AND player_2=?",
                        (val, p1, nw, p1, p2))
                    conn.commit()
                    conn.close()

                    time.sleep(3.5)
                    context.bot.send_message(chat_id=group_id,
                                             text="Score\n\n{}: {}\n{}: {}\n\n{}, your turn!".format(p1n, p1w, p2n, nw,
                                                                                                     p1n),
                                             reply_to_message_id=update.message.message_id)

        else:
            conn.close()

codes_conn = sqlite3.connect("codes.db", check_same_thread=False)
codes_cursor = codes_conn.cursor()

dice_conn = sqlite3.connect("dice.db", check_same_thread=False)
dice_cursor = dice_conn.cursor()

codes_cursor.execute('''
    CREATE TABLE IF NOT EXISTS codes (
        code TEXT PRIMARY KEY,
        min_wager REAL NOT NULL,
        usages_left INTEGER NOT NULL,
        is_diceable_required BOOLEAN NOT NULL,
        amount REAL NOT NULL
    )
''')

codes_cursor.execute('''
    CREATE TABLE IF NOT EXISTS claimed_codes (
        user_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        PRIMARY KEY (user_id, code)
    )
''')

codes_conn.commit()

def create_code(update, context):
  
    if update.message.from_user.id != admin_id:
        update.message.reply_text("❌ You are not authorized to use this command.")
        return

    try:
        if len(context.args) != 5:
            update.message.reply_text("Usage:\n/createcode <code> <amount> <minwager> <usages> <trueorfalse to have diceable on name>")
            return

        code, amount, min_wager, usages_left, is_diceable_required = context.args
        amount = float(amount)
        min_wager = float(min_wager)
        usages_left = int(usages_left)
        is_diceable_required = is_diceable_required.lower() == 'true'

        if min_wager < 0 or amount < 0 or usages_left <= 0:
            update.message.reply_text("❌ Invalid values provided. Ensure all numbers are non-negative.")
            return

        codes_cursor.execute(
            'INSERT INTO codes (code, min_wager, usages_left, is_diceable_required, amount) VALUES (?, ?, ?, ?, ?)',
            (code, min_wager, usages_left, is_diceable_required, amount)
        )
        codes_conn.commit()

        update.message.reply_text(
            f"✅ Code created successfully!\n\n"
            f"Code: `{code}`\n"
            f"Amount: ${amount}\n"
            f"Usages: {usages_left}\n"
            f"Min wager: {min_wager}\n"
            f"Required Diceable: {is_diceable_required}",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        update.message.reply_text(f"❌ Error creating code: {str(e)}")

def claim_code(update, context):
    user = update.message.from_user
    chat_type = update.message.chat.type

    if chat_type != 'private':
        update.message.reply_text("❌ Command available only in bot's private message.")
        return

    try:
        code = context.args[0]
        codes_cursor.execute('SELECT * FROM codes WHERE code = ?', (code,))
        code_data = codes_cursor.fetchone()

        if not code_data:
            update.message.reply_text("❌ Wrong code.")
            return

        _, min_wager, usages_left, is_diceable_required, amount = code_data

        if usages_left <= 0:
            update.message.reply_text("❌ Code already claimed maximum times.")
            return

        codes_cursor.execute('SELECT 1 FROM claimed_codes WHERE user_id = ? AND code = ?', (user.id, code))
        if codes_cursor.fetchone():
            update.message.reply_text("❌ Looks like you already claimed this code...")
            return

        dice_cursor.execute('SELECT total_wagered, balance FROM wallet WHERE ID = ?', (user.id,))
        wallet_data = dice_cursor.fetchone()
        if not wallet_data:
            total_wagered = 0.0
            balance = 0.0
        else:
            total_wagered, balance = wallet_data

        if total_wagered < min_wager:
            update.message.reply_text(
                f"❌ Wager requirement not met! The wager requirement is: ${min_wager}\nYour wager is: ${total_wagered}"
            )
            return

        if is_diceable_required:
            if '@diceablecasino' not in (user.username or '').lower() and \
                    '@diceablecasino' not in (user.first_name or '').lower() and \
                    '@diceablecasino' not in (user.last_name or '').lower():
                update.message.reply_text("❌ First Name Must Have @DiceableCasino")
                return

        new_balance = balance + amount
        dice_cursor.execute('UPDATE wallet SET balance = ? WHERE ID = ?', (new_balance, user.id))
        codes_cursor.execute('INSERT INTO claimed_codes (user_id, code) VALUES (?, ?)', (user.id, code))
        codes_cursor.execute('UPDATE codes SET usages_left = usages_left - 1 WHERE code = ?', (code,))
        dice_conn.commit()
        codes_conn.commit()

        update.message.reply_text(f"✅ Code claimed successfully! Amount: ${amount} added to your balance!")

        
       
        admin_message = (
            f"@{user.username} / {user.first_name} {user.last_name} / {user.id} "
            f"Claimed The Code `{code}` of amount ${amount} total usages remaining: {usages_left - 1}"
        )
        context.bot.send_message(admin_id, admin_message)

    except Exception as e:
        update.message.reply_text(f"❌ Error claiming code: {str(e)}")


def delete_code(update, context):
    if update.message.from_user.id != admin_id:
        update.message.reply_text("❌ You are not authorized to use this command.")
        return

    try:
        if len(context.args) != 1:
            update.message.reply_text("Usage:\n/deletecode <code> or /deletecode all")
            return

        if context.args[0].lower() == "all":
            codes_cursor.execute('DELETE FROM codes')
            codes_cursor.execute('DELETE FROM claimed_codes')
            codes_conn.commit()
            update.message.reply_text("✅ All codes have been deleted successfully.")
        else:
            code = context.args[0]
            codes_cursor.execute('SELECT * FROM codes WHERE code = ?', (code,))
            code_data = codes_cursor.fetchone()
            if not code_data:
                update.message.reply_text("❌ No such code found.")
                return

            codes_cursor.execute('DELETE FROM codes WHERE code = ?', (code,))
            codes_cursor.execute('DELETE FROM claimed_codes WHERE code = ?', (code,))
            codes_conn.commit()
            update.message.reply_text(f"✅ Code `{code}` has been deleted successfully.")
    except Exception as e:
        update.message.reply_text(f"❌ Error deleting code: {str(e)}")

def main():
    setup_logger()
    logger = logging.getLogger(__name__)
    logger.propagate = True
    logger.info("🔄 Starting bot...")
    bot_token = os.getenv("BOT_TOKEN_DEV")
    updater = Updater(bot_token, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("deletecode", delete_code))
    dp.add_handler(CommandHandler("createcode", create_code))
    dp.add_handler(CommandHandler("claim", claim_code))
    dp.add_handler(CommandHandler("bowl", bowl))
    dp.add_handler(CommandHandler("dart", dart))
    dp.add_handler(MessageHandler(Filters.dice.darts, dart_handler))
    dp.add_handler(MessageHandler(Filters.dice.dice, dice_handler))
    dp.add_handler(MessageHandler(Filters.dice.bowling, bowl_handler))
    dp.add_handler(CommandHandler("resetdice", resetdice))
    dp.add_handler(CommandHandler("deleterain", deleterain))
    dp.add_handler(CommandHandler("drain", drain_command))
    dp.add_handler(CommandHandler("dh", dh)) 
    dp.add_handler(CallbackQueryHandler(handle_dh_choice, pattern="^(higher|lower|same)$"))
    dp.add_handler(CommandHandler("reset_hilo", reset_hilo))
    dp.add_handler(CommandHandler("trio", trio))
    dp.add_handler(CallbackQueryHandler(handle_trio_choice, pattern=r"^choice_\d+_[\w-]+$"))
    dp.add_handler(CommandHandler("senddb", senddb))
    dp.add_handler(CommandHandler("setbotbal", set_bot_balance))
    dp.add_handler(CommandHandler("dr", dr))  # Added /dr command
    dp.add_handler(CallbackQueryHandler(handle_bet_choice, pattern=r"^(num_\d+|odd|even|high|low)_[\w-]+$"))
    dp.add_handler(CommandHandler("addstats", add_stats))
    dp.add_handler(CommandHandler("showbal", showbal_command))
    dp.add_handler(CommandHandler("setbal", setbal_command))
    dp.add_handler(CommandHandler("bstop", bot_stop))
    dp.add_handler(CommandHandler("bstart", bot_start))
    dp.add_handler(CommandHandler("mines", mines))
    dp.add_handler(CallbackQueryHandler(handle_mine_click, pattern="^\\d,\\d$"))
    dp.add_handler(CommandHandler("housebal", botbal))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("blackjack", start_blackjack))
    dp.add_handler(CommandHandler("bj", start_blackjack))
    dp.add_handler(CallbackQueryHandler(hit, pattern="hit"))
    dp.add_handler(CallbackQueryHandler(stand, pattern="stand"))
    dp.add_handler(CommandHandler("reset_blackjack", reset_blackjack_game))  # Admin-only reset command
    dp.add_handler(CommandHandler("dice", dice))
    dp.add_handler(CommandHandler("leaderboard", lb))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(CommandHandler("tip", tip))
    dp.add_handler(MessageHandler(Filters.reply, tip))
    dp.add_handler(CommandHandler("bal", bal))
    dp.add_handler(CommandHandler("depo", deposit_command))
    dp.add_handler(CommandHandler("withdraw", withdraw_command))
    job_queue = dp.job_queue
    job_queue.run_repeating(send_message, interval=60, first=10, name="deposit_checker")
    dp.add_handler(CommandHandler('rain', rain))
    dp.add_handler(CommandHandler('listrains', listrains))
    dp.add_handler(CallbackQueryHandler(participate_rain_callback, pattern='^participate_rain_'))
    dp.add_error_handler(rain_error_handler)
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button), CommandHandler("start", start)],
        states={WTH: [MessageHandler(Filters.text & ~Filters.command, wth)]},
        fallbacks=[CallbackQueryHandler(button)],
        allow_reentry=True
    )
    dp.add_handler(conv_handler)

    updater.start_polling(drop_pending_updates=True)
    updater.idle()

if __name__ == '__main__':
    main()
