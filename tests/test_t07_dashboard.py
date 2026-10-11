"""T07 (#8): the dashboard counts active members.

Each test name says which acceptance criterion of #8 it covers.
"""
from __future__ import annotations


def test_dashboard_shows_the_leader_the_number_of_active_members_linking_to_the_accounts(
        client_as, create_account, account_url, account_action, dashboard_counts):
    leader = client_as("admin")
    count, link = dashboard_counts(leader)["Miembros activos"]
    assert count == "2"  # Ana and Beto; the leader is not a member
    assert link.endswith("/admin/users")

    create_account(leader, email="carla@albiazul.example", role="editor")
    assert dashboard_counts(leader)["Miembros activos"][0] == "3"

    account_action(leader, account_url(leader, "beto@albiazul.example"), "deactivate")
    assert dashboard_counts(leader)["Miembros activos"][0] == "2"

    create_account(leader, email="dani@albiazul.example", role="admin")
    assert dashboard_counts(leader)["Miembros activos"][0] == "2", "a second leader is no member"


def test_members_do_not_see_the_count_of_members(client_as, dashboard_counts):
    assert "Miembros activos" not in dashboard_counts(client_as("editor"))
