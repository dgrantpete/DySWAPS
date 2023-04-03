from .wordle_state_entities import Feedback, WordInfo, LetterInfo

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from typing import Optional, List

import logging


WEBDRIVER_PATH = r"webdriver\chromedriver.exe"


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
        