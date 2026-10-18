"""
Solver for a hidden code of a KNOWN length (3 or 4 cards/digits), each
digit 1-10, repeats allowed. Feedback after each guess is simply the
raw count of correct positions (e.g. "2" out of 4 -- not a percentage).

Usage:
    python code_solver.py
    (it will ask how many cards, then solve)

Strategy: at each step, pick the guess (from the full space of possible
codes) that minimizes the worst-case number of remaining candidates,
no matter what feedback comes back -- a standard minimax approach.
"""

import itertools
import numpy as np

DIGITS = list(range(1, 11))
NUM_DIGITS = len(DIGITS)


def build_candidates(length):
    return list(itertools.product(DIGITS, repeat=length))


def onehot(codes, length):
    arr = np.zeros((len(codes), length * NUM_DIGITS), dtype=np.float32)
    for i, c in enumerate(codes):
        for p, v in enumerate(c):
            arr[i, p * NUM_DIGITS + (v - 1)] = 1
    return arr


def best_guess(candidates, A_cand, length):
    """Minimax: pick the candidate-as-guess minimizing the worst-case
    bucket size across all possible feedback values (0..length correct)."""
    M = np.round(A_cand @ A_cand.T).astype(np.int32)  # matches[i, j]
    best_idx, best_worst = None, None
    for i in range(len(candidates)):
        counts = np.bincount(M[i], minlength=length + 1)
        worst = int(counts.max())
        if best_worst is None or worst < best_worst:
            best_worst, best_idx = worst, i
    return best_idx, best_worst, M[best_idx]


def solve_interactive():
    while True:
        raw_len = input("How many cards? ").strip()
        if raw_len in ("3", "4"):
            length = int(raw_len)
            break
        print("Please enter 3 or 4.")

    candidates = build_candidates(length)
    guess_num = 0

    while True:
        guess_num += 1
        n = len(candidates)

        if n == 1:
            guess = candidates[0]
        else:
            A_cand = onehot(candidates, length)
            idx, worst, _ = best_guess(candidates, A_cand, length)
            guess = candidates[idx]

        print(f"\nGuess {guess_num}: {'-'.join(map(str, guess))}")

        if n == 1:
            print("(This should be the answer.)")

        while True:
            raw = input(f"How many correct, out of {length}? ").strip()
            if raw.isdigit() and 0 <= int(raw) <= length:
                m = int(raw)
                break
            print(f"Please enter a whole number from 0 to {length}.")

        if m == length:
            print(f"\nSolved in {guess_num} guesses! Code = {'-'.join(map(str, guess))}")
            return guess

        A_cand = onehot(candidates, length)
        A_guess = onehot([guess], length)
        matches_row = np.round((A_guess @ A_cand.T)).astype(np.int32)[0]
        candidates = [c for c, mm in zip(candidates, matches_row) if mm == m]

        if not candidates:
            print("No candidates match that feedback -- double check the number you entered.")
            return None

        print(f"{len(candidates)} candidate code(s) remain.")


if __name__ == "__main__":
    solve_interactive()
