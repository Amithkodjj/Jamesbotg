import random
import sqlite3
import re
import time

# Card values and deck
CARD_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10, "A": 11
}
SUITS = ['♠️', '♥️', '♣️', '♦️']
deck = [f'{value}{suit}' for value in CARD_VALUES for suit in SUITS]
multiplier_blackjack = 2.0

# Global variables for cooldowns and previous bets
cooldown = {}  # {user_id: timestamp_of_last_game_end}
previous_bets = {}  # {user_id: last_bet_amount}

def format_hand(hand):
    """Formats a list of cards into a readable string."""
    return ', '.join(hand)

def format_hand_with_suits(hand, reveal_dealer=False):
    """
    Formats a list of cards with suits. Optionally hides the dealer's second card.
    """
    if reveal_dealer:
        return "  •  ".join(hand)
    else:
        return f"{hand[0]}  •  [❔]"

def format_player_hand(player_name, player_hand, player_value, dealer_value=None):
    """
    Formats the player's hand with name, cards, and value.
    Optionally includes the dealer's value.
    """
    hand_str = "  •  ".join(player_hand)
    if dealer_value is not None:
        return f"{player_name} - Value: {player_value}\nDealer's Value: {dealer_value}\n\n{hand_str}\n"
    else:
        return f"{player_name} - Value: {player_value}\n\n{hand_str}"

def draw_card(biased=False):
    """Draw a card with an optional bias."""
    deck_copy = deck[:]
    random.shuffle(deck_copy)
    if biased:
        # Favor high-value cards (10, J, Q, K, A)
        high_value_cards = [card for card in deck_copy if CARD_VALUES[card[:-1]] >= 10]
        if high_value_cards and random.random() < 0.7:  # 70% bias
            return random.choice(high_value_cards)
    return random.choice(deck_copy)

def calculate_hand_total(hand):
    """Calculate the total value of a hand."""
    total = 0
    aces = 0

    for card in hand:
        value = re.sub(r'[^0-9A-Z]', '', card[:-1]) 
        if value not in CARD_VALUES:
            raise KeyError(f"Unexpected card value '{value}' extracted from card '{card}'.")
        total += CARD_VALUES[value]
        if value == 'A':
            aces += 1

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1

    return total

def deal_initial_hands(dealer_bias=False):
    """Deal initial hands to player and dealer, with an optional dealer bias."""
    deck_copy = deck[:]
    random.shuffle(deck_copy)

    # Deal dealer's hand
    dealer_hand = [deck_copy.pop(), deck_copy.pop()]
    if dealer_bias:  # Ensure dealer has a stronger start
        while calculate_hand_total(dealer_hand) < 17:
            dealer_hand.append(deck_copy.pop())

    # Deal player's hand
    player_hand = [deck_copy.pop(), deck_copy.pop()]
    return player_hand, dealer_hand

def start_blackjack_game(bet_amount, user_id, database_dice):
    """Start the blackjack game."""
    global previous_bets

    # Check cooldown
    if user_id in cooldown and time.time() - cooldown[user_id] < 10:
        remaining_time = 10 - int(time.time() - cooldown[user_id])
        return None, f"The dealer is shuffling! 🃏 Please wait {remaining_time} seconds."

    # Check if this bet is 2x the last bet
    last_bet = previous_bets.get(user_id, 0)
    guaranteed_loss = bet_amount >= 2 * last_bet

    # Retrieve user balance
    connection = sqlite3.connect(database_dice)
    cursor = connection.cursor()
    cursor.execute("SELECT balance FROM wallet WHERE id = ?", (user_id,))
    result = cursor.fetchone()

    if result is None or result[0] < bet_amount:
        connection.close()
        return None, "You have insufficient balance."

    # Deduct bet from balance
    new_balance = result[0] - bet_amount
    cursor.execute("UPDATE wallet SET balance = ? WHERE id = ?", (new_balance, user_id))
    connection.commit()
    connection.close()

    # Set previous bet and cooldown
    previous_bets[user_id] = bet_amount
    cooldown[user_id] = time.time()

    # Deal hands with dealer bias if guaranteed_loss
    player_hand, dealer_hand = deal_initial_hands(dealer_bias=guaranteed_loss)

    return {
        'player_hand': player_hand,
        'dealer_hand': dealer_hand,
        'bet_amount': bet_amount,
        'game_over': False,
        'guaranteed_loss': guaranteed_loss
    }, None

def handle_hit(player_hand):
    """Handle the player's decision to hit."""
    player_hand.append(draw_card(biased=True))
    return player_hand

def handle_stand(player_hand, dealer_hand, guaranteed_loss):
    """Handle the player's decision to stand."""
    player_total = calculate_hand_total(player_hand)
    dealer_total = calculate_hand_total(dealer_hand)

    # Dealer draws cards until total is at least 17
    while dealer_total < 17:
        dealer_hand.append(draw_card())
        dealer_total = calculate_hand_total(dealer_hand)

    # Guaranteed loss logic
    if guaranteed_loss:
        return f"The dealer wins with {dealer_total}! Better luck next time!", False

    # Determine winner
    if dealer_total > 21:
        return "Dealer busts! You win!", True
    elif player_total > dealer_total:
        return f"You win with {player_total} vs dealer's {dealer_total}!", True
    elif player_total == dealer_total:
        return f"It's a tie! You both have {player_total}.", False
    else:
        return f"Dealer wins with {dealer_total} vs your {player_total}. You lose!", False

def payout(bet_amount, user_id, database_dice, player_won, draw=False):
    """Handle the payout."""
    connection = sqlite3.connect(database_dice)
    cursor = connection.cursor()
    cursor.execute("UPDATE wallet SET total_games = total_games + 1 WHERE id = ?", (user_id,))

    if player_won:
        winnings = bet_amount * multiplier_blackjack
        cursor.execute("UPDATE wallet SET balance = balance + ?, total_earnings = total_earnings + ?, wins = wins + 1 WHERE id = ?", (winnings, bet_amount, user_id))
    elif draw:
        cursor.execute("UPDATE wallet SET balance = balance + ? WHERE id = ?", (bet_amount, user_id))

    connection.commit()
    connection.close()

def handle_game_end(user_id, bet_amount, player_won, draw, database_dice):
    """Handle game end logic."""
    # Start cooldown
    cooldown[user_id] = time.time()

    # Payout
    payout(bet_amount, user_id, database_dice, player_won, draw)