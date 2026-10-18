"""
Card-code solver that minimizes the WORST-CASE number of cards spent.

Rules it assumes
  - The code has 3 or 4 cards, each a number 1-10, repeats allowed.
  - A guess is a PREFIX of the code: the first k cards (k = 1..length).
    Submitting k cards costs k cards.
  - Feedback is how many of the k submitted cards are correct.
  - You win by submitting the full code with everything correct.

Strategy (a hybrid)
  1. While many candidate codes remain (more than THRESHOLD), submit full
     guesses chosen to shrink the largest feedback group as much as possible.
  2. Once THRESHOLD or fewer remain, search EXACTLY over every prefix guess
     for the lowest worst-case card cost (ties broken by lowest average
     cost). Cheap 1- and 2-card probes show up here, mostly at the end.

Measured on the real game (10 numbers, 3 cards), walking the whole decision
tree: worst case 33 cards, average 25.61 (the full-guess-only strategy was
36 and 26.93).

Usage:  python code_solver.py
"""

import itertools
import numpy as np

DIGITS = list(range(1, 11))
NUM = len(DIGITS)
THRESHOLD = 15


def onehot(codes, L):
    arr = np.zeros((len(codes), L * NUM), dtype=np.float32)
    for i, c in enumerate(codes):
        for p, v in enumerate(c):
            arr[i, p * NUM + (int(v) - 1)] = 1
    return arr


class Solver:
    def __init__(self, L, threshold=THRESHOLD):
        self.L = L
        self.T = threshold
        self.cands = np.array(list(itertools.product(DIGITS, repeat=L)), dtype=np.int16)
        self.C = onehot(self.cands, L)
        self.memo = {}

    # ---------- feedback ----------
    def matches(self, guess, S):
        """Correct cards among the submitted prefix, for each candidate in S."""
        k = len(guess)
        m = np.zeros(len(S), dtype=np.int8)
        for p in range(k):
            m += (self.cands[S, p] == guess[p])
        return m

    # ---------- phase 1: full guesses, shrink the largest group ----------
    def full_minimax(self, S):
        L = self.L
        if len(S) == len(self.cands):          # first move: every guess is equivalent
            return (1,) * L
        CS = self.C[S]
        worst = np.empty(len(S), dtype=np.int64)
        for a in range(0, len(S), 1500):
            M = np.rint(CS[a:a + 1500] @ CS.T).astype(np.int8)
            counts = np.stack([(M == f).sum(axis=1) for f in range(L + 1)], axis=1)
            worst[a:a + 1500] = counts.max(axis=1)
        return tuple(int(x) for x in self.cands[S[int(np.argmin(worst))]])

    # ---------- phase 2: exact search over all prefix guesses ----------
    def _pool(self, Cs):
        """All prefix guesses built from digits that appear among the remaining
        candidates, plus one filler digit that can never match."""
        L = self.L
        opts = []
        for p in range(L):
            present = sorted(set(Cs[:, p].tolist()))
            absent = [d for d in DIGITS if d not in present]
            opts.append(present + absent[:1])
        Mp = [np.array([(Cs[:, p] == d) for d in opts[p]], dtype=np.int8) for p in range(L)]
        rows, digs, costs = [], [], []
        cur, cur_d = Mp[0], [(d,) for d in opts[0]]
        rows.append(cur); digs += cur_d; costs += [1] * len(cur_d)
        for p in range(1, L):
            nxt = (cur[:, None, :] + Mp[p][None, :, :]).reshape(-1, Cs.shape[0])
            nxt_d = [t + (d,) for t in cur_d for d in opts[p]]
            rows.append(nxt); digs += nxt_d; costs += [p + 1] * len(nxt_d)
            cur, cur_d = nxt, nxt_d
        return np.concatenate(rows, axis=0), digs, np.array(costs)

    def solve(self, S):
        """Returns (worst-case cards, total cards over all codes in S, best guess)."""
        L = self.L
        if len(S) == 1:
            return (L, L, tuple(int(x) for x in self.cands[S[0]]))
        key = tuple(S.tolist())
        if key in self.memo:
            return self.memo[key]
        sub, digs, costs = self._pool(self.cands[S])
        cnt = np.stack([(sub == f).sum(axis=1) for f in range(L + 1)], axis=1)
        maxb = cnt.max(axis=1)
        valid = np.where(maxb < len(S))[0]
        order = valid[np.lexsort((costs[valid], maxb[valid]))]
        best = (10 ** 9, 10 ** 9, None)
        seen = set()
        for gi in order:
            k = int(costs[gi])
            if k + L > best[0]:
                continue
            row = sub[gi]
            sig = row.tobytes() + bytes([k])
            if sig in seen:
                continue
            seen.add(sig)
            worst, total, ok = 0, 0, True
            for f in range(L + 1):
                mask = row == f
                n = int(mask.sum())
                if n == 0:
                    continue
                if k == L and f == L:           # exact code: game over
                    total += k
                    continue
                w, t, _ = self.solve(S[mask])
                worst = max(worst, w)
                total += k * n + t
                if k + worst > best[0]:
                    ok = False
                    break
            if ok and (k + worst, total) < (best[0], best[1]):
                best = (k + worst, total, tuple(digs[gi]))
        self.memo[key] = best
        return best

    # ---------- choose the next guess ----------
    def pick(self, S):
        if len(S) == 1:
            return tuple(int(x) for x in self.cands[S[0]])
        if len(S) <= self.T:
            return self.solve(S)[2]
        return self.full_minimax(S)


def play(L, ask, say=print):
    """Run one game. ask(guess) must return how many submitted cards were correct."""
    solver = Solver(L)
    S = np.arange(len(solver.cands))
    spent, turn = 0, 0
    while True:
        turn += 1
        guess = solver.pick(S)
        k = len(guess)
        spent += k
        shown = "-".join(map(str, guess))
        if k == L:
            say(f"\nGuess {turn}: submit all {L} cards: {shown}   (costs {k})")
        else:
            say(f"\nGuess {turn}: submit only the first {k} card{'s' if k > 1 else ''}: {shown}   (costs {k})")
        m = ask(guess)
        if k == L and m == L:
            say(f"\nSolved in {turn} guesses, spending {spent} cards. Code = {shown}")
            return spent
        S = S[solver.matches(guess, S) == m]
        if len(S) == 0:
            say("No code fits those answers -- one of the numbers you entered was probably wrong.")
            return None
        say(f"{len(S)} possible code(s) remain.")


def main():
    while True:
        raw = input("How many cards? ").strip()
        if raw in ("3", "4"):
            L = int(raw)
            break
        print("Please enter 3 or 4.")

    def ask(guess):
        k = len(guess)
        while True:
            raw = input(f"How many correct, out of {k}? ").strip()
            if raw.isdigit() and 0 <= int(raw) <= k:
                return int(raw)
            print(f"Please enter a whole number from 0 to {k}.")

    play(L, ask)


if __name__ == "__main__":
    main()
