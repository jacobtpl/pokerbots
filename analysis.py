EQUITY = {}
hands = []
def weight(hand):
    if len(hand) == 2:
        return 6
    if hand[2] == 's':
        return 4
    return 12

def load_preflop_equity():
    stored = open('preflop_equity.txt', 'r').read().strip().split()
    for i in range(0, len(stored), 2):
        EQUITY[stored[i]] = float(stored[i+1])
        hands.append([float(stored[i+1]), stored[i], weight(stored[i])])
        # if len(stored[i]) == 3:
        #     EQUITY[stored[i][1] + stored[i][0] + stored[i][2]] = float(stored[i+1])

load_preflop_equity()

from pprint import pprint
total = sum(hand[2] for hand in hands)
hands.sort()

cur = 0
for i in range(len(hands)):
    cur += hands[i][2]
    print(f'{hands[i][1]} {hands[i][0]} {cur/total}')
# print(total)