from dyswaps import Solver, WordDict, Feedback, WordInfo, LetterInfo, WordleInteractor

import logging
import pathlib

GUESS_ATTEMPTS = 6
WORDS_JSON_PATH = r"words\words.json"
FEEDBACK_MATRIX_PATH = r"words\feedback_matrix.npy"
CHROME_WEBDRIVER_DRIVER_PATH = r"webdriver\chromedriver.exe"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    word_dict = WordDict.from_json(WORDS_JSON_PATH)

    # Load feedback matrix from file if it exists at `FEEDBACK_MATRIX_PATH`, otherwise create a new one and save it to that path.
    if pathlib.Path(FEEDBACK_MATRIX_PATH).exists():
        solver = Solver(word_dict, load_matrix_path=FEEDBACK_MATRIX_PATH)
    else:
        solver = Solver(word_dict, save_matrix_path=FEEDBACK_MATRIX_PATH)

    with WordleInteractor(webdriver_path=CHROME_WEBDRIVER_DRIVER_PATH) as site_reader:
        for guess_count in range(GUESS_ATTEMPTS):
            optimal_guess = solver.get_best_guess()

            print(f"Entering optimal guess: '{optimal_guess}'\nRemaining possible answers: {len(solver.remaining_possible_answers)}")
            site_reader.input_guess(optimal_guess)

            feedback = site_reader.get_newest_feedback()

            print(f"Feedback: {feedback}")

            solver.apply_feedback(feedback)

            if feedback == WordInfo([LetterInfo(letter, Feedback.CORRECT) for letter in optimal_guess]):
                print(f"Guessed word correctly in {guess_count + 1} guesses: '{optimal_guess}'")
                break

        else:
            print(f"Failed to guess word correctly within {GUESS_ATTEMPTS} attempts")
