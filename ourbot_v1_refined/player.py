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
        self.open_cutoff = 0.42 # top 80%
        self.open_defend = 0.52 # top 40%
        self.open_reraise = 0.60 # top 10%
        
        self.bb_defend = 0.50 # top 50%
        self.bb_reraise = 0.56 # top 24%
        self.bb_redefend = 0.59 # top 13%

        self.preflop_allin = 0.62 # top 6%

    def calc_strength(self, hole, iters, board):
        ''' 
        Using MC with iterations to evalute hand strength 

        Args: 
        hole - our hole carsd 
        iters - number of times we run MC 
        '''

        deck = eval7.Deck() # deck of cards

        for card in hole: #removing our hole cards from the deck
            deck.cards.remove(card)
        
        for card in board:
            deck.cards.remove(card)

        score = 0 

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


            if our_hand_value > opp_hand_value:
                score += 2 
            elif our_hand_value == opp_hand_value:
                score += 1 
            else: 
                score += 0        

        hand_strength = score/(2*iters) # win probability 

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

        _MONTE_CARLO_ITERS = 100
        strength = self.calc_strength(hole, _MONTE_CARLO_ITERS,board)

        # raise logic 
        if street < 3: #preflop 
            raise_amount = int(my_pip + continue_cost + (pot_total + continue_cost))
        else: #postflop
            raise_amount = int(my_pip + continue_cost + 0.5*(pot_total + continue_cost))

        # ensure raises are legal
        raise_amount = max([min_raise, raise_amount])
        raise_amount = min([max_raise, raise_amount])

        # PREFLOP casework
        # if SB, open if strength > 0.42
        if street < 3 and not self.big_blind and continue_cost == 1:
            if strength > self.open_cutoff:
                my_action = RaiseAction(raise_amount)
                return my_action
            else:
                my_action = FoldAction()
                return my_action
        # if SB, defend against 3-bet if strength > 0.50 and reraise if strength > 0.60
        if street < 3 and not self.big_blind and continue_cost > 1 and my_pip < 10:
            if strength > self.open_reraise:
                my_action = RaiseAction(raise_amount)
                return my_action
            elif strength > self.open_defend:
                my_action = CallAction()
                return my_action
            else:
                my_action = FoldAction()
                return my_action
        # if SB, defend against 5-bet if strength > 0.62
        if street < 3 and not self.big_blind and my_pip >= 10:
            if strength > self.preflop_allin:
                my_action = RaiseAction(raise_amount)
                return my_action
            else:
                my_action = FoldAction()
                return my_action
        # if BB, do not allow limpers if strength > 0.42
        if street < 3 and self.big_blind and continue_cost == 0:
            if strength > self.open_cutoff:
                my_action = RaiseAction(raise_amount)
                return my_action
            else:
                my_action = CheckAction()
                return my_action
        # if BB, defend against an open if strength > 0.5 and reraise if strength > 0.559
        if street < 3 and self.big_blind and continue_cost < 10:
            if strength > self.bb_reraise:
                my_action = RaiseAction(raise_amount)
                return my_action
            elif strength > self.bb_defend:
                my_action = CallAction()
                return my_action
            else:
                my_action = FoldAction()
                return my_action
        # if BB, all-in against a 4bet if strength > 0.62 and defend if strength > 0.58
        if street < 3 and self.big_blind and continue_cost >= 10:
            if strength > self.preflop_allin:
                my_action = RaiseAction(max_raise)
                return my_action
            elif strength > self.bb_redefend:
                my_action = CallAction()
                return my_action
            else:
                my_action = FoldAction()
                return my_action
        
        if (RaiseAction in legal_actions and (raise_amount <= my_stack)):
            temp_action = RaiseAction(raise_amount)
        elif (CallAction in legal_actions and (continue_cost <= my_stack)):
            temp_action = CallAction()
        elif CheckAction in legal_actions:
            temp_action = CheckAction()
        else:
            temp_action = FoldAction() 

        if continue_cost > 0:
            self.num_raises += 1
            out_of_range = 0.15
            for _ in range(self.num_raises):
                strength = (strength - out_of_range)/(1 - out_of_range)

            strength = max(0,strength)

            pot_odds = continue_cost/(pot_total + continue_cost)

            if strength >= pot_odds: # nonnegative EV decision
                if strength > 0.75 and random.random() < strength: 
                    my_action = temp_action
                else: 
                    my_action = CallAction()
            
            else: #negative EV
                my_action = FoldAction()
                
        else: # continue cost is 0  
            if strength > 0.25 and random.random() < strength: 
                my_action = temp_action
            else: 
                my_action = CheckAction()
        
        #if isinstance(my_action, RaiseAction):
            #self.num_raises += 1

        return my_action
        # min_raise, max_raise = round_state.raise_bounds()
        # pot_total = my_contribution + opp_contribution
        
        # _MONTE_CARLO_ITERS = 100
        # strength = self.calc_strength(hole, _MONTE_CARLO_ITERS,board)

        # range_strength = []
        # for hand in self.range:
        #     range_strength.append(self.calc_strength(hand,_MONTE_CARLO_ITERS//10,board))

        # range_strength.sort()
        # ranking = 0
        # for i in range(len(range_strength)):
        #     if range_strength[i] < strength:
        #         ranking += 1
        # percentile = ranking / len(range)
        # # raise logic 
        # if street <3: #preflop 
        #     raise_amount = int(my_pip + continue_cost + (pot_total + continue_cost))
        # else: #postflop
        #     raise_amount = int(my_pip + continue_cost + 0.75*(pot_total + continue_cost))

        # # ensure raises are legal
        # raise_amount = max([min_raise, raise_amount])
        # raise_amount = min([max_raise, raise_amount])

        # if (RaiseAction in legal_actions and (raise_amount <= my_stack)):
        #     temp_action = RaiseAction(raise_amount)
        # elif (CallAction in legal_actions and (continue_cost <= my_stack)):
        #     temp_action = CallAction()
        # elif CheckAction in legal_actions:
        #     temp_action = CheckAction()
        # else:
        #     temp_action = FoldAction() 

        

        # if continue_cost > 0: 
        #     pot_odds = continue_cost/(pot_total + continue_cost)
        #     if strength >= pot_odds: # nonnegative EV decision
        #         if random.random() < strength: 
        #             my_action = temp_action
        #         else: 
        #             my_action = CallAction()
            
        #     else: #negative EV
        #         my_action = FoldAction()
                
        # else: # continue cost is 0  
        #     if random.random() < strength: 
        #         my_action = temp_action
        #     else: 
        #         my_action = CheckAction()
            

        # return my_action
        


if __name__ == '__main__':
    run_bot(Player(), parse_args())
