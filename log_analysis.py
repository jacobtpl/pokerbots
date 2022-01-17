import eval7
import pandas as pd
import matplotlib.pyplot as plt


FILENAME = 'log.txt'
text = open(FILENAME, 'r').read().strip()
rounds = text.split('\n\n')
rounds = [r.splitlines() for r in rounds]
result = rounds[-1][0]
rounds = rounds[1:-1]

final_score_A = int(result.split('(')[1].split(')')[0])
final_score_B = int(result.split('(')[-1].split(')')[0])

print(f'Score: A ({final_score_A}), B ({final_score_B})')


num_opens = {'A':0, 'B':0}
total_open_amount = {'A':0, 'B':0}

final = {}

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


def get_hand_from(line):
    cards = line.split('[')[1].split(']')[0].split()
    return cards

def process_preflop_bets(round):
    bets = []
    bets.append((round[0][0], 1))
    bets.append((round[1][0], 2))
    hand1 = get_hand_from(round[2])
    hand2 = get_hand_from(round[3])
    if round[2][0] == 'A':
        handA, handB = hand1, hand2
    else:
        handA, handB = hand2, hand1

    for step in round[4:]:
        if 'call' in step or 'check' in step:
            bets.append((step[0], bets[-1][1]))
        elif 'raise' in step:
            bets.append((step[0], int(step.split()[-1])))
        elif 'fold' in step:
            bets.append((step[0], 0))
        else:
            pass
    return bets, handA, handB

def avg(l):
    return sum(l)/len(l)

class Round:
    def __init__(self, round):
        self.text = round
        self.round_num = int(round[0].split('#')[1].split(',')[0])

        self.small_blind = round[1][0]
        self.big_blind = round[2][0]

        score = abs(int(round[0].split('(')[1].split(')')[0]))

        self.check_fold = False
        if score > (1000 - self.round_num) * 3 // 2:
            self.check_fold = True
        
        self.flop_idx = None
        self.turn_idx = None
        self.river_idx = None
        self.showdown_idx = None

        if round[-1][0] == 'A':
            self.deltaA = int(round[-1].split()[-1])
            self.deltaB = int(round[-2].split()[-1])
        else:
            self.deltaA = int(round[-2].split()[-1])
            self.deltaB = int(round[-1].split()[-1])
            

        for i in range(len(round)):
            if 'Flop' in round[i]:
                self.flop_idx = i
            if 'Turn' in round[i]:
                self.turn_idx = i
            if 'River' in round[i]:
                self.river_idx = i
            if 'shows' in round[i] and self.showdown_idx is None:
                self.showdown_idx = i
        
        self.preflop_bets, self.preflopA, self.preflopB = process_preflop_bets(round[1:self.flop_idx])



class PreflopTracker:
    NAMES = ['limp', 'open', '3-bet', '4-bet', 'jam', 'fold']
    def __init__(self):
        self.stats = [{}, {}]
        for p in range(2):
            for n in self.NAMES:
                self.stats[p][n] = 0
        self.num_rounds = 0
        self.valid_counts = [0, 0]
        self.cur_round = []
    
    def update(self, player, val):
        if val in self.stats[player]:
            self.stats[player][val] += 1
        else:
            self.stats[player][val] = 1

    def new_round(self, small_blind_player):
        self.cur_round = [(small_blind_player, 1), (1-small_blind_player, 2)]
        self.num_rounds += 1
        self.add_counts = [0, 0]

    def group(self, amount):
        assert amount >= 2
        if amount == 2:
            return 'limp'
        if amount < 15:
            return 'open'
        if amount < 60:
            return '3-bet'
        if amount < 150:
            return '4-bet'
        return 'jam'

    def add_bet(self, player, amount):
        assert player != self.cur_round[-1][0]

        if self.add_counts[player] == 0:
            self.add_counts[player] = 1
            self.valid_counts[player] += 1

        if amount == self.cur_round[-1][1]:
            if amount == 2:
                self.update(player, self.group(amount))
            else:
                self.update(player, self.group(amount))
        else:
            # raise
            self.update(player, self.group(amount))
        self.cur_round.append((player, amount))
        # self.update(player, amount)

    def fold(self, player):
        if self.add_counts[player] == 0:
            self.add_counts[player] = 1
            self.valid_counts[player] += 1
        self.update(player, 'fold')

        
load_preflop_equity()
rounds = [Round(r) for r in rounds]

# a_fold = 0
# b_fold = 0
# a_win = 0
# b_win = 0

# """
# A limp
# A open
# B limp
# B open
# """


def get_raises(round):
    raises = []
    for i in range(2, len(round)):
        if round[i][1] > round[i-1][1]:
            raises.append(round[i])
    return raises

b3 = []
ours = []
preflop_deltaA = 0

deltas = {
    'showdown': 0,
    'river': 0,
    'turn': 0,
    'flop': 0,
    'preflop': 0
}

