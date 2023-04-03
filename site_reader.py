from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from enum import Enum
from dataclasses import dataclass
from json import load
from typing import Callable, List, Tuple, Iterable, Optional, Dict, overload
from collections import Counter
from itertools import product
import logging
import numpy as np
from copy import deepcopy
from tqdm import tqdm
from random import choices, choice


WEBDRIVER_PATH = r"webdriver\chromedriver.exe"


class Feedback(Enum):
    ABSENT = 0
    PRESENT = 1
    CORRECT = 2
    EMPTY = 3

    @classmethod
    def from_str(cls, feedback: str) -> 'Feedback':
        return cls[feedback.upper()]


@dataclass(frozen=True)
class LetterInfo:
    letter: str
    feedback: Feedback


@dataclass
class WordInfo:
    letters: Tuple[LetterInfo, ...]

    def __init__(self, letters: Iterable[LetterInfo]):
        self.letters = tuple(letters)

    def __str__(self):
        pretty_chars = []

        for letter in self.letters:
            if letter.feedback == Feedback.CORRECT:
                pretty_chars.append(letter.letter.upper())
            elif letter.feedback == Feedback.ABSENT:
                pretty_chars.append("~")
            else:
                pretty_chars.append(letter.letter.lower())

        return "".join(pretty_chars)

    def __iter__(self):
        return iter(self.letters)

    def __len__(self):
        return len(self.letters)

    def __getitem__(self, index):
        return self.letters[index]

    @staticmethod
    def from_word(word: str, feedback: str) -> 'WordInfo':
        letter_info = []

        for letter, letter_status in zip(word, feedback):
            if letter_status == "2":
                letter_info.append(LetterInfo(letter, Feedback.CORRECT))
            elif letter_status == "1":
                letter_info.append(LetterInfo(letter, Feedback.PRESENT))
            else:
                letter_info.append(LetterInfo(letter, Feedback.ABSENT))

        return WordInfo(letter_info)


class WordleReader:

    WORDLE_URL = r"https://www.nytimes.com/games/wordle/index.html"

    POPUP_SELECTOR = (By.XPATH, r"//div[contains(@class, 'Modal')]")
    CLOSE_POPUP_SELECTOR = (By.XPATH, r".//button[@aria-label='Close']")

    ROW_SELECTOR = (By.XPATH, r"//div[contains(@aria-label,'Row')]")
    LETTER_SELECTOR = (By.XPATH, r".//div[@aria-roledescription='tile']")

    def __init__(self, driver: Optional[webdriver.Chrome] = None):
        if driver is None:
            self.driver = webdriver.Chrome(service=Service(WEBDRIVER_PATH))
        else:
            self.driver = driver

    def __enter__(self):
        self.navigate_to_wordle()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.driver.__exit__(exc_type, exc_value, traceback)

    def navigate_to_wordle(self):
        logging.info("Navigating to Wordle website...")
        self.driver.get(self.WORDLE_URL)
        self.close_popup()

    def close_popup(self):
        if self.is_popup_shown():
            self.driver.find_element(
                *WordleReader.CLOSE_POPUP_SELECTOR).click()
            WebDriverWait(self.driver, 10).until(
                lambda _: not self.is_popup_shown())

    def is_popup_shown(self) -> bool:
        return len(self.driver.find_elements(*WordleReader.POPUP_SELECTOR)) > 0

    def get_word_feedback(self) -> List[WordInfo]:
        word_feedback = []

        word_rows = self.driver.find_elements(*WordleReader.ROW_SELECTOR)

        for row in word_rows:
            letters = row.find_elements(*WordleReader.LETTER_SELECTOR)
            if any(letter.get_attribute("data-state") == "empty" for letter in letters):
                break

            row_feedbacks = (feedback.get_attribute("data-state")
                             for feedback in letters)
            row_letters = (letter.text for letter in letters)

            word_feedback.append(WordInfo(LetterInfo(letter, Feedback.from_str(
                feedback)) for letter, feedback in zip(row_letters, row_feedbacks)))

        return word_feedback

    def get_newest_feedback(self) -> WordInfo:
        word_feedback = self.get_word_feedback()
        return word_feedback[-1]

    def input_guess(self, guess: str):
        logging.info(f"Guessing {guess}")
        initial_feedback_len = len(self.get_word_feedback())
        next_row_element = self.driver.find_elements(
            *WordleReader.ROW_SELECTOR)[initial_feedback_len]

        guess_input = self.driver.find_element(By.XPATH, r"//body")
        guess_input.send_keys(guess)
        guess_input.send_keys("\n")

        # Wait for the letter animation to finish
        WebDriverWait(self.driver, 10).until(lambda _: all(
            letter.get_attribute("data-animation") == "idle"
            for letter in next_row_element.find_elements(*WordleReader.LETTER_SELECTOR))
        )


