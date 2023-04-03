from site_reader import LetterInfo, WordleGame, WordDict, Feedback, WordInfo, Solver


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
