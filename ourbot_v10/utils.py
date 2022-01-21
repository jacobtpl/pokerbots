import eval7

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
        if amount <= 12:
            return 'open'
        if amount <= 60:
            return '3-bet'
        # if amount < 150:
        #     return '4-bet'
        return 'jam'

    def add_bet(self, player, amount):
        # assert player != self.cur_round[-1][0]

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
    
    def get_range(self, player, amount):
        return self.stats[player][self.group(amount)] / self.valid_counts[player]