from dyswaps import LetterInfo, WordleGame, WordDict, Feedback, WordInfo, Solver


def test_generate_feedback():
    test_answer = "aaabb"
    
    answer_matches_expected = lambda guess, expected_feedback: str(WordInfo(WordleGame.generate_full_feedback(guess, test_answer))) == expected_feedback

    assert answer_matches_expected("aabbb", "AA~BB")
    assert answer_matches_expected("bbaaa", "bbAaa")
    assert answer_matches_expected("abbbb", "A~~BB")
    assert answer_matches_expected("baaaa", "bAAa~")
    assert answer_matches_expected("bbbba", "b~~Ba")
    assert answer_matches_expected("acaca", "A~A~a")

def test_base_3_conversions():
    to_feedback = lambda x: Solver.base_3_to_feedback(x, 5)
    to_base_3 = lambda x: Solver.feedback_to_base_3(x)

    assert to_feedback(0) == [Feedback.ABSENT] * 5
    assert to_feedback(242) == [Feedback.CORRECT] * 5
    assert to_feedback(1) == [Feedback.ABSENT] * 4 + [Feedback.PRESENT]

    assert to_base_3(to_feedback(20)) == 20
    assert to_base_3(to_feedback(242)) == 242
    assert to_base_3(to_feedback(0)) == 0

    assert to_base_3([Feedback.ABSENT] * 5) == 0
    assert to_base_3([Feedback.CORRECT] * 5) == 242
    assert to_base_3([Feedback.ABSENT] * 4 + [Feedback.PRESENT]) == 1

def test_word_info_from_str():
    assert WordInfo.from_word("aabb", "2211") == WordInfo([LetterInfo("a", Feedback.CORRECT), LetterInfo("a", Feedback.CORRECT), LetterInfo("b", Feedback.PRESENT), LetterInfo("b", Feedback.PRESENT)])
    assert WordInfo.from_word("bbba", "0110") == WordInfo([LetterInfo("b", Feedback.ABSENT), LetterInfo("b", Feedback.PRESENT), LetterInfo("b", Feedback.PRESENT), LetterInfo("a", Feedback.ABSENT)])

def test_wordle_game():
    assert WordleGame.generate_full_feedback("aabb", "aaaa") == WordInfo([LetterInfo("a", Feedback.CORRECT), LetterInfo("a", Feedback.CORRECT), LetterInfo("b", Feedback.ABSENT), LetterInfo("b", Feedback.ABSENT)])
    assert WordleGame.generate_full_feedback("aabb", "bbbb") == WordInfo([LetterInfo("a", Feedback.ABSENT), LetterInfo("a", Feedback.ABSENT), LetterInfo("b", Feedback.CORRECT), LetterInfo("b", Feedback.CORRECT)])
    assert WordleGame.generate_full_feedback("aabb", "aabb") == WordInfo([LetterInfo("a", Feedback.CORRECT), LetterInfo("a", Feedback.CORRECT), LetterInfo("b", Feedback.CORRECT), LetterInfo("b", Feedback.CORRECT)])
    assert WordleGame.generate_full_feedback("aabb", "bbaa") == WordInfo([LetterInfo("a", Feedback.PRESENT), LetterInfo("a", Feedback.PRESENT), LetterInfo("b", Feedback.PRESENT), LetterInfo("b", Feedback.PRESENT)])

def test_word_dict():
    word_dict = WordDict(["zzzz", "aabb", "abab", "bbaa", "baba", "abba", "baab"])

    assert "aabb" in word_dict
    assert "abab" in word_dict
    assert "cccc" not in word_dict

    assert word_dict[0] == "aabb"
    assert word_dict[-1] == "zzzz"

    assert word_dict["aabb"] == 0
    assert word_dict["zzzz"] == 6

    word_dict.filter_impossible_words(WordInfo.from_word("aabb", "0000"))

    assert "aabb" not in word_dict
    assert "zzzz" in word_dict

    assert word_dict[0] == "zzzz"

    assert word_dict["zzzz"] == 0

    assert list(word_dict) == ["zzzz"]
    assert len(word_dict) == 1