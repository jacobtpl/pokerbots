from eval7 import *
import random

HAND1 = ["As", "Ah"]
HAND2 = ["Ad", "Ac"]

HAND1 = [Card(x) for x in HAND1]
HAND2 = [Card(x) for x in HAND2]

ITERATIONS = 100

def disjoint(cards1, cards2):
    for card in cards1:
        if card in cards2:
            return False
    return True

def equity_against(h1, h2):
    # print(f'Equity of {h1} vs {h2}')
    eq1 = 0
    eq2 = 0
    for i in range(ITERATIONS):
        deck = Deck()
        deck.shuffle()
        hand1 = list(h1)
        hand2 = list(h2)
        
        while not disjoint(hand1 + hand2, deck[:13]):
            deck.shuffle()

        cur = 5

        # swap flop
        if random.random() < 0.145:
            hand1[0] = deck[cur]
            cur += 1
        if random.random() < 0.145:
            hand1[1] = deck[cur]
            cur += 1
        if random.random() < 0.145:
            hand2[0] = deck[cur]
            cur += 1
        if random.random() < 0.145:
            hand2[1] = deck[cur]
            cur += 1
        
        # if random.random() < 0.05:
        #     hand1[0] = deck[cur]
        #     cur += 1
        # if random.random() < 0.05:
        #     hand1[1] = deck[cur]
        #     cur += 1
        # if random.random() < 0.05:
        #     hand2[0] = deck[cur]
        #     cur += 1
        # if random.random() < 0.05:
        #     hand2[1] = deck[cur]
        #     cur += 1

        
        value1 = evaluate(hand1 + deck[:5])
        value2 = evaluate(hand2 + deck[:5])
        if value1 > value2:
            eq1 += 1
        elif value2 > value1:
            eq2 += 1
        else:
            eq1 += 0.5
            eq2 += 0.5
    return eq1

def equity_against_random(hand):
    deck = Deck()
    cnt = 0
    eq = 0
    for i in range(len(deck)):
        for j in range(i+1, len(deck)):
            if disjoint(hand, [deck[i], deck[j]]):
                cnt += 1
                eq += equity_against(hand, [deck[i], deck[j]])
    
    return eq/cnt

all_cards = Deck()
values = {}

NUMBERS = [str(x) for x in range(2,10)] + ['T', 'J', 'Q', 'K', 'A']

output = open('preflop_equity.txt', 'a')
# pockets
for n in NUMBERS:
    c1 = Card(n + 's')
    c2 = Card(n + 'h')
    hand = n+n
    eq = equity_against_random([c1, c2])
    print(f'{hand}: {eq}')
    output.write(f'{hand} {eq}\n')
    values[hand] = eq

# suited
for i in range(len(NUMBERS)):
    for j in range(i+1, len(NUMBERS)):
        c1 = Card(NUMBERS[i] + 's')
        c2 = Card(NUMBERS[j] + 's')
        hand = NUMBERS[i] + NUMBERS[j] + 's'
        eq = equity_against_random([c1, c2])
        print(f'{hand}: {eq}')
        output.write(f'{hand} {eq}\n')
        values[hand] = eq

# off-suited
for i in range(len(NUMBERS)):
    for j in range(i+1, len(NUMBERS)):
        c1 = Card(NUMBERS[i] + 's')
        c2 = Card(NUMBERS[j] + 'h')
        hand = NUMBERS[i] + NUMBERS[j] + 'o'
        eq = equity_against_random([c1, c2])
        print(f'{hand}: {eq}')
        output.write(f'{hand} {eq}\n')
        values[hand] = eq

# for i in range(len(all_cards)):
#     for j in range(i+1, len(all_cards)):
#         c1 = all_cards[i]
#         c2 = all_cards[j]
#         hand = str(c1)+str(c2)
#         eq = equity_against_random([c1, c2])
#         print(f'{hand}: {eq}')
#         values[hand] = eq

    
# print(equity_against_random([Card('Kd'), Card('Ks')]))