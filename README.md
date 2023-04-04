# DySWAPS

DySWAPS is a small, open-source package which contains functionality to solve [Wordle](https://en.wikipedia.org/wiki/Wordle) puzzles by calculating the optimal guessing strategy based on a provided dictionary of words and the feedback from the game. It does this using information theory and dynamic programming, picking words that maximize the expected information gain from the next guess. Credit to [this](https://www.youtube.com/watch?v=v68zYyaEmEA) video by [Grant Sanderson](https://www.youtube.com/@3blue1brown) for helping me understand the idea behind this strategy.

This package is mostly written as a personal educative project to help me learn more about semantic Python and to get more familiar with the Python package ecosystem, so I would appreciate any feedback or suggestions for improvement (and will continue to improve the package as I learn more).

## Usage

### Dependencies and Installation

DySWAPS has a few dependencies, the biggest of which are `Numpy` and `Selenium`. These can be installed by running the following command in the root directory of this repository:
```
pip install -r "requirements.txt"
```
In addition, you will need to have a web driver installed for Selenium to use. Web driver installation instructions can be found [here](https://www.selenium.dev/documentation/en/webdriver/driver_requirements/). The default web driver used by DySWAPS is `ChromeDriver` (if you only want to pass in the path to the web driver when you create a `WordleInteractor` object), but you can also pass in your own `WebDriver` object to use any configuration you like.

### Getting Started

Below is a list of the main objects which are available in the `dyswaps` package, along with a brief description of their functionality. I'm currently working on adding clearer documentation/docstrings and examples for the future.

*If you prefer to learn by example, you can look at the `solve_daily_wordle.py` script in the root directory of this repository to see basic usage (this file simply solves the daily Wordle puzzle at the [NYT website](https://www.nytimes.com/games/wordle/index.html)).*

* `Feedback`: An `enum` which contains the possible letter feedbacks from the game. `Feedback.EMPTY` is not valid in most contexts and represents a square which does not yet have a letter in it.

    ```python
    from dyswaps import Feedback

    color_to_feedback = {
        "green": Feedback.CORRECT,
        "yellow": Feedback.PRESENT,
        "gray": Feedback.ABSENT,
        "black": Feedback.EMPTY
    }
    ```

* `LetterInfo`: An immutable `dataclass` which holds information about a letter in the Wordle puzzle. The `letter` attribute is a single character string, and the `feedback` attribute is a `Feedback` object.

    ```python
    from dyswaps import LetterInfo

    letter_info = LetterInfo(letter="A", feedback=Feedback.CORRECT)
    ```

* `WordInfo`: Stores multiple `LetterInfo` objects as a tuple. Contains a helper method `from_strings` which takes in a string of letters and a string of digits (`2` for correct, `1` for present, `0` for absent), then returns a `WordInfo` object.

    ```python
    from dyswaps import WordInfo

    word_info_1 = WordInfo((
        LetterInfo(letter="a", feedback=Feedback.CORRECT),
        LetterInfo(letter="b", feedback=Feedback.PRESENT),
        LetterInfo(letter="c", feedback=Feedback.ABSENT)
    ))
    
    word_info_2 = WordInfo.from_strings("abc", "210")
    
    assert word_info_1 == word_info_2
    ```

* `WordDict`: Represents a dictionary of words and provides methods for filtering words based on a given WordInfo feedback. This class has two class methods, `from_json` and `from_txt`, which allow you to create a `WordDict` from a JSON array of strings or newline delimited text file, respectively.

    ```python
    from dyswaps import WordDict

    word_dict = WordDict(["aaaaa", "bbbbb", "ccccc"])
    word_dict_json = WordDict.from_json("path/to/your/json_file.json")
    word_dict_file = WordDict.from_txt("path/to/your/text_file.txt")

    guess_feedback = WordInfo.from_strings("abccc", "00222")

    word_dict.filter_impossible_words(guess_feedback)

    assert word_dict == WordDict(["ccccc"])
    ```

* `WordleGame`: A class containing two static methods for generating the feedback that would be given to a player if they guessed a word for a given answer. The `generate_full_feedback` method generates a `WordInfo` object containing the feedback along with the guessed letters, while the `generate_feedback` method only returns the feedback statuses as a list of `Feedback` objects. (Planning to expand this class to include more functionality in the future.)

    ```python
    from dyswaps import WordleGame

    guess = "apple"
    answer = "apply"

    full_feedback = WordleGame.generate_full_feedback(guess, answer)
    feedback = WordleGame.generate_feedback(guess, answer)

    print(full_feedback)  # WordInfo object containing the feedback and letters
    print(feedback)       # [Feedback.CORRECT, Feedback.CORRECT, Feedback.CORRECT, Feedback.CORRECT, Feedback.ABSENT]
    ```

* `Solver`: A class responsible for finding the best guess for the next word based on the words that are still possible. It initializes with a `WordDict` and a path that either loads a precomputed feedback matrix from a specified file or generates it using the given word dictionary. The solver can apply feedback to filter out impossible words, calculate the confidence in the next answer, and find the best guess based on the remaining possible answers.

    ```python
    from dyswaps import Solver, WordDict

    word_dict = WordDict.from_json("path/to/your/text_file.json")

    # If you want to load a precomputed feedback matrix, use the `load_matrix_path` argument
    solver = Solver(word_dict, save_matrix_path="path/to/save/matrix.npy")

    feedback = WordInfo.from_strings("tares", "00000")
    solver.apply_feedback(feedback)

    best_guess = solver.get_best_guess()
    confidence = solver.confidence_in_answer()

    print(best_guess)  # Best guess based on the remaining possible words
    print(confidence)  # Confidence in the next answer (float between 0 and 1)
    ```

* `WordleInteractor`: A class that provides interaction with the Wordle game on the New York Times website using Selenium WebDriver. It provides basic methods for navigating to the game, closing pop-ups, retrieving feedback for submitted words, and inputting guesses. It implements a context manager, so you can use it with the `with` keyword to automatically close the web driver when you're done. (When using as a context manager, the webpage will automatically be navigated to and pop-ups will be closed.)

    ```python
    from dyswaps import WordleInteractor

    # If you want to use a different web driver, pass in your own WebDriver object using the `driver` argument
    with WordleInteractor(webdriver_path="path/to/web/driver") as interactor:
        best_guess = "tares" # Use a `Solver` to find the actual best guess
        
        interactor.input_guess(best_guess)
        feedback = interactor.get_newest_feedback()
    ```
