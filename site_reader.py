from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from enum import Enum
from dataclasses import dataclass
from json import load
from typing import Callable, List, Tuple, Iterable, Optional, Dict
from collections import Counter
from itertools import combinations, product
import logging
import numpy as np
import pathlib
from copy import deepcopy
from tqdm import tqdm


WEBDRIVER_PATH = r"webdriver/chromedriver.exe"


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
            self.words = {word: index for index, word in enumerate(load(word_list))}

    def __contains__(self, word: str) -> bool:
        return word in self.words

    def __len__(self) -> int:
        return len(self.words)

    def __iter__(self):
        return iter(self.words)

    def apply_feedback(self, feedback: WordInfo):
        self.words = set(self.iterate_possible_words(feedback))

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
    def generate_full_feedback(answer: str, guess: str) -> WordInfo:
        return WordInfo(LetterInfo(letter, Feedback(feedback)) for letter, feedback in 
                        zip(guess, WordleGame.generate_feedback(answer, guess)))
    
    @staticmethod
    def generate_feedback(answer: str, guess: str) -> List[Feedback]:
        unused_feedback_letters = Counter(answer)

        feedback = []

        for answer_letter, guess_letter in zip(answer, guess):
            if answer_letter == guess_letter:
                feedback.append(Feedback.CORRECT)
                unused_feedback_letters[answer_letter] -= 1
            else:
                # None is a placeholder for letters we can't determine feedback for yet
                feedback.append(None)

        for guess_position, letter in enumerate(guess):
            # We can skip letters we've already determined as correct
            if feedback[guess_position] is not None:
                continue

            if unused_feedback_letters[letter] > 0:
                updated_letter_status = Feedback.PRESENT
                unused_feedback_letters[letter] -= 1
            else:
                updated_letter_status = Feedback.ABSENT

            feedback[guess_position] = updated_letter_status

        return feedback


class Solver:
    def __init__(self, word_dict, precomputed_feedback_matrix_path: Optional[str] = None):
        self.all_words = word_dict
        self.remaining_words = deepcopy(word_dict)
        self.feedback_matrix = self.initialize_feedback_matrix(word_dict, precomputed_feedback_matrix_path)

    def initialize_feedback_matrix(self, word_dict, precomputed_feedback_matrix_path: Optional[str] = None):
        if precomputed_feedback_matrix_path is None:
            return self.generate_feedback_matrix(word_dict)
        else:
            return self.load_feedback_matrix(precomputed_feedback_matrix_path)

    def generate_feedback_matrix(self, word_dict):
        # This method is extremely expensive, (I should probably implement it in C/Rust down the line)
        # so I added a progress bar so it's obvious that it's doing something
        feedback_matrix = np.zeros((len(word_dict), len(word_dict)), dtype=np.uint8)

        progress = tqdm(product(word_dict.words.items(), repeat=2),
                        total=len(word_dict) ** 2,
                        desc="Generating feedback matrix")

        for (word1, index1), (word2, index2) in progress:
            feedback = WordleGame.generate_feedback(word1, word2)
            feedback_matrix[index1, index2] = self.feedback_to_base3(feedback)
            

    def load_feedback_matrix(self, precomputed_feedback_matrix_path: str):
        pass
    
    @staticmethod
    def feedback_to_base3(feedback: Iterable[Feedback]) -> int:
        return sum(3 ** index * feedback.value for index, feedback in enumerate(feedback))
    
    @staticmethod
    def base3_to_feedback(base3: int) -> List[Feedback]:
        feedback = []
        while base3 > 0:
            feedback.append(Feedback(base3 % 3))
            base3 //= 3
        return feedback
