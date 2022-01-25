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
import math

EQUITY_MAP = {}
PERCENTILE_MAP = {}
EQUITY_LIST = []
VALUE_MAP = {
    '2': 2,
    '3': 3,
    '4': 4,
    '5': 5,
    '6': 6,
    '7': 7,
    '8': 8,
    '9': 9,
    'T': 10,
    'J': 11,
    'Q': 12,
    'K': 13,
    'A': 14,
}

def load_preflop_equity():
    def hand_class_weight(hand):
        if len(hand) == 2:
            return 6
        if hand[2] == 's':
            return 4
        return 12

    stored = open('preflop_equity.txt', 'r').read().strip().split()
    for i in range(0, len(stored), 2):
        hand_class = stored[i]
        equity = float(stored[i+1])
        EQUITY_MAP[hand_class] = equity
        EQUITY_LIST.append([equity, hand_class, hand_class_weight(hand_class)])
    
    EQUITY_LIST.sort()
    total_wt = sum(hand[2] for hand in EQUITY_LIST)
    cum_wt = 0
    for eq, hand, wt in EQUITY_LIST:
        cum_wt += wt
        PERCENTILE_MAP[hand] = cum_wt / total_wt * 100
        

def number(card):
    return str(card)[0]

def suit(card):
    return str(card)[1]

def get_hand_class(hand):
    n1 = number(hand[0])
    n2 = number(hand[1])
    if VALUE_MAP[n1] > VALUE_MAP[n2]:
        n1, n2 = n2, n1
    if n1 == n2:
        return n1 + n2
    if suit(hand[0]) == suit(hand[1]):
        return n1 + n2 + 's'
    else:
        return n1 + n2 + 'o'

def get_preflop_equity(hand):
    assert len(hand) == 2
    return EQUITY_MAP[get_hand_class(hand)]

