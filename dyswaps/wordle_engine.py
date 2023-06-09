from .wordle_state_entities import Feedback, WordInfo, LetterInfo, WordDict

from typing import List, Optional
from itertools import product
from copy import deepcopy
from tqdm import tqdm
from random import choices

import logging
import numpy as np


class WordleGame:
    @staticmethod
    def generate_full_feedback(guess: str, answer: str) -> WordInfo:
        """Generates a `WordInfo` object containing the feedback that would be given to a player if they guessed `guess` for the answer `answer`."""

        return WordInfo(LetterInfo(letter, Feedback(feedback)) for letter, feedback in 
                        zip(guess, WordleGame.generate_feedback(guess, answer)))
    
    @staticmethod
    def generate_feedback(guess: str, answer: str) -> List[Feedback]:
        """Generates the feedback that would be given to a player if they guessed `guess` for the answer `answer`.

        Only returns the feedback statuses (i.e. `Feedback.CORRECT`, `Feedback.PRESENT`, `Feedback.ABSENT`) and not the actual letters (see `generate_full_feedback` if letters must be included)."""

        unused_feedback_letters = list(answer)
        feedback = [Feedback.EMPTY] * len(answer)

        # Calculate CORRECT feedback
        for i, (answer_letter, guess_letter) in enumerate(zip(answer, guess)):
            if answer_letter == guess_letter:
                feedback[i] = Feedback.CORRECT
                unused_feedback_letters.remove(answer_letter)

        # Calculate PRESENT and ABSENT feedback
        for i, guess_letter in enumerate(guess):
            if feedback[i] is not Feedback.EMPTY:
                continue

            if guess_letter in unused_feedback_letters:
                feedback[i] = Feedback.PRESENT
                unused_feedback_letters.remove(guess_letter)
            else:
                feedback[i] = Feedback.ABSENT

        return feedback


