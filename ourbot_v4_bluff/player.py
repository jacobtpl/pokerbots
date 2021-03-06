'''
Simple example pokerbot, written in Python.
'''
from skeleton.actions import FoldAction, CallAction, CheckAction, RaiseAction
from skeleton.states import GameState, TerminalState, RoundState
from skeleton.states import NUM_ROUNDS, STARTING_STACK, BIG_BLIND, SMALL_BLIND
from skeleton.bot import Bot
from skeleton.runner import parse_args, run_bot

import random 
import eval7

EQUITY = {}
def load_preflop_equity():
    stored = open('preflop_equity.txt', 'r').read().strip().split()
    for i in range(0, len(stored), 2):
        EQUITY[stored[i]] = float(stored[i+1])
        if len(stored[i]) == 3:
            EQUITY[stored[i][1] + stored[i][0] + stored[i][2]] = float(stored[i+1])

def number(card):
    return str(card)[0]

def suit(card):
    return str(card)[1]

def get_preflop_equity(hand):
    assert len(hand) == 2
    n1 = number(hand[0])
    n2 = number(hand[1])
    if n1 == n2:
        return EQUITY[n1 + n2]
    if suit(hand[0]) == suit(hand[1]):
        return EQUITY[n1 + n2 + 's']
    else:
        return EQUITY[n1 + n2 + 'o']

