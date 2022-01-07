s = open('preflop_equity.txt', 'r').read().strip().splitlines()

# Fix formatting with the preflop equity list cos K was before Q lol

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

output = []
for line in s:
    hand = line.split()[0]
    if len(hand) == 2:
        print(line)
        continue
    n1 = hand[0]
    n2 = hand[1]
    if VALUE_MAP[n1] > VALUE_MAP[n2]:
        n1,n2 = n2,n1
    corrected = n1 + n2 + hand[2]
    output.append([hand[2] == 's', VALUE_MAP[n1], VALUE_MAP[n2], corrected + ' ' + line.split()[1]])

output.sort()
for x in output:
    print(x[-1])

