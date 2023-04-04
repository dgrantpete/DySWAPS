from dataclasses import dataclass
from enum import Enum
from typing import Callable, Counter, Iterable, Tuple, overload
from json import load


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

    @classmethod
    def from_strings(cls, word: str, feedback: str) -> 'WordInfo':
        letter_info = []

        for letter, letter_status in zip(word, feedback):
            if letter_status == "2":
                letter_info.append(LetterInfo(letter, Feedback.CORRECT))
            elif letter_status == "1":
                letter_info.append(LetterInfo(letter, Feedback.PRESENT))
            elif letter_status == "0":
                letter_info.append(LetterInfo(letter, Feedback.ABSENT))
            else:
                raise ValueError(f"Invalid letter status '{letter_status}', must be '0', '1' or '2'")\
                
        return cls(letter_info)


class WordDict:
    def __init__(self, words: Iterable[str]):
        self.words_list = list(words)
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
        self.words = {word: i for i, word in enumerate(self.words_list)}

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
    
    @classmethod
    def from_json(cls, filename: str) -> 'WordDict':
        with open(filename, "r") as f:
            return cls(load(f))
    
    @classmethod
    def from_txt(cls, filename: str) -> 'WordDict':
        with open(filename, "r") as f:
            return cls(f.read().splitlines())
        