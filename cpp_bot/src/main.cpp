#include <skeleton/actions.h>
#include <skeleton/constants.h>
#include <skeleton/runner.h>
#include <skeleton/states.h>
#include <omp/HandEvaluator.h>
#include <random>
#include <algorithm>

using namespace pokerbots::skeleton;
using namespace std;
using namespace omp;

unsigned charToRank(char c) {
    switch(c) {
        case 'A': return 12;
        case 'K': return 11;
        case 'Q': return 10;
        case 'J': return 9;
        case 'T': return 8;
        case '9': return 7;
        case '8': return 6;
        case '7': return 5;
        case '6': return 4;
        case '5': return 3;
        case '4': return 2;
        case '3': return 1;
        case '2': return 0;
        default: return ~0u;
    }
}

unsigned charToSuit(char c) {
    switch(c) {
        case 's': return 0;
        case 'h': return 1;
        case 'c': return 2;
        case 'd': return 3;
        default: return ~0u;
    }
}

unsigned cardToInt(string s) {
	assert(s.length() == 2);
	return 4 * charToRank(s[0]) + charToSuit(s[1]);
}

struct Bot {
    bool bigBlind = false;
	mt19937 rng;
	uniform_real_distribution<double> udist;

	Bot() {
		rng = mt19937();
		udist = uniform_real_distribution<double>(0.0, 1.0);
	}

	double randomReal() {
		return udist(rng);
	}
	
	double getPostflopWeight(pair<int,int> hand) {
		return 1.0;
	}

	double calcStrength(pair<int,int> hole, int iters, vector<int> board) {
		if (board.size() == 0) {
			// TODO: change to GET PREFLOP EQUITY
			return 0;
		}
		vector<int> deck;
		for (int i=0;i<52;i++) {
			if (i == hole.first || i == hole.second) continue;
			if (find(board.begin(), board.end(), i) != board.end()) continue;
			deck.push_back(i);
		}

		HandEvaluator eval;
		double score = 0;
		double totalWeight = 0.0;

		for (int kk=0;kk<iters;kk++) {
			shuffle(deck.begin(), deck.end(), rng);
			
			int COMM = 5 - board.size();
			pair<int,int> oppHole = make_pair(deck[0], deck[1]);

			Hand ourHand = Hand::empty();
			ourHand += Hand(hole.first) + Hand(hole.second);
			for (int b : board) ourHand += Hand(b);
			for (int i=2;i<COMM+2;i++) ourHand += Hand(deck[i]);


			Hand oppHand = Hand::empty();
			oppHand += Hand(oppHole.first) + Hand(oppHole.second);
			for (int b : board) oppHand += Hand(b);
			for (int i=2;i<COMM+2;i++) oppHand += Hand(deck[i]);
			
			int ourValue = eval.evaluate(ourHand);
			int oppValue = eval.evaluate(oppHand);

			double weight = getPostflopWeight(oppHole);

			if (ourValue >= oppValue) {
				score += weight;
			} else if (ourValue == oppValue) {
				score += 0.0;
			}
			totalWeight += weight;
		}
		double strength = score / totalWeight;
		return strength;
	}

    /*
    Called when a new round starts. Called NUM_ROUNDS times.

    @param gameState The GameState object.
    @param roundState The RoundState object.
    @param active Your player's index.
	*/
    void handleNewRound(GameInfoPtr gameState, RoundStatePtr roundState, int active) {
        int myBankroll = gameState->bankroll;      // the total number of chips you've gained or lost from the beginning of the game to the start of this round
        float gameClock = gameState->gameClock;    // the total number of seconds your bot has left to play this game
        int roundNum = gameState->roundNum;        // the round number from 1 to State.NUM_ROUNDS
        auto myCards = roundState->hands[active];  // your cards
        bigBlind = (active == 1);                  // true if you are the big blind
    }

    /*
    Called when a round ends. Called NUM_ROUNDS times.

    @param gameState The GameState object.
    @param terminalState The TerminalState object.
    @param active Your player's index.
	*/
    void handleRoundOver(GameInfoPtr gameState, TerminalStatePtr terminalState, int active) {
        int myDelta = terminalState->deltas[active];                                                    // your bankroll change from this round
        auto previousState = std::static_pointer_cast<const RoundState>(terminalState->previousState);  // RoundState before payoffs
        int street = previousState->street;                                                             // 0, 3, 4, or 5 representing when this round ended
        auto myCards = previousState->hands[active];                                                    // your cards
        auto oppCards = previousState->hands[1 - active];                                               // opponent's cards or "" if not revealed
    }

