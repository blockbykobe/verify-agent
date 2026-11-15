"""Офлайн-тесты эксперимента 6 (RAG): проверка цитат программой, оценка, журнал. Модель не нужна."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rag"))
import rag_experiment as r  # noqa: E402

DOC = """GREP(1)

       -i, --ignore-case
              Ignore  case  distinctions  in  patterns and input data, so that characters that differ only in
              case match each other.

       -v, --invert-match
              Invert the sense of matching, to select non-matching lines.

       -w, --word-regexp
              Select only those lines containing matches that form whole words.
"""
DOCS = {"grep": DOC}


def test_verify_accepts_option_in_entry_header():
    ok, _ = r.verify({"option": "-v", "quote": "Invert the sense of matching, to select non-matching lines.", "source": "grep"}, DOCS)
    assert ok


def test_verify_accepts_option_without_dashes():
    assert r.verify({"option": "invert-match", "quote": "Invert the sense of matching, to select non-matching lines.", "source": "grep"}, DOCS)[0]


def test_verify_rejects_neighbouring_option():
    for opt in ("-i", "-w"):
        assert not r.verify({"option": opt, "quote": "Invert the sense of matching, to select non-matching lines.", "source": "grep"}, DOCS)[0]


def test_verify_rejects_invented_quote_unknown_source_and_short_quote():
    assert not r.verify({"option": "-v", "quote": "Select the lines that do not match the given pattern", "source": "grep"}, DOCS)[0]
    assert not r.verify({"option": "-v", "quote": "Invert the sense of matching, to select non-matching lines.", "source": "egrep"}, DOCS)[0]
    assert not r.verify({"option": "-v", "quote": "Invert", "source": "grep"}, DOCS)[0]


def test_verify_tolerates_line_breaks_and_spacing():
    q = "Ignore case distinctions in patterns and input data, so that characters that differ only in case match each other."
    assert r.verify({"option": "-i", "quote": q, "source": "grep"}, DOCS)[0]


def test_grade():
    ans = {"kind": "answerable", "gold": ["-v", "--invert-match"]}
    trap = {"kind": "trap", "gold": []}
    assert r.grade(ans, "-v") == "correct"
    assert r.grade(ans, "invert-match") == "correct"
    assert r.grade(ans, "-w") == "wrong"
    assert r.grade(ans, None) == "abstain"
    assert r.grade(trap, None) == "correct_abstain"
    assert r.grade(trap, "--backup") == "wrong"


def test_journal_chain_detects_tampering():
    j = r.Journal()
    j.add("q1", {"option": "-v", "quote": "x" * 30, "source": "grep"})
    j.add("q2", {"option": "-i", "quote": "y" * 30, "source": "grep"})
    assert j.intact()
    j.rows[0]["option"] = "-w"
    assert not j.intact()


def test_bm25_ranks_relevant_first():
    bm = r.BM25([r.toks("ignore case distinctions"), r.toks("invert the sense of matching non-matching lines")])
    assert bm.top(r.toks("select non-matching lines"), 1) == [1]