def get_preflop_percentile(hand):
    assert len(hand) == 2
    return PERCENTILE_MAP[get_hand_class(hand)]

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

        # PERCENTILES are rounded up, i.e. best hand is 100% and worst hand is > 0%

        # PREFLOP
        self.open_cutoff = 20
        self.open_defend = 20
        self.open_reraise = 7
        self.open_redefend = 5
        
        self.bb_limpraise = 20
        self.bb_defend = 20
        self.bb_reraise = 7
        self.bb_redefend = 5

        self.preflop_allin = 5

        self.guaranteed_win = False
        self.max_loss = 200

        # self.preflop_multiplier = 1.0
        self.flop_multiplier = 1.0
        self.turn_multiplier = 1.0
        self.river_multiplier = 1.0

        self.lead_bluff = 0.1
        self.cbet_bluff = 0.2
        self.bluff_raise = 0.3

        self.sum_bet_size = 0
        self.cnt_bet_size = 0

        load_preflop_equity()

    def calc_strength(self, hole, iters, board):
        ''' 
        Using MC with iterations to evalute hand strength 

        Args: 
        hole - our hole cards 
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

            if our_hand_value >= opp_hand_value:
                score += weight
            else: 
                score += 0
                
            total_weight += weight    

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

        if round_num < 100:
            self.will_bluff = False
        else:
            self.will_bluff = True

        if remain % 2 == 0:
            mincost = 3 * (remain // 2)
            opp_mincost = 3 * (remain // 2)
            if self.big_blind:
                opp_mincost -= 1
            else:
                opp_mincost -=2
        else:
            mincost = 3 * (remain // 2)
            opp_mincost = 3 * (remain // 2)
            if self.big_blind:
                mincost += 2
            else:
                mincost += 1
        
        # if mincost < my_bankroll:
        #     self.guaranteed_win = True

        self.max_loss = my_bankroll + opp_mincost

        self.flop_call = False
        self.turn_call = False
        self.river_call = False
        self.did_raise = False
        self.did_cbet = False
        self.did_lead = False


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

        change = (my_delta/1000)
        if change < 0:
            change = -change

        bluff_change = (my_delta/2000)
        if bluff_change < 0:
            bluff_change = -bluff_change

        if street == 5 and self.river_call:
            if my_delta > 0:
                self.river_multiplier += change
                self.river_multiplier = min(self.river_multiplier,2)
            elif my_delta < 0:
                self.river_multiplier -= change
                self.river_multiplier = max(self.river_multiplier,0.5)

        if street >= 4 and self.turn_call:
            if my_delta > 0:
                self.turn_multiplier += change
                self.turn_multiplier = min(self.turn_multiplier,2)
            elif my_delta < 0:
                self.turn_multiplier -= change
                self.turn_multiplier = max(self.turn_multiplier,0.5)
        
        if street >= 3 and self.flop_call:
            if my_delta > 0:
                self.flop_multiplier += change
                self.flop_multiplier = min(self.flop_multiplier,2)
            elif my_delta < 0:
                self.flop_multiplier -= change
                self.flop_multiplier = max(self.flop_multiplier,0.5)
        
        if self.did_lead:
            if my_delta > 0 and len(opp_cards) == 0:
                self.lead_bluff += bluff_change
                self.lead_bluff = min(self.lead_bluff,1)
            else:
                self.lead_bluff -= bluff_change
                self.lead_bluff = max(self.lead_bluff,0)
        
        if self.did_cbet:
            if my_delta > 0 and len(opp_cards) == 0:
                self.cbet_bluff += bluff_change
                self.cbet_bluff = min(self.cbet_bluff,1)
            else:
                self.cbet_bluff -= bluff_change
                self.cbet_bluff = max(self.cbet_bluff,0)
        
        if self.did_raise:
            if my_delta > 0 and len(opp_cards) == 0:
                self.bluff_raise += bluff_change
                self.bluff_raise = min(self.bluff_raise,1)
            else:
                self.bluff_raise -= bluff_change
                self.bluff_raise = max(self.bluff_raise,0)

                
    
    def get_board_texture(self,board):
        suits = [str(card)[1] for card in board]
        ans = 0
        for suit in suits:
            if suits.count(suit) == 3:
                ans += 20
            elif suits.count(suit) == 2:
                ans += 10

        numbers = [VALUE_MAP[str(card)[0]] for card in board]
        for i in range(1,11):
            cnt = 0
            for _ in range(i,i+5):
                val = _
                if val == 1:
                    val = 14
                if numbers.count(val) >= 1:
                    cnt += 1
            if cnt == 2:
                ans += 1
            if cnt == 3:
                ans += 5
        # maxval = 20 + 17 = 37
        # minval = 0
        return ans
        

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
        # bet to pot ratio
        ratio = 0.7
        # if street == 3:
        #     ratio = 0.35 + self.get_board_texture(board)/37 * 0.5

        # raise logic 
        if street < 3: #preflop 3x
            raise_amount = int(my_pip + continue_cost + 2*(pot_total + continue_cost))
        else: #postflop half pot
            raise_amount = int(my_pip + continue_cost + ratio*(pot_total + continue_cost))

        # ensure raises are legal
        raise_amount = max([min_raise, raise_amount])
        raise_amount = min([max_raise, raise_amount])

        if opp_contribution > 100:
            self.will_bluff = False

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

        if my_contribution > self.max_loss and -opp_contribution <= self.max_loss:
            my_action = jam_action
            return my_action

        if my_contribution - my_pip + raise_amount > self.max_loss and -opp_contribution <= self.max_loss:
            aggro_action = jam_action
            
        if my_contribution + continue_cost > self.max_loss and -opp_contribution <= self.max_loss:
            flat_action = jam_action
            
        # do not fold preflop to small raises, 2x or less
        if street < 3 and my_contribution > 2 and continue_cost <= my_contribution:
            passive_action = flat_action

        # PREFLOP casework
        rev_percentile = 100 - get_preflop_percentile(hole)
        rev_percentile = max(rev_percentile,0)
        # if SB, open
        if street < 3 and not self.big_blind and continue_cost == 1:
            if rev_percentile < self.open_cutoff:
                my_action = aggro_action
                return my_action
            else:
                my_action = passive_action
                return my_action
        # if SB, defend against 3-bet
        if street < 3 and not self.big_blind and opp_contribution <= 50:
            if rev_percentile < self.open_reraise:
                my_action = aggro_action
                return my_action
            elif rev_percentile < self.open_defend:
                my_action = flat_action
                return my_action
            else:
                my_action = passive_action
                return my_action
        # if SB, jam against 5-bet
        if street < 3 and not self.big_blind:
            if rev_percentile < self.preflop_allin:
                my_action = jam_action
                return my_action
            elif rev_percentile < self.open_redefend:
                my_action = flat_action
                return my_action
            else:
                my_action = passive_action
                return my_action
        # if BB, do not allow limpers
        if street < 3 and self.big_blind and continue_cost == 0:
            if rev_percentile < self.bb_limpraise:
                my_action = aggro_action
                return my_action
            else:
                my_action = flat_action
                return my_action
        # if BB, defend against an open
        if street < 3 and self.big_blind and continue_cost <= 20:
            if rev_percentile < self.bb_reraise:
                my_action = aggro_action
                return my_action
            elif rev_percentile < self.bb_defend:
                my_action = flat_action
                return my_action
            else:
                my_action = passive_action
                return my_action
        # if BB, all-in against a 4bet
        if street < 3 and self.big_blind:
            if rev_percentile < self.preflop_allin:
                my_action = jam_action
                return my_action
            elif strength > self.bb_redefend:
                my_action = flat_action
                return my_action
            else:
                my_action = passive_action
                return my_action

        if street == 3:
            out_of_range = 0.05
            reraise_cutoff = 0.75
            lead_cutoff = 0.4
            cbet_cutoff = 0.25
        elif street == 4:
            out_of_range = 0.15
            reraise_cutoff = 0.8
            lead_cutoff = 0.45
            cbet_cutoff = 0.3
        else:
            out_of_range = 0.25
            reraise_cutoff = 0.85
            lead_cutoff = 0.5
            cbet_cutoff = 0.35



        if continue_cost > 0:
            self.num_raises += min(4, continue_cost/my_contribution)
        # if continue_cost > 0:
        #     self.sum_bet_size += continue_cost/my_contribution
        #     self.cnt_bet_size += 1
        #     # old_pot = my_contribution + opp_contribution - opp_pip
        #     # if opp_pip > old_pot:
        #     #     # overbet
        #     #     capped_continue_cost = old_pot - my_pip
        #     #     assert capped_continue_cost >= 0
        #     #     capped_continue_cost = max(0, capped_continue_cost)
        #     #     self.num_raises += capped_continue_cost/my_contribution
        #     # else:
        #     self.num_raises += (continue_cost/my_contribution) / (self.sum_bet_size / self.cnt_bet_size)
        #     # self.num_raises += 2 * min(1, continue_cost / old_pot)

        scared_strength = strength

        for _ in range(int(self.num_raises)):
            scared_strength = (scared_strength - out_of_range)/(1 - out_of_range)

        scared_strength = max(0.1,scared_strength)

        multiplier = 1.0

        if street == 3:
            multiplier = self.flop_multiplier
        elif street == 4:
            multiplier = self.turn_multiplier
        elif street == 5:
            multiplier = self.river_multiplier

        if continue_cost > 0:
            pot_odds = continue_cost/(pot_total + continue_cost)
            if scared_strength * multiplier >= pot_odds: # nonnegative EV decision
                if street == 3:
                    self.flop_call = True
                if street == 4:
                    self.turn_call = True
                if street == 5:
                    self.river_call = True
                if scared_strength * multiplier > reraise_cutoff: 
                    my_action = aggro_action
                    self.did_raise = True
                    self.num_raises += 1.4
                else: 
                    my_action = flat_action
            elif random.random() < self.bluff_raise and self.will_bluff:
                my_action = aggro_action
                self.did_raise = True
                self.num_raises += 1.4
            else: #negative EV
                my_action = passive_action
        else: # continue cost is 0
            if self.big_blind:
                if scared_strength > lead_cutoff and random.random() < scared_strength: 
                    my_action = aggro_action
                    self.num_raises += 1.4
                    self.did_lead = True
                elif scared_strength < lead_cutoff and random.random() < self.lead_bluff and self.will_bluff:
                    my_action = aggro_action
                    self.num_raises += 1.4
                    self.did_lead = True
                else:
                    my_action = flat_action
            else:
                if scared_strength > cbet_cutoff and random.random() < scared_strength: 
                    my_action = aggro_action
                    self.num_raises += 1.4
                    self.did_cbet = True
                elif scared_strength < cbet_cutoff and random.random() < self.cbet_bluff and self.will_bluff:
                    my_action = aggro_action
                    self.num_raises += 1.4
                    self.did_cbet = True
                else: 
                    my_action = flat_action
        return my_action


if __name__ == '__main__':
    run_bot(Player(), parse_args())
