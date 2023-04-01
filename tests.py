from site_reader import LetterInfo, WordleGame, WordDict, Feedback, WordInfo


def test_generate_feedback():
    test_answer = "aaabb"
    
    answer_matches_expected = lambda guess, expected_feedback: str(WordInfo(WordleGame.generate_full_feedback(test_answer, guess))) == expected_feedback

    assert answer_matches_expected("aabbb", "AA~BB")
    assert answer_matches_expected("bbaaa", "bbAaa")
    assert answer_matches_expected("abbbb", "A~~BB")
    assert answer_matches_expected("baaaa", "bAAa~")
    assert answer_matches_expected("bbbba", "b~~Ba")
    assert answer_matches_expected("acaca", "A~A~a")


if __name__ == "__main__":
    test_generate_feedback()