	pair<int,int> toHand(array<string, 2UL> hand) {
		return make_pair(cardToInt(hand[0]), cardToInt(hand[1]));
	}

    /*
    Where the magic happens - your code should implement this function.
    Called any time the engine needs an action from your bot.

    @param gameState The GameState object.
    @param roundState The RoundState object.
    @param active Your player's index.
    @return Your action.
	*/
    Action getAction(GameInfoPtr gameState, RoundStatePtr roundState, int active) {
        auto legalActions = roundState->legalActions();   // the actions you are allowed to take
        int street = roundState->street;                  // 0, 3, 4, or 5 representing pre-flop, flop, turn, or river respectively
        auto myCards = roundState->hands[active];         // your cards
        auto boardCards = roundState->deck;               // the board cards
        int myPip = roundState->pips[active];             // the number of chips you have contributed to the pot this round of betting
        int oppPip = roundState->pips[1 - active];        // the number of chips your opponent has contributed to the pot this round of betting
        int myStack = roundState->stacks[active];         // the number of chips you have remaining
        int oppStack = roundState->stacks[1 - active];    // the number of chips your opponent has remaining
        int continueCost = oppPip - myPip;                // the number of chips needed to stay in the pot
        int myContribution = STARTING_STACK - myStack;    // the number of chips you have contributed to the pot
        int oppContribution = STARTING_STACK - oppStack;  // the number of chips your opponent has contributed to the pot

		int minRaise = 0;
		int maxRaise = 0;

		if (legalActions.find(Action::Type::RAISE) != legalActions.end()) {
			auto raiseBounds = roundState->raiseBounds();  // the smallest and largest numbers of chips for a legal bet/raise
			minRaise = raiseBounds[0];          // the cost of a minimum bet/raise
			maxRaise = raiseBounds[1];          // the cost of a maximum bet/raise
		}

		int potTotal = myContribution + oppContribution;
		int raiseAmount = 0;
		if (street < 3) {
			raiseAmount = (int)(0.4 * (potTotal + continueCost) + myPip + continueCost);
		} else {
			raiseAmount = (int)(0.75 * (potTotal + continueCost) + myPip + continueCost);
		}

		raiseAmount = max(raiseAmount, minRaise);
		raiseAmount = min(raiseAmount, maxRaise);

		Action tempAction;
        if (legalActions.count(Action::Type::RAISE) && raiseAmount <= myStack) {
            tempAction = Action(Action::Type::RAISE, raiseAmount);
        } else if (legalActions.count(Action::Type::CALL) && continueCost <= myStack) {
            tempAction = Action(Action::Type::CALL);
        } else if (legalActions.count(Action::Type::CHECK) && continueCost <= myStack) {
            tempAction = Action(Action::Type::CHECK);
		} else {
            tempAction = Action(Action::Type::FOLD);
		}

		const int MC_ITERS = 100;
		pair<int,int> myHand = toHand(myCards);
		cout << myCards[0] << " " << myCards[1] << endl;
		cout << myHand.first << " " << myHand.second << endl;
		double strength = calcStrength(myHand, MC_ITERS);
		cout << strength << endl;
		double SCARY = 0.0;

		Action myAction;

		if (continueCost > 0) {
			if (continueCost > 6) {
				SCARY = 0.1;
			}
			if (continueCost > 15) {
				SCARY = 0.2;
			}
			if (continueCost > 50) {
				SCARY = 0.35;
			}

			strength = max(0.0, strength - SCARY);
			double potOdds = continueCost/(potTotal + continueCost);
	
			if (strength >= potOdds) {
				if (strength > 0.5 && randomReal() < strength) {
					myAction = tempAction;
				} else {
					myAction = Action(Action::Type::CALL);
				}
			} else {
				myAction = Action(Action::Type::FOLD);
			}
		} else {
			if (randomReal() < strength) {
				myAction = tempAction;
			} else {
				myAction = Action(Action::Type::CHECK);
			}
		}
		return myAction;
    }
};

/*
  Main program for running a C++ pokerbot.
*/
int main(int argc, char *argv[]) {
    auto [host, port] = parseArgs(argc, argv);
    runBot<Bot>(host, port);
    return 0;
}