class Solver:
    def __init__(self, word_dict: WordDict, load_matrix_path: Optional[str] = None, save_matrix_path: Optional[str] = None):
        """Initializes the solver with the given word dictionary and either loads the feedback matrix from `load_matrix_path` or generates it from `word_dict` and saves it to `save_matrix_path` if it is not None."""

        self.all_words = word_dict
        self.remaining_possible_answers = deepcopy(word_dict)
        self.feedback_matrix = self.initialize_feedback_matrix(word_dict, load_matrix_path, save_matrix_path)

        logging.info("Performing self-test on feedback matrix...")
        
        if not all(self.matrix_self_test() for _ in range(3)):
            raise ValueError("Feedback matrix does not match inputted word lists")
        
        logging.info("Self-test completed successfully")

    def initialize_feedback_matrix(self, word_dict: WordDict, load_path: Optional[str] = None, save_path: Optional[str] = None):
        """Initializes the feedback matrix by either loading it from `load_path` or generating it from `word_dict` and saving it to `save_path` if it is not None.
        
        If both `load_path` and `save_path` are None, the feedback matrix is only saved in memory (not recommended since this operation is very expensive)."""

        # Feedback matrix is a 2D array with both axes being the word_dict words. It stores the cached feedback for each pair of words.
        # The feedback is stored as an integer in base 3 (0 = absent, 1 = present, 2 = correct) for maximal space efficiency.
        # i.e. "Absent, Absent, Present, Correct" is stored as base 3 integer 0012 (which is 5 in base 10)
        if load_path is not None:
            logging.info(f"Loading precomputed matrix from '{load_path}'...")
            return np.load(load_path)

        logging.info("Generating feedback matrix (this may take a while)...")
        return self.generate_feedback_matrix(word_dict, save_path)

    def generate_feedback_matrix(self, word_dict: WordDict, save_path: Optional[str] = None):
        """Generates a feedback matrix for the given `word_dict` and saves it to `save_path` if it is not None."""

        # This method is extremely expensive, (I should probably implement it in C/Rust down the line)
        # so I added a progress bar so it's obvious that it's doing something
        feedback_matrix = np.zeros((len(word_dict), len(word_dict)), dtype=np.uint16)

        progress = tqdm(product(word_dict.words.items(), repeat=2),
                total=len(word_dict) ** 2,
                desc="Generating feedback matrix")

        for (guess, guess_index), (answer, answer_index) in progress:
            feedback_matrix[guess_index, answer_index] = self.gen_matrix_cell(guess, answer)

        if save_path is not None:
            np.save(save_path, feedback_matrix)
        
        return feedback_matrix
    
    def lookup_feedback(self, guess: str, answer: str):
        """Returns the feedback for the given `guess` and `answer` using the feedback matrix."""

        guess_index, answer_index = self.all_words[guess], self.all_words[answer]
        return self.base_3_to_feedback(self.feedback_matrix[guess_index, answer_index], len(guess)) # type: ignore
    
    def create_bin_counts(self):
        """Creates a 2D array where each row is a possible guess and each column is a count of the number of possible answers for each feedback type."""

        # Bin quantity is the number of possible feedbacks for a word of length n
        bin_quantity = 3 ** len(self.all_words[0])

        indexes_of_remaining_guesses = [self.all_words[word] for word in self.remaining_possible_answers.words_list]

        return np.apply_along_axis(np.bincount, arr=self.feedback_matrix[:, indexes_of_remaining_guesses], axis=-1, minlength=bin_quantity)
    
    def apply_feedback(self, feedback: WordInfo):
        """Removes all words which are not possible based on the given `WordInfo`."""

        self.remaining_possible_answers.filter_impossible_words(feedback)

    def get_best_guess(self) -> str:
        """Returns the best guess for the next word based on the words that are still possible."""

        probabilities = self.create_bin_counts() / len(self.remaining_possible_answers)
        # Create a masked array where zero values are masked
        masked_probabilities = np.ma.masked_equal(probabilities, 0)
        
        # Calculate the entropy_distribution using the masked array
        entropy_distribution = -np.ma.log2(masked_probabilities).filled(0)
        
        entropy_sums = np.sum(entropy_distribution, axis=-1)

        # Returns a list of the indexes with the highest entropy sums
        best_guess_indexes = np.argwhere(entropy_sums == np.max(entropy_sums)).flatten()

        # If there are multiple best guesses, check to see if any of them are in the remaining possible answers and guess that
        # Otherwise, just guess a random one
        # TODO: create a more advanced heuristic for when there are multiple guesses with the same entropy sum, e.g. see which pattern would eliminate the most words
        for best_guess_index in best_guess_indexes:
            if self.all_words[best_guess_index] in self.remaining_possible_answers:
                return self.all_words[best_guess_index]

        return self.all_words[np.random.choice(best_guess_indexes)]

    def confidence_in_answer(self) -> float:
        """Returns a float between 0 and 1 representing the confidence in the next answer. 0 means no confidence, 1 means 100% confidence."""

        if len(self.remaining_possible_answers) == 0:
            return 0.0
        return 1 / len(self.remaining_possible_answers)

    def matrix_self_test(self) -> bool:
        """Checks to ensure that the feedback contained in the feedback matrix cooresponds with the data in `word_dict`.
        Does this by comparing every word to one other random word, and checking that the feedback is the same."""
        
        if self.feedback_matrix.shape != (len(self.all_words), len(self.all_words)):
            logging.error(f"Feedback matrix does not have the correct shape (expected: {(len(self.all_words), len(self.all_words))}, got: {self.feedback_matrix.shape})")
            return False

        random_word_samples = choices(self.all_words, k=len(self.all_words))

        if not all(self.lookup_feedback(guess, answer) == WordleGame.generate_feedback(guess, answer)
                   for guess, answer
                   in zip(self.all_words, random_word_samples)):
            logging.error("Feedback matrix feedback does not match inputted word list, please regenerate the feedback matrix")
            return False
        
        return True

    @classmethod        
    def gen_matrix_cell(cls, guess, answer):
        """Generates a single cell for the feedback matrix, represented as a base 3 number."""

        feedback = WordleGame.generate_feedback(guess, answer)
        return cls.feedback_to_base_3(feedback)

    @staticmethod
    def feedback_to_base_3(feedback: List[Feedback] | WordInfo) -> int:
        """Converts a list of `Feedback` or a `WordInfo` object to a base 3 number.
        
        `0` represents `Feedback.ABSENT`, `1` represents `Feedback.PRESENT`, and `2` represents `Feedback.CORRECT` in base 3."""

        if isinstance(feedback, WordInfo):
            feedback = [letter_info.feedback for letter_info in feedback]

        # This is very imperative/ugly, but it needs to be fast since it's called a lot
        total = 0
        digit_multiplier = 1

        for feedback_digit in reversed(feedback):
            total += feedback_digit.value * digit_multiplier
            digit_multiplier *= 3

        return total
    
    @staticmethod
    def base_3_to_feedback(base_3: int, word_length: int) -> List[Feedback]:
        """Converts a base 3 number to a list of `Feedback` objects according to `Solver.feedback_to_base_3`."""

        feedback = []
        while base_3 > 0:
            feedback.append(Feedback(base_3 % 3))
            base_3 //= 3

        while len(feedback) < word_length:
            feedback.append(Feedback.ABSENT)

        return list(reversed(feedback))