for r in rounds:
    if r.check_fold:
        break
    raises = get_raises(r.preflop_bets)
    if len(raises) > 1:
        if raises[1][0] == 'A':
            if r.preflop_bets[-1] == ('B', 0):
                b3.append((r.preflopA, r.preflopB, False))
            else:
                b3.append((r.preflopA, r.preflopB, True))
    if r.showdown_idx is not None:
        deltas['showdown'] += r.deltaA
    elif r.river_idx is not None:
        deltas['river'] += r.deltaA
    elif r.turn_idx is not None:
        deltas['turn'] += r.deltaA
    elif r.flop_idx is not None:
        deltas['flop'] += r.deltaA
    else:
        deltas['preflop'] += r.deltaA

print(deltas)

# b3_we_fold = [get_preflop_equity(x[0]) > get_preflop_equity(x[1]) for x in b3 if x[2] is False]
# b3_we_call = [get_preflop_equity(x[0]) > get_preflop_equity(x[1]) for x in b3 if x[2] is True]
# print(f'3-Bets we fold: {avg(b3_we_fold)} (x {len(b3_we_fold)})')
# print(f'3-Bets we call: {avg(b3_we_call)} (x {len(b3_we_call)})')

# def analyse_preflop(player):
#     limp_hands = []
#     open_hands = []
#     fold_hands = []
#     win_hands = []

#     for r in rounds:
#         if r.small_blind == player:
#             hand = r.preflopA if player == 'A' else r.preflopB
#             if r.preflop_bets[2][1] == r.preflop_bets[1][1]:
#                 # limp
#                 limp_hands.append(hand)
#             elif r.preflop_bets[2][1] > r.preflop_bets[1][1]:
#                 # open
#                 open_hands.append(hand)
#             else:
#                 assert r.preflop_bets[2][1] == 0
#                 fold_hands.append(hand)
#                 if get_preflop_equity(hand) > 70:
#                     print(r.text)
    
#     return limp_hands, open_hands, fold_hands
    



# limp_hands, open_hands, fold_hands = analyse_preflop('B')

# print([f for f in fold_hands if get_preflop_equity(f) > 70])

# limp_strength = [get_preflop_percentile(hand) for hand in limp_hands]
# open_strength = [get_preflop_percentile(hand) for hand in open_hands]
# fold_strength = [get_preflop_percentile(hand) for hand in fold_hands]

# print('Limp hands (percentile):')
# print(pd.Series(limp_strength).describe())
# print('Open hands (percentile):')
# print(pd.Series(open_strength).describe())
# print('Fold hands (percentile):')
# print(pd.Series(fold_strength).describe())


# for r in rounds:
#     if r.preflop_bets[-1][1] == 0 and r.preflop_bets[-2][1] > 6:
#         if r.preflop_bets[-1][0] == 'A':
#             a_fold += 1
#             b_win += r.deltaB
#         else:
#             b_fold += 1
#             a_win += r.deltaA

# print(f'A folds: {a_fold}')
# print(f'B folds: {b_fold}')
# print(f'A delta: {a_win}')
# print(f'B delta: {b_win}')


# for round in rounds:
#     r = Round(round)
    # small_blind = round[1][0]
    # big_blind = round[2][0]
    # first_raiser = None
    # raise_amount = 0
    # if 'calls' in round[5]:
    #     # limp
    #     first_raiser = round[5][0]
    #     raise_amount = 2
    # else:
    #     for line in round:
    #         if 'raises' in line:
    #             first_raiser = line[0]
    #             raise_amount = int(line.split()[-1])
    #             break
    #         if 'Flop' in line:
    #             break
    # if first_raiser is not None:
    #     num_opens[first_raiser] += 1
    #     total_open_amount[first_raiser] += raise_amount
    # # if first_raiser == 'A':
    #     print(f'Open: {first_raiser} to {raise_amount}')
    #     x = first_raiser + ' ' + str(raise_amount)
    #     if x in final:
    #         final[x] += 1
    #     else:
    #         final[x] = 1

# print(num_opens)
# print({x: total_open_amount[x]/num_opens[x] for x in num_opens})

# print(final)


tracker = PreflopTracker()

for r in rounds:
    if r.check_fold:
        break
    tracker.new_round(0 if r.small_blind == 'A' else 1)
    for bet in r.preflop_bets[2:]:
        player = 0 if bet[0] == 'A' else 1
        if bet[1] == 0:
            tracker.fold(player)
        else:
            tracker.add_bet(player, bet[1])


for p in range(2):
    print(['A', 'B'][p], ':', tracker.stats[p], f'(total {tracker.valid_counts[p]})')
    print(['A', 'B'][p], ':', {x: tracker.stats[p][x] / tracker.valid_counts[p] for x in tracker.stats[p]})

# s = tracker.stats[1]
# df = pd.DataFrame(list(s.items()))
# df.plot.bar(x=0, y=1)
# plt.show()
