from dyswaps import Solver, WordDict, Feedback, WordInfo, LetterInfo, WordleReader

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

    with WordleReader(webdriver_path=r"webdriver\chromedriver.exe") as site_reader:
        for guess_num in range(6):
            optimal_guess = solver.get_best_guess()

            print(f"Entering optimal guess: '{optimal_guess}'\nRemaining possible answers: {len(solver.remaining_possible_answers)}")
            site_reader.input_guess(optimal_guess)

            feedback = site_reader.get_newest_feedback()

            print(f"Feedback: {feedback}")

            solver.apply_feedback(feedback)

            if feedback == WordInfo([LetterInfo(letter, Feedback.CORRECT) for letter in optimal_guess]):
                print(f"Guessed word correctly: '{optimal_guess}'")
                break

        else:
            print("Failed to guess word correctly within 6 attempts")