class Player(Bot):
    '''
    A pokerbot.
    '''
    

    def __init__(self):
        '''
        Called when a new game starts. Called exactly once.
        
        Arguments:
        Nothing.

        Returns:
        Nothing.
        '''
        # self.played_bb = 0
        # self.played_sb = 0
        # self.opp_defend_bb = 0
        # self.opp_fold_bb = 0
        # self.opp_raise_bb = 0
        # self.opp_open_sb = 0
        # self.opp_fold_sb = 0
        # self.opp_limp_sb = 0
        self.open_cutoff = 0.45 # top 70%
        self.open_defend = 0.52 # top 40%
        self.open_reraise = 0.60 # top 10%
        
        self.bb_defend = 0.50 # top 50%
        self.bb_reraise = 0.559 # top 24%
        self.bb_redefend = 0.59 # top 13%

        self.preflop_allin = 0.62 # top 6%

        self.guaranteed_win = False
        load_preflop_equity()

    def calc_strength(self, hole, iters, board):
        ''' 
        Using MC with iterations to evalute hand strength 

        Args: 
        hole - our hole carsd 
        iters - number of times we run MC 
        '''
        if len(board) == 0:
            return get_preflop_equity(hole)/100
    
        deck = eval7.Deck() # deck of cards

        for card in hole: #removing our hole cards from the deck
            deck.cards.remove(card)
        
        for card in board:
            deck.cards.remove(card)

        score = 0 

        total_weight = 0

        for _ in range(iters): # MC the probability of winning

            deck.shuffle()

            _OPP = 2 
            _COMM = 5 - len(board)

            draw = deck.peek(_OPP + _COMM)

            opp_hole = draw[:_OPP]
            community = draw[_OPP:] + board

            our_hand = hole + community
            opp_hand = opp_hole + community

            our_hand_value = eval7.evaluate(our_hand)
            opp_hand_value = eval7.evaluate(opp_hand)

            weight = get_preflop_equity(opp_hole)

            if our_hand_value > opp_hand_value:
                score += weight
            elif our_hand_value == opp_hand_value:
                score += weight/2
            else: 
                score += 0
                
            total_weight += weight    

        # hand_strength = score/(2*iters) # win probability 
        hand_strength = score/total_weight

        return hand_strength


    def handle_new_round(self, game_state, round_state, active):
        '''
        Called when a new round starts. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        my_bankroll = game_state.bankroll  # the total number of chips you've gained or lost from the beginning of the game to the start of this round
        game_clock = game_state.game_clock  # the total number of seconds your bot has left to play this game
        round_num = game_state.round_num  # the round number from 1 to NUM_ROUNDS
        my_cards = round_state.hands[active]  # your cards
        self.big_blind = bool(active)  # True if you are the big blind
        self.num_raises = 0

        remain = 1000 - round_num + 1
        if remain % 2 == 0:
            mincost = 3 * (remain // 2)
        else:
            mincost = 3 * (remain // 2)
            if self.big_blind:
                mincost += 2
            else:
                mincost += 1
        
        if mincost < my_bankroll:
            self.guaranteed_win = True

        if my_bankroll < -300: # aggro play if behind
            self.open_cutoff = 0.00 # top 100%
            self.open_defend = 0.45 # top 70%
            self.aggro = 0.2
        elif my_bankroll < -100:
            self.open_cutoff = 0.40 # top 87%
            self.open_defend = 0.47 # top 63%
            self.aggro = 0.1
        else:
            self.open_cutoff = 0.45 # top 70%
            self.open_defend = 0.52 # top 40%
            if my_bankroll > 200:
                self.aggro = -0.1
            else:
                self.aggro = 0.0


    def handle_round_over(self, game_state, terminal_state, active):
        '''
        Called when a round ends. Called NUM_ROUNDS times.

        Arguments:
        game_state: the GameState object.
        terminal_state: the TerminalState object.
        active: your player's index.

        Returns:
        Nothing.
        '''
        my_delta = terminal_state.deltas[active]  # your bankroll change from this round
        previous_state = terminal_state.previous_state  # RoundState before payoffs
        street = previous_state.street  # 0, 3, 4, or 5 representing when this round ended
        my_cards = previous_state.hands[active]  # your cards
        opp_cards = previous_state.hands[1-active]  # opponent's cards or [] if not revealed
        

    def get_action(self, game_state, round_state, active):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the engine needs an action from your bot.

        Arguments:
        game_state: the GameState object.
        round_state: the RoundState object.
        active: your player's index.

        Returns:
        Your action.
        '''
        legal_actions = round_state.legal_actions()  # the actions you are allowed to take
        street = round_state.street  # 0, 3, 4, or 5 representing pre-flop, flop, turn, or river respectively
        my_cards = round_state.hands[active]  # your cards
        board_cards = round_state.deck[:street]  # the board cards
        my_pip = round_state.pips[active]  # the number of chips you have contributed to the pot this round of betting
        opp_pip = round_state.pips[1-active]  # the number of chips your opponent has contributed to the pot this round of betting
        my_stack = round_state.stacks[active]  # the number of chips you have remaining
        opp_stack = round_state.stacks[1-active]  # the number of chips your opponent has remaining
        continue_cost = opp_pip - my_pip  # the number of chips needed to stay in the pot
        my_contribution = STARTING_STACK - my_stack  # the number of chips you have contributed to the pot
        opp_contribution = STARTING_STACK - opp_stack  # the number of chips your opponent has contributed to the pot
        net_upper_raise_bound = round_state.raise_bounds()
        stacks = [my_stack, opp_stack] #keep track of our stacks

        my_action = None

        min_raise, max_raise = round_state.raise_bounds()
        pot_total = my_contribution + opp_contribution

        hole = [eval7.Card(card) for card in my_cards]
        board = [eval7.Card(card) for card in board_cards]

        _MONTE_CARLO_ITERS = 200
        strength = self.calc_strength(hole, _MONTE_CARLO_ITERS, board)

        # raise logic 
        if street < 3: #preflop 3x
            raise_amount = int(my_pip + continue_cost + (pot_total + continue_cost))
        else: #postflop half pot
            raise_amount = int(my_pip + continue_cost + 0.5*(pot_total + continue_cost))

        # ensure raises are legal
        raise_amount = max([min_raise, raise_amount])
        raise_amount = min([max_raise, raise_amount])

        if RaiseAction in legal_actions:
            jam_action = RaiseAction(max_raise)
        elif CallAction in legal_actions:
            jam_action = CallAction()
        else:
            jam_action = CheckAction()

        if RaiseAction in legal_actions:
            aggro_action = RaiseAction(raise_amount)
        elif CallAction in legal_actions:
            aggro_action = CallAction()
        else:
            aggro_action = CheckAction()

        if CallAction in legal_actions:
            flat_action = CallAction()
        else:
            flat_action = CheckAction()

        if CheckAction in legal_actions:
            passive_action = CheckAction()
        else:
            passive_action = FoldAction()

        if self.guaranteed_win:
            my_action = passive_action
            return my_action

        # PREFLOP casework
        # if SB, open if strength > 0.42
        if street < 3 and not self.big_blind and continue_cost == 1:
            if strength > self.open_cutoff:
                my_action = aggro_action
                return my_action
            else:
                my_action = passive_action
                return my_action
        # if SB, defend against 3-bet if strength > 0.50 and reraise if strength > 0.60
        if street < 3 and not self.big_blind and continue_cost > 1 and my_pip < 10:
            if strength > self.open_reraise:
                my_action = aggro_action
                return my_action
            elif strength > self.open_defend:
                my_action = flat_action
                return my_action
            else:
                my_action = passive_action
                return my_action
        # if SB, jam against 5-bet if strength > 0.62
        # note that we never defend, currently because our post-flop play is weak
        if street < 3 and not self.big_blind and my_pip >= 10:
            if strength > self.preflop_allin:
                my_action = jam_action
                return my_action
            else:
                my_action = passive_action
                return my_action
        # if BB, do not allow limpers if strength > 0.42
        if street < 3 and self.big_blind and continue_cost == 0:
            if strength > self.open_cutoff:
                my_action = aggro_action
                return my_action
            else:
                my_action = flat_action
                return my_action
        # if BB, defend against an open if strength > 0.5 and reraise if strength > 0.559
        if street < 3 and self.big_blind and continue_cost < 10:
            if strength > self.bb_reraise:
                my_action = aggro_action
                return my_action
            elif strength > self.bb_defend:
                my_action = flat_action
                return my_action
            else:
                my_action = passive_action
                return my_action
        # if BB, all-in against a 4bet if strength > 0.62 and defend if strength > 0.58
        if street < 3 and self.big_blind and continue_cost >= 10:
            if strength > self.preflop_allin:
                my_action = jam_action
                return my_action
            elif strength > self.bb_redefend:
                my_action = flat_action
                return my_action
            else:
                my_action = passive_action
                return my_action

        # CURRENT VALUES:
        # flop scare factor = 0.1
        # turn scare factor = 0.15
        # river scare factor = 0.2
        # reraise flop if 0.8, lead if 0.6
        # reraise turn if 0.8, lead if 0.6
        # reraise river if 0.85, lead if 0.7
        if street == 3:
            out_of_range = 0.1
            reraise_cutoff = 0.8
            lead_cutoff = 0.6
            cbet_cutoff = 0.0
            lead_bluff = 0.1
            check_bluff = 0.2
        elif street == 4:
            out_of_range = 0.2
            reraise_cutoff = 0.8
            lead_cutoff = 0.6
            cbet_cutoff = 0.0
            lead_bluff = 0.1
            check_bluff = 0.2
        else:
            out_of_range = 0.3
            reraise_cutoff = 0.85
            lead_cutoff = 0.7
            cbet_cutoff = 0.0
            lead_bluff = 0.1
            check_bluff = 0.2

        scared_strength = strength

        for _ in range(self.num_raises):
            scared_strength = (scared_strength - out_of_range)/(1 - out_of_range)

        scared_strength = max(0,scared_strength)
        scared_strength += self.aggro
        if continue_cost > 0:
            self.num_raises += 1
            pot_odds = continue_cost/(pot_total + continue_cost)

            scared_strength = (scared_strength - out_of_range)/(1 - out_of_range)
            scared_strength = max(0,scared_strength)

            if scared_strength >= pot_odds: # nonnegative EV decision
                if scared_strength > reraise_cutoff: 
                    my_action = aggro_action
                    self.num_raises += 1
                else: 
                    my_action = flat_action
            
            else: #negative EV
                my_action = passive_action
        else: # continue cost is 0
            if self.big_blind:
                if scared_strength > lead_cutoff: 
                    my_action = aggro_action
                    self.num_raises += 1
                elif scared_strength < lead_bluff and random.random() < (scared_strength+lead_bluff)/(scared_strength + 2*lead_bluff):
                    my_action = aggro_action
                    if street == 5:
                        my_action = jam_action
                    self.num_raises += 1
                else: 
                    my_action = flat_action
            else:
                if scared_strength > cbet_cutoff: 
                    my_action = aggro_action
                    self.num_raises += 1
                elif scared_strength < check_bluff and random.random() < (scared_strength+check_bluff)/(scared_strength + 2*check_bluff):
                    my_action = aggro_action
                    if street == 5:
                        my_action = jam_action
                    self.num_raises += 1
                else: 
                    my_action = flat_action
        return my_action


if __name__ == '__main__':
    run_bot(Player(), parse_args())
