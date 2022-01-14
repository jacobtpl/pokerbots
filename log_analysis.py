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

def process_preflop_bets(round):
    bets = []
    bets.append((round[0][0], 1))
    bets.append((round[1][0], 2))
    for step in round[4:]:
        if 'call' in step:
            bets.append((step[0], bets[-1][1]))
        elif 'raise' in step:
            bets.append((step[0], int(step.split()[-1])))
        elif 'fold' in step:
            bets.append((step[0], 0))
        else:
            pass
    return bets


class Round:
    def __init__(self, round):
        self.small_blind = round[1][0]
        self.big_blind = round[2][0]
        flop_idx = None
        turn_idx = None
        river_idx = None
        showdown_idx = None

        if round[-1][0] == 'A':
            self.deltaA = int(round[-1].split()[-1])
            self.deltaB = int(round[-2].split()[-1])
        else:
            self.deltaA = int(round[-2].split()[-1])
            self.deltaB = int(round[-1].split()[-1])
            

        for i in range(len(round)):
            if 'Flop' in round[i]:
                flop_idx = i
            if 'Turn' in round[i]:
                turn_idx = i
            if 'River' in round[i]:
                river_idx = i
            if 'shows' in round[i] and showdown_idx is None:
                showdown_idx = i
        
        self.preflop_bets = process_preflop_bets(round[1:flop_idx])
        

        

rounds = [Round(r) for r in rounds]

a_fold = 0
b_fold = 0
a_win = 0
b_win = 0
for r in rounds:
    if r.preflop_bets[-1][1] == 0 and r.preflop_bets[-2][1] > 6:
        if r.preflop_bets[-1][0] == 'A':
            a_fold += 1
            b_win += r.deltaB
        else:
            b_fold += 1
            a_win += r.deltaA

print(a_fold, b_fold)
print(a_win, b_win)


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