class WordDict:
    def __init__(self, word_list_path: str):
        with open(word_list_path) as word_list:
            self.words_list = load(word_list)
            self.words_list.sort()

            self.words = {word: index for index, word in enumerate(self.words_list)}

    def __contains__(self, word: str) -> bool:
        return word in self.words

    def __len__(self) -> int:
        return len(self.words_list)

    def __iter__(self):
        return iter(self.words_list)
    
    @overload
    def __getitem__(self, index: int) -> str:
        ...

    @overload
    def __getitem__(self, index: str) -> int:
        ...

    def __getitem__(self, index: int | str) -> int | str:
        if isinstance(index, str):
            return self.words[index]
        else:
            return self.words_list[index]
        
    def filter_impossible_words(self, feedback: WordInfo) -> None:
        """Filters out all words that cannot generate the given feedback (as implemented in WordleReader.get_word_feedback)."""
        self.words_list = [word for word in self.iterate_possible_words(feedback)]
        self.words = {word: self.words[word] for word in self.words_list}

    def iterate_possible_words(self, feedback: WordInfo) -> Iterable[str]:
        feedback_filter = WordDict.make_feedback_filter(feedback)
        return (word for word in self.words if feedback_filter(word))
 
    @staticmethod
    def make_feedback_filter(feedback: WordInfo) -> Callable[[str], bool]:
        def word_filter(answer: str) -> bool:
            """Returns True if answer could generate the given feedback (as implemented in WordleReader.get_word_feedback), and False otherwise."""

            # Keeps track of how many characters haven't been "consumed" yet when matching the feedback.
            unused_feedback_letters = Counter(answer)

            for answer_letter, letter_info in zip(answer, feedback):
                is_same_letter = answer_letter == letter_info.letter

                # If the letter is correct, the two letters at the same index must be the same.
                if letter_info.feedback == Feedback.CORRECT:
                    if not is_same_letter:
                        return False

                    unused_feedback_letters[answer_letter] -= 1

                # If the letter is present or absent, the two letters at the same index must differ
                # (if they were the same, the letter should be "correct" in the if statement above)
                elif is_same_letter:
                    return False

            for letter_info in feedback:
                if letter_info.feedback == Feedback.PRESENT:
                    if unused_feedback_letters[letter_info.letter] <= 0:
                        return False
                    unused_feedback_letters[letter_info.letter] -= 1

            # At this point, since we've removed all the correct and present letters, any letters left
            # in unused_feedback_letters must be absent.
            for letter_info in feedback:
                if letter_info.feedback == Feedback.ABSENT:
                    if unused_feedback_letters[letter_info.letter] > 0:
                        return False

            return True

        return word_filter


class WordleGame:
    @staticmethod
    def generate_full_feedback(guess: str, answer: str) -> WordInfo:
        return WordInfo(LetterInfo(letter, Feedback(feedback)) for letter, feedback in 
                        zip(guess, WordleGame.generate_feedback(guess, answer)))
    
    @staticmethod
    def generate_feedback(guess: str, answer: str) -> List[Feedback]:
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
        self.all_words = word_dict
        self.remaining_possible_answers = deepcopy(word_dict)
        self.feedback_matrix = self.initialize_feedback_matrix(word_dict, load_matrix_path, save_matrix_path)

        logging.info("Performing self-test on feedback matrix...")
        if not all(self.matrix_self_test() for _ in range(3)):
            raise ValueError("Feedback matrix does not match inputted word lists")
        
        logging.info("Self-test completed successfully")

    def initialize_feedback_matrix(self, word_dict: WordDict, load_path: Optional[str] = None, save_path: Optional[str] = None):
        # Feedback matrix is a 2D array with both axes being the word_dict words. It stores the cached feedback for each pair of words.
        # The feedback is stored as an integer in base 3 (0 = absent, 1 = present, 2 = correct) for maximal space efficiency.
        # i.e. "Absent, Absent, Present, Correct" is stored as base 3 integer 0012 (which is 5 in base 10)
        if load_path is not None:
            logging.info(f"Loading precomputed matrix from '{load_path}'...")
            return np.load(load_path)

        logging.info("Generating feedback matrix (this may take a while)...")
        return self.generate_feedback_matrix(word_dict, save_path)

    def generate_feedback_matrix(self, word_dict: WordDict, save_path: Optional[str] = None):
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
            
    def gen_matrix_cell(self, guess, answer):
        feedback = WordleGame.generate_feedback(guess, answer)
        return self.feedback_to_base_3(feedback)
    
    def lookup_feedback(self, guess, answer):
        guess_index, answer_index = self.all_words[guess], self.all_words[answer]
        return self.base_3_to_feedback(self.feedback_matrix[guess_index, answer_index], len(guess)) # type: ignore
    
    def create_bin_counts(self):
        # Bin quantity is the number of possible feedbacks for a word of length n
        bin_quantity = 3 ** len(self.all_words[0])

        indexes_of_remaining_guesses = list(self.remaining_possible_answers.words.values())

        return np.apply_along_axis(np.bincount, arr=self.feedback_matrix[:, indexes_of_remaining_guesses], axis=-1, minlength=bin_quantity)
    
    def apply_feedback(self, feedback: WordInfo):
        self.remaining_possible_answers.filter_impossible_words(feedback)

    def get_best_guess(self):
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

    def confidence_in_answer(self):
        return 1 / len(self.remaining_possible_answers)

    def matrix_self_test(self) -> bool:
        """Checks to ensure that the feedback contained in the feedback matrix cooresponds to the actual dictionary.
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

    @staticmethod
    def feedback_to_base_3(feedback: List[Feedback]) -> int:
        # This is very imperative, but it needs to be fast since it's called a lot
        total = 0
        digit_multiplier = 1

        for feedback_digit in reversed(feedback):
            total += feedback_digit.value * digit_multiplier
            digit_multiplier *= 3

        return total
    
    @staticmethod
    def base_3_to_feedback(base_3: int, word_length: int) -> List[Feedback]:
        feedback = []
        while base_3 > 0:
            feedback.append(Feedback(base_3 % 3))
            base_3 //= 3

        while len(feedback) < word_length:
            feedback.append(Feedback.ABSENT)

        return list(reversed(feedback))
