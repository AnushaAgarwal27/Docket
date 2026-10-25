from agents.coordinator.selection import parse_selection


def test_direct_mention_json():
    assert parse_selection('{"action": "approve_refund", "case_id": "c1"}') == {"action": "approve_refund", "case_id": "c1"}


def test_form_json_carries_field_values():
    sel = parse_selection('{"action": "submit_profile", "arrival_date": "2024-08-15", "visa_type": "F-1", '
                          '"employer": "University Dining Services"}')
    assert sel["action"] == "submit_profile" and sel["visa_type"] == "F-1"


def test_planner_prose_with_the_action_id():
    assert parse_selection("The user clicked Approve (approve_refund) on the refund review card.") == {
        "action": "approve_refund"}


def test_planner_prose_with_form_values():
    sel = parse_selection("The user submitted the profile form (submit_profile) with arrival_date: 2024-08-15, "
                          "visa_type: F-1, employer: University Dining Services.")
    assert sel == {"action": "submit_profile", "arrival_date": "2024-08-15", "visa_type": "F-1",
                   "employer": "University Dining Services"}


def test_ordinary_messages_are_not_selections():
    assert parse_selection("check my pay") is None
    assert parse_selection("yes") is None
    assert parse_selection('{"hello": "world"}') is None
    assert parse_selection("[1, 2]") is None


def test_ambiguous_prose_is_not_guessed():
    assert parse_selection("approve_refund or decline_refund?") is None
