
#include "omp/HandEvaluator.h"
#include "omp/EquityCalculator.h"
#include "omp/Random.h"
#include "ttest/ttest.h"
#include <iostream>
#include <unordered_set>
#include <unordered_map>
#include <vector>
#include <list>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;
using namespace omp;


int ITERS = 200;

auto seed = chrono::system_clock::now().time_since_epoch().count();
mt19937 rng(seed);
uniform_real_distribution<double> u(0.0,1.0);

double equity_against(int h1, int h2, int h3, int h4) {
    HandEvaluator eval;
    vector<int> deck;
    for (int i=0;i<52;i++) {
        if (i!=h1 && i!=h2 && i!=h3 && i!=h4) deck.push_back(i);
    }
    double score = 0;
    for (int kk=0;kk<ITERS;kk++) {
        shuffle(deck.begin(), deck.end(), rng);

        int nh1=h1;
        int nh2=h2;
        int nh3=h3;
        int nh4=h4;
        
        int cur=5;
        if (u(rng) < 0.145) nh1 = deck[cur++];
        if (u(rng) < 0.145) nh2 = deck[cur++];
        if (u(rng) < 0.145) nh3 = deck[cur++];
        if (u(rng) < 0.145) nh4 = deck[cur++];

        Hand ourHand = Hand::empty();
        ourHand += Hand(nh1) + Hand(nh2);
        for (int i=0;i<5;i++) ourHand += Hand(deck[i]);

        Hand oppHand = Hand::empty();
        oppHand += Hand(nh3) + Hand(nh4);
        for (int i=0;i<5;i++) oppHand += Hand(deck[i]);

        int ourValue = eval.evaluate(ourHand);
        int oppValue = eval.evaluate(oppHand);

        if (ourValue > oppValue) {
            score += 1.0;
        } else if (ourValue == oppValue) {
            score += 0.5;
        }
    }
    return score/(double)ITERS;
}

double equity_against_random(int h1, int h2) {
    double total=0;
    double cnt=0;
    for (int h3=0;h3<52;h3++) {
        for (int h4=h3+1;h4<52;h4++) {
            if (h3 != h1 && h3 != h2 && h4 != h1 && h4 != h2) {
                total += equity_against(h1,h2,h3,h4);
                cnt += 1.0;
            }
        }
    }
    return total/cnt;
}
int to_hand(int val, int suit) {
    return (val-2) * 4 + suit;
}
int main() {
    // pockets
    for (int x=2;x<=14;x++) {
        printf("%d %d %d %lf\n", x, x, 0, equity_against_random(to_hand(x,0),to_hand(x,1)));
    }
    //off suited
    for (int x=2;x<=14;x++) {
        for (int y=x+1;y<=14;y++) {
            printf("%d %d %d %lf\n", x, y, 0, equity_against_random(to_hand(x,0),to_hand(y,1)));
        }
    }
    //suited
    for (int x=2;x<=14;x++) {
        for (int y=x+1;y<=14;y++) {
            printf("%d %d %d %lf\n", x, y, 1, equity_against_random(to_hand(x,0),to_hand(y,0)));
        }
    }
    // for (int h1=0;h1<52;h1++) {
    //     for (int h2=h1+1;h2<52;h2++) {
    //         printf("%d %d: %lf\n",h1,h2,equity_against_random(h1,h2));
    //     }
    // }
}
