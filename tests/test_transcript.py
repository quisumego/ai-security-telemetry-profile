"""Reading completed turn figures from the Claude Code transcript.

This is the one place the lab depends on an artefact of the CLI rather than on
a documented SDK surface, so it is tested against a synthetic transcript. The
contract that matters is not that the reader works, it is that a format change
produces a miss and a null rather than a wrong number.
"""

import json

from lab.transcript import await_completed_turn, read_completed_turns


def _write(path, records):
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def _assistant(message_id, out, stop="end_turn", **usage):
    return {
        "type": "assistant",
        "message": {
            "id": message_id,
            "stop_reason": stop,
            "usage": {
                "input_tokens": 3,
                "cache_creation_input_tokens": 948,
                "cache_read_input_tokens": 14443,
                "output_tokens": out,
                **usage,
            },
        },
    }


def test_completed_turns_are_keyed_by_message_id(tmp_path):
    path = tmp_path / "t.jsonl"
    _write(path, [_assistant("msg_a", 183, "tool_use"), _assistant("msg_b", 512)])

    turns = read_completed_turns(path)
    assert set(turns) == {"msg_a", "msg_b"}
    assert turns["msg_a"].output_tokens == 183
    assert turns["msg_a"].stop_reason == "tool_use"
    assert turns["msg_b"].output_tokens == 512


def test_input_tokens_sum_the_uncached_and_cached_counts(tmp_path):
    path = tmp_path / "t.jsonl"
    _write(path, [_assistant("msg_a", 183)])
    assert read_completed_turns(path)["msg_a"].input_tokens_total == 3 + 948 + 14443


def test_a_later_record_for_the_same_id_wins(tmp_path):
    """The CLI writes one record per content block of a message.

    They carry identical usage, so taking the last is the same as taking the
    first, but the behaviour is pinned so a change is visible.
    """
    path = tmp_path / "t.jsonl"
    _write(path, [_assistant("msg_a", 183), _assistant("msg_a", 183)])
    assert read_completed_turns(path)["msg_a"].output_tokens == 183


def test_non_assistant_records_are_ignored(tmp_path):
    path = tmp_path / "t.jsonl"
    _write(
        path,
        [
            {"type": "user", "message": {"content": "hello"}},
            {"type": "system", "subtype": "init"},
            _assistant("msg_a", 42),
        ],
    )
    assert set(read_completed_turns(path)) == {"msg_a"}


def test_a_half_written_final_line_is_skipped_rather_than_raised_on(tmp_path):
    """The CLI appends to this file while the reader runs."""
    path = tmp_path / "t.jsonl"
    path.write_text(json.dumps(_assistant("msg_a", 42)) + "\n{\"type\": \"assis", encoding="utf-8")
    assert set(read_completed_turns(path)) == {"msg_a"}


def test_a_missing_transcript_gives_nothing_rather_than_an_error(tmp_path):
    assert read_completed_turns(tmp_path / "absent.jsonl") == {}
    assert await_completed_turn(tmp_path / "absent.jsonl", "msg_a", attempts=1, delay=0) is None


def test_a_lookup_that_misses_returns_none_so_the_caller_emits_null(tmp_path):
    """A wrong number is worse than a null. The miss is counted in the manifest."""
    path = tmp_path / "t.jsonl"
    _write(path, [_assistant("msg_a", 42)])
    assert await_completed_turn(path, "msg_b", attempts=1, delay=0) is None
    assert await_completed_turn(path, None, attempts=1, delay=0) is None


def test_a_changed_record_shape_misses_rather_than_returning_a_wrong_number(tmp_path):
    """If the CLI stopped nesting usage under `message`, this must not silently
    read zero. It must miss, so turns_unenriched rises and the change is seen."""
    path = tmp_path / "t.jsonl"
    _write(path, [{"type": "assistant", "usage": {"output_tokens": 183}, "id": "msg_a"}])
    assert read_completed_turns(path) == {}
