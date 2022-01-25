#include <skeleton/actions.h>
#include <skeleton/constants.h>
#include <skeleton/runner.h>
#include <skeleton/states.h>
#include <omp/HandEvaluator.h>
#include <random>
#include <algorithm>
#include <fstream>
#include <map>
#include <iostream>

using namespace pokerbots::skeleton;
using namespace std;
using namespace omp;

int charToRank(char c) {
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

int charToSuit(char c) {
    switch(c) {
        case 's': return 0;
        case 'h': return 1;
        case 'c': return 2;
        case 'd': return 3;
        default: return ~0u;
    }
}

int intToRank(int card) {
	return card/4;
}
int intToSuit(int card) {
	return card%4;
}
int bothToInt(int rank, int suit) {
	return 4 * rank + suit;
}

int cardToInt(string s) {
	assert(s.length() == 2);
	return 4 * charToRank(s[0]) + charToSuit(s[1]);
}

map<pair<int,int>, double> EQUITY, PERCENTILE;

void loadPreflopEquity() {
	ifstream file("preflop_equity_cpp.txt");
	for (int i=0;i<169;i++) {
		int r1, r2, suited;
		double eq;
		file >> r1 >> r2 >> suited >> eq;
		r1 -= 2;
		r2 -= 2;
		if (suited) {
			assert(r1 != r2);
			for (int s=0;s<4;s++) {
				EQUITY[make_pair(bothToInt(r1, s), bothToInt(r2, s))] = eq;
				EQUITY[make_pair(bothToInt(r2, s), bothToInt(r1, s))] = eq;
			}
		} else {
			for (int s1=0;s1<4;s1++) {
				for (int s2=0;s2<4;s2++) {
					if (s1 == s2) continue;
					EQUITY[make_pair(bothToInt(r1, s1), bothToInt(r2, s2))] = eq;
					EQUITY[make_pair(bothToInt(r2, s2), bothToInt(r1, s1))] = eq;
				}
			}
		}
	}
	vector<pair<double, pair<int,int> > > v;
	for (auto x : EQUITY) {
		v.push_back(make_pair(x.second, x.first));
	}
	sort(v.begin(), v.end());
	for (int i=0;i<v.size();i++) {
		PERCENTILE[v[i].second] = (double)(i+1)/(double)v.size() * 100.0;
	}
}
double getPreflopEquity(pair<int,int> hand) {
	return EQUITY[hand];
}
double getPreflopPercentile(pair<int,int> hand) {
	return PERCENTILE[hand];
}

struct PreflopTracker {
	vector<string> NAMES = {"fold", "limp", "open", "3-bet", "jam"};
	int stats[2][2][5];
	int counts[2][2][5];
	int num_rounds = 0;
	int small_blind;
	bool done;

	PreflopTracker() {
		// init maps
		memset(stats, 0, sizeof(stats));
		memset(counts, 0, sizeof(counts));
	}

	void new_round(int small_blind_player) {
		small_blind = small_blind_player;
		num_rounds++;
		done = false;
	}
	
	int get_index(int amount) {
		if (amount < 2) return 0;
		if (amount == 2) {
			return 1;
		}
		if (amount <= 12) {
			return 2;
		}
		if (amount <= 60) {
			return 3;
		}
		return 4;
	}

	void update_to(int player, int blind, int idx) {
		for (int i=0;i<=idx;i++) {
			stats[player][blind][i]++;
		}
		for (int i=0;i<=idx;i++) {
			counts[player][blind][i]++;
		}
	}
	void update_all(int player, int blind, int idx) {
		for (int i=0;i<=idx;i++) {
			stats[player][blind][i]++;
		}
		for (int i=0;i<5;i++) {
			counts[player][blind][i]++;
		}
	}
	void add_preflop_bets(int bet0, int bet1, int last_to_act) {
		assert(!done);
		cout << "0 bet " << bet0 << ", 1 bet " << bet1 << ", " << last_to_act << " last to act" << endl;
		int blind0 = (small_blind == 0)?0:1;
		if (bet0 == bet1) {
			int idx = get_index(bet0);
			if (last_to_act == 0) {
				// 1 raised and 0 called
				// 1 no chance to raise further
				// 0 can be updated everything
				update_all(0, blind0, idx);
				update_to(1, 1-blind0, idx);
			} else {
				// 0 raised and 1 called
				update_to(0, blind0, idx);
				update_all(1, 1-blind0, idx);
			}
		} else {
			if (bet0 < bet1) {
				// 0 folded to 1
				// 0 update all
				update_all(0, blind0, get_index(bet0));
				update_to(1, 1-blind0, get_index(bet1));
			} else {
				// 1 folded to 0
				// 1 update all
				update_to(0, blind0, get_index(bet0));
				update_all(1, 1-blind0, get_index(bet1));
			}
		}
	}

	double get_blind_range(int player, int blind, int amount) {
        return (double)stats[player][blind][get_index(amount)] / (double)counts[player][blind][get_index(amount)];
	}

	bool has_data(int player, int blind, int amount) {
		return (counts[player][blind][get_index(amount)] > 0);
	}
	
	pair<double, double> get_percentile_bounds(int player, int blind, int amount) {
        int grp = get_index(amount);
        int next = grp + 1;
        double low_bound = 100.0 * (1.0 - get_blind_range(player, blind, amount));
        double high_bound = 100.0;
		if (next < 5 && counts[player][blind][next] > 0) {
            double next_range = (double)stats[player][blind][next] / (double)counts[player][blind][next];
            high_bound = 100.0 * (1.0 - next_range);
		}
        return make_pair(low_bound, high_bound);
	}

	double get_total_range(int player, int amount) {
		int idx = get_index(amount);
        return (double)(stats[player][0][idx] + stats[player][0][idx]) / (double)(counts[player][0][idx] + counts[player][1][idx]);
	}

    string get_stat(int player, int blind) {
		stringstream out;
		for (int i=0;i<5;i++) {
			string x = NAMES[i];
			if (counts[player][blind][i] == 0) {
				out << x << ": " << "None" << ", ";
			} else {
				out << x << ": " << (double)stats[player][blind][i] / (double)counts[player][blind][i] << ", ";
			}
		}
		return out.str();
	}
};
struct Bot {
	mt19937 rng;
	uniform_real_distribution<double> udist;

	bool bigBlind = false;

	int roundNum;
	double num_raises = 0.0;
	bool flop_call = false;
	bool turn_call = false;
	bool river_call = false;
	bool did_raise = false;
	bool did_cbet = false;
	bool did_lead = false;

	// PREFLOP CONSTANTS

	double open_cutoff = 80;
	double open_defend = 50;
	double open_reraise = 15;
	double open_redefend = 12;

	double bb_limpraise = 65;
	double bb_defend = 65;
	double bb_reraise = 25;
	double bb_redefend = 18;

	double preflop_allin = 6;

	bool guaranteed_win = false;
	int max_loss = 200;
	
	// TRACKER CONSTANTS
	double round_start_using_tracker = 150;
	double low_spread = 20; // percent
	double low_min_weight = 0.1;
	double high_spread = 20; // percent
	double high_min_weight = 0.5;

	// MULTIPLIERS
	double preflop_multiplier = 1.0;
	double flop_multiplier = 1.0;
	double turn_multiplier = 1.0;
	double river_multiplier = 1.0;

	double lead_bluff = 0.1;
	double cbet_bluff = 0.2;
	double bluff_raise = 0.3;

	bool will_bluff = false;

	bool last_raised = false;
	bool we_last_raised = false;

	int final_preflop_bet = 0;
	PreflopTracker tracker;

	Bot() {
		rng = mt19937();
		udist = uniform_real_distribution<double>(0.0, 1.0);
		loadPreflopEquity();
		tracker = PreflopTracker();
	}

	double randomReal() {
		return udist(rng);
	}
	
	double getPostflopWeight(pair<int,int> hand) {
		if (roundNum < round_start_using_tracker) {
			return getPreflopEquity(hand);
		}
		pair<double, double> bounds;
		if (bigBlind) {
			if (!tracker.has_data(1, 0, final_preflop_bet)) {
				cout << "ERROR: No data yet" << endl;
				return getPreflopEquity(hand);
			}
			bounds = tracker.get_percentile_bounds(1, 0, final_preflop_bet);
		} else {
			if (!tracker.has_data(1, 1, final_preflop_bet)) {
				cout << "ERROR: No data yet" << endl;
				return getPreflopEquity(hand);
			}
			bounds = tracker.get_percentile_bounds(1, 1, final_preflop_bet);
		}

		double pct = getPreflopPercentile(hand);
		double low_pct = bounds.first;
		double high_pct = bounds.second;

		if (pct < low_pct) {
            double low_cutoff = low_pct - low_spread;
            if (pct < low_cutoff) {
                return low_min_weight;
			} else {
                return low_min_weight + (1.0 - low_min_weight) * (pct - low_cutoff) / low_spread;
			}
		} else if (pct > high_pct) {
            double high_cutoff = high_pct + high_spread;
            if (pct > high_cutoff) {
                return high_min_weight;
            } else {
                return high_min_weight + (1.0 - high_min_weight) * (high_cutoff - pct) / high_spread;
			}
		}
        return 1.0;
	}

	double calcStrength(pair<int,int> hole, int iters, vector<int> board) {
		if (board.size() == 0) {
			return getPreflopEquity(hole)/100.0;
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

	void checkGuaranteedWin(int bankroll) {
		int remain = 1000 - roundNum + 1;

		if (roundNum < 100) {
			will_bluff = false;
		} else {
			will_bluff = true;
		}

		int mincost, opp_mincost;
		if (remain%2 == 0) {
			mincost = 3 * (remain/2);
			opp_mincost = 3 * (remain/2);
			if (bigBlind) {
				opp_mincost -= 1;
			} else {
				opp_mincost -= 2;
			}
		} else {
			mincost = 3 * (remain/2);
			opp_mincost = 3 * (remain/2);
			if (bigBlind) {
				mincost += 2;
			} else {
				mincost += 1;
			}
		}

		if (mincost < bankroll) {
			// guaranteed_win = true;
		}
		max_loss = bankroll + opp_mincost;
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
        roundNum = gameState->roundNum;        // the round number from 1 to State.NUM_ROUNDS
        auto myCards = roundState->hands[active];  // your cards
        bigBlind = (active == 1);                  // true if you are the big blind
		num_raises = 0.0;

		if (bigBlind) {
			tracker.new_round(1);
		} else {
			tracker.new_round(0);
		}
		checkGuaranteedWin(myBankroll);

		flop_call = false;
		turn_call = false;
		river_call = false;
		did_raise = false;
		did_cbet = false;
		did_lead = false;

		we_last_raised = false;

		cout << "Round " << roundNum << ":" << endl;
    }

    /*
    Called when a round ends. Called NUM_ROUNDS times.

    @param gameState The GameState object.
    @param terminalState The TerminalState object.
    @param active Your player's index.
	*/
    void handleRoundOver(GameInfoPtr gameState, TerminalStatePtr terminalState, int active) {
        int my_delta = terminalState->deltas[active];                                                    // your bankroll change from this round
        auto previousState = std::static_pointer_cast<const RoundState>(terminalState->previousState);  // RoundState before payoffs
        int street = previousState->street;                                                             // 0, 3, 4, or 5 representing when this round ended
        auto myCards = previousState->hands[active];                                                    // your cards
        auto oppCards = previousState->hands[1 - active];                                               // opponent's cards or "" if not revealed
    
		if (street == 0) {
			int myPip = previousState->pips[active];
			int oppPip = previousState->pips[1 - active];
			cout << "Round ended preflop" << endl;
			assert(myPip != oppPip);
			if (my_delta > 0) {
				assert(myPip > oppPip);
				tracker.add_preflop_bets(myPip, oppPip, 0);
			} else {
				assert(myPip < oppPip);
				tracker.add_preflop_bets(myPip, oppPip, 1);
			}
			tracker.done = true;
		}

		double change = 0.05;
		double bluff_change = 0.02;

		if (street == 5 && river_call) {
			if (my_delta > 	0) {
				river_multiplier += change;
				river_multiplier = min(river_multiplier,2.0);
			} else if (my_delta < 0) {
				river_multiplier -= change;
				river_multiplier = max(river_multiplier,0.33);
			}
		}
		if (street >= 4 && turn_call) {
			if (my_delta > 0) {
				turn_multiplier += change;
				turn_multiplier = min(turn_multiplier,2.0);
			} else if (my_delta < 0) {
				turn_multiplier -= change;
				turn_multiplier = max(turn_multiplier,0.33);
			}
		}
		if (street >= 3 && flop_call) {
			if (my_delta > 0) {
				flop_multiplier += change;
				flop_multiplier = min(flop_multiplier,2.0);
			} else if (my_delta < 0) {
				flop_multiplier -= change;
				flop_multiplier = max(flop_multiplier,0.33);
			}
		}
		if (did_lead) {
			if (my_delta > 0 && oppCards.size() == 0) {
				lead_bluff += bluff_change;
				lead_bluff = min(lead_bluff,1.0);
			} else {
				lead_bluff -= bluff_change;
				lead_bluff = max(lead_bluff,0.0);
			}
		}
		if (did_cbet) {
			if (my_delta > 0 && oppCards.size() == 0) {
				cbet_bluff += bluff_change;
				cbet_bluff = min(cbet_bluff,1.0);
			} else {
				cbet_bluff -= bluff_change;
				cbet_bluff = max(cbet_bluff,0.0);
			}
		}
		if (did_raise) {
			if (my_delta > 0 && oppCards.size() == 0) {
				bluff_raise += bluff_change;
				bluff_raise = min(bluff_raise,1.0);
			} else {
				bluff_raise -= bluff_change;
				bluff_raise = max(bluff_raise,0.0);
			}
		}

		cout << "Us in SB: " << tracker.get_stat(0, 0) << endl;
		cout << "Us in BB: " << tracker.get_stat(0, 1) << endl;
		cout << "Op in SB: " << tracker.get_stat(1, 0) << endl;
		cout << "Op in BB: " << tracker.get_stat(1, 1) << endl;
		cout << endl;
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
		vector<int> board;
		for (int i=0;i<street;i++) {
			board.push_back(cardToInt(boardCards[i]));
		}
		
        int myPip = roundState->pips[active];             // the number of chips you have contributed to the pot this round of betting
        int oppPip = roundState->pips[1 - active];        // the number of chips your opponent has contributed to the pot this round of betting
        int myStack = roundState->stacks[active];         // the number of chips you have remaining
        int oppStack = roundState->stacks[1 - active];    // the number of chips your opponent has remaining
        int continueCost = oppPip - myPip;                // the number of chips needed to stay in the pot
        int myContribution = STARTING_STACK - myStack;    // the number of chips you have contributed to the pot
        int oppContribution = STARTING_STACK - oppStack;  // the number of chips your opponent has contributed to the pot

		int minRaise = 0;
		int maxRaise = 200;

		if (legalActions.find(Action::Type::RAISE) != legalActions.end()) {
			auto raiseBounds = roundState->raiseBounds();  // the smallest && largest numbers of chips for a legal bet/raise
			minRaise = raiseBounds[0];          // the cost of a minimum bet/raise
			maxRaise = raiseBounds[1];          // the cost of a maximum bet/raise
		}

		int potTotal = myContribution + oppContribution;        

		if (street == 3 && myPip == 0 && !tracker.done) {
			int preflop_bet = myContribution;
			cout << "Made it to flop" << endl;
			if (we_last_raised) {
				tracker.add_preflop_bets(preflop_bet, preflop_bet, 1);
			} else {
				tracker.add_preflop_bets(preflop_bet, preflop_bet, 0);
			}
			tracker.done = true;
		}


		const int MC_ITERS = 1000;
		pair<int,int> myHand = toHand(myCards);
		double strength = calcStrength(myHand, MC_ITERS, board);

		// CALCULATE RAISE SIZING
		double ratio = 0.7; // pot bet ratio postflop

		int raiseAmount = 0;
		if (street < 3) {
			if (oppContribution <= 2) {
				raiseAmount = 4 * oppContribution;
			} else if (oppContribution <= 12) {
				raiseAmount = 4 * oppContribution;
			} else if (oppContribution <= 40) {
				raiseAmount = 5 * oppContribution / 2;
			} else {
				raiseAmount = 200;
			}
		} else {
			raiseAmount = (int)(ratio * (potTotal + continueCost) + myPip + continueCost);
		}
		// ensure raises are legal
		raiseAmount = max(raiseAmount, minRaise);
		raiseAmount = min(raiseAmount, maxRaise);

		if (oppContribution > 100) {
			will_bluff = false;
		}

		Action my_action, jam_action, aggro_action, flat_action, passive_action;

		// jam action
		if (legalActions.count(Action::Type::RAISE)) {
            jam_action = Action(Action::Type::RAISE, maxRaise);
        } else if (legalActions.count(Action::Type::CALL)) {
            jam_action = Action(Action::Type::CALL);
        } else {
            jam_action = Action(Action::Type::CHECK);
		}
		
		// aggro action raise
		if (legalActions.count(Action::Type::RAISE)) {
            aggro_action = Action(Action::Type::RAISE, raiseAmount);
        } else if (legalActions.count(Action::Type::CALL)) {
            aggro_action = Action(Action::Type::CALL);
        } else {
            aggro_action = Action(Action::Type::CHECK);
		}

		// flat action
		if (legalActions.count(Action::Type::CALL)) {
            flat_action = Action(Action::Type::CALL);
        } else {
            flat_action = Action(Action::Type::CHECK);
		}

		// passive action
		if (legalActions.count(Action::Type::CHECK)) {
            passive_action = Action(Action::Type::CHECK);
        } else {
            passive_action = Action(Action::Type::FOLD);
		}

		if (guaranteed_win) {
			return passive_action;
		}

		if (myContribution > max_loss && -oppContribution <= max_loss) {
			return jam_action;
		}

		if (myContribution - myPip + raiseAmount > max_loss && -oppContribution <= max_loss) {
            aggro_action = jam_action;
		}
            
        if (myContribution + continueCost > max_loss && -oppContribution <= max_loss) {
            flat_action = jam_action;
		}


		// PREFLOP CASEWORK
		if (street < 3) {
			Action my_action;
			if (myContribution > 2 && continueCost <= myContribution) {
				passive_action = flat_action;
			}
			double rev_percentile = 100.0 - getPreflopPercentile(myHand);
			rev_percentile = max(rev_percentile, 0.0);
			last_raised = false;
			if (!bigBlind) {
				// small blind
				if (continueCost == 1) {
					if (rev_percentile < open_cutoff) {
						last_raised = true;
						my_action = aggro_action;
					} else {
						my_action = passive_action;
					}
				} else if (oppContribution <= 50) {
					if (rev_percentile < open_reraise) {
						last_raised = true;
						my_action = aggro_action;
					} else if (rev_percentile < open_defend) {
						my_action = flat_action;
					} else {
						my_action = passive_action;
					}
				} else {
					if (rev_percentile < preflop_allin) {
						last_raised = true;
						my_action = jam_action;
					} else if (rev_percentile < open_redefend) {
						my_action = flat_action;
					} else {
						my_action = passive_action;
					}
				}
			} else {
				// big blind
				if (continueCost == 0) {
					if (rev_percentile < bb_limpraise) {
						last_raised = true;
						my_action = aggro_action;
					} else {
						my_action = flat_action;
					}
				} else if (oppContribution <= 20) {
					if (rev_percentile < bb_reraise) {
						last_raised = true;
						my_action = aggro_action;
					} else if (rev_percentile < bb_defend) {
						my_action = flat_action;
					} else {
						my_action = passive_action;
					}
				} else {
					if (rev_percentile < preflop_allin) {
						last_raised = true;
						my_action = jam_action;
					} else if (rev_percentile < bb_redefend) {
						my_action = flat_action;
					} else {
						my_action = passive_action;
					}
				}
			}
			if (my_action.actionType == Action::Type::RAISE) {
				we_last_raised = true;
			} else {
				we_last_raised = false;
			}
			return my_action;
		}

		// POSTFLOP PLAY FROM HERE
		double out_of_range, reraise_cutoff, lead_cutoff, cbet_cutoff;
        if (street == 3) {
			out_of_range = 0.15;
			reraise_cutoff = 0.8;
			lead_cutoff = 0.4;
			cbet_cutoff = 0.25;
		} else if (street == 4) {
			out_of_range = 0.2;
			reraise_cutoff = 0.825;
			lead_cutoff = 0.45;
			cbet_cutoff = 0.3;
		} else {
			out_of_range = 0.25;
			reraise_cutoff = 0.85;
			lead_cutoff = 0.5;
			cbet_cutoff = 0.35;
		}

		if (continueCost > 0) {
			num_raises += min(4.0, (double)continueCost / (double)myContribution);
		}
		double scared_strength = strength;
		for (int i=0;i<(int)num_raises;i++) {
			scared_strength = (scared_strength - out_of_range)/(1.0 - out_of_range);
		}
		scared_strength = max(0.1, scared_strength);

		double multiplier = 1.0;
		if (street == 3) {
			multiplier = flop_multiplier;
		} else if (street == 4) {
			multiplier = turn_multiplier;
		} else {
			multiplier = river_multiplier;
		}


		if (continueCost > 0) {
			double pot_odds = (double)continueCost / (double)(potTotal + continueCost);
            if (scared_strength * multiplier >= pot_odds) { // nonnegative EV decision
                if (street == 3)
                    flop_call = true;
                if (street == 4)
                    turn_call = true;
                if (street == 5)
                    river_call = true;
                if (scared_strength * multiplier > reraise_cutoff) {
                    my_action = aggro_action;
                    did_raise = true;
                    num_raises += 1.4;
				} else {
                    my_action = flat_action;
				}
			} else if (randomReal() < bluff_raise && will_bluff && myPip == 0) { // bluff
                my_action = aggro_action;
                did_raise = true;
                num_raises += 1.4;
			} else { // negative EV
                my_action = passive_action;
			}
		} else {
			if (bigBlind) {
                // First to act
                if (scared_strength > lead_cutoff && randomReal() < scared_strength) {
                    my_action = aggro_action;
                    num_raises += 1.4;
                    did_lead = true;
                } else if (scared_strength < lead_cutoff && randomReal() < lead_bluff && will_bluff) {
                    my_action = aggro_action;
                    num_raises += 1.4;
                    did_lead = true;
				} else {
                    my_action = flat_action;
				}
			} else {
                // Opp checks to us
                if (scared_strength > cbet_cutoff && randomReal() < scared_strength) {
                    my_action = aggro_action;
                    num_raises += 1.4;
                    did_cbet = true;
                } else if (scared_strength < cbet_cutoff && randomReal() < cbet_bluff && will_bluff) {
                    my_action = aggro_action;
                    num_raises += 1.4;
                    did_cbet = true;
				} else {
                    my_action = flat_action;
				}
			}
		}
		return my_action;
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
