# Unit Test Report

Project: Shared Whiteboard (Team 11, Section E). Report date: 05-11-2026.

Code under test: main at 5768ae4 (canvas wired, availability test merged) plus the test-ID fix (tests/e2e and tests/test_restore_notifies.py renamed).

Environment: Python 3.13.16, pytest 9.1.1 (pytest-cov), FastAPI 0.162.0, SQLAlchemy 2.1.6, Playwright with Chromium; Linux; SQLite in memory for the unit and integration tests, SQLite file for the browser tests.

## Summary

| Item | Value |
|---|---|
| Tests run | 175 |
| Passed | 175 |
| Failed | 0 |
| Skipped | 0 |
| Pass rate | 100.0% |
| Run time | 35.1 s |
| Unit and integration tests (pytest, no browser) | 160 |
| Browser tests (Playwright, Chromium) | 15 |

Command: `pytest --cov=src --cov-branch --junitxml=junit.xml`. Every test name carries its STP test case id, so `pytest -k tc_sync_04` selects one case.

## Results by test file

| File | Level | Tests | Passed | Failed | Test cases covered |
|---|---|---|---|---|---|
| `tests/e2e/test_canvas_sync.py` | System (browser) | 15 | 15 | 0 | TC-Draw-01, TC-Draw-02, TC-Draw-03, TC-Draw-04, TC-Draw-05, TC-Draw-06, TC-Sync-01, TC-Sync-02, TC-Sync-04, TC-Ver-02, TC-Ver-04, TC-Ver-05 |
| `tests/test_board_api.py` | Unit / integration | 6 | 6 | 0 | TC-Board-01 |
| `tests/test_board_api_edge_cases.py` | Unit / integration | 8 | 8 | 0 | TC-Board-01, TC-Sec-03 |
| `tests/test_convergence.py` | Unit / integration | 31 | 31 | 0 | TC-Sync-05 |
| `tests/test_gateway_persistence.py` | Unit / integration | 13 | 13 | 0 | TC-Persist-01 |
| `tests/test_health.py` | Unit / integration | 1 | 1 | 0 | supporting tests |
| `tests/test_persistence.py` | Unit / integration | 6 | 6 | 0 | TC-Persist-01 |
| `tests/test_restore_notifies.py` | Unit / integration | 2 | 2 | 0 | TC-Ver-05 |
| `tests/test_security.py` | Unit / integration | 10 | 10 | 0 | TC-Sec-02, TC-Sec-05 |
| `tests/test_session_service.py` | Unit / integration | 13 | 13 | 0 | TC-Board-02, TC-Board-03, TC-Board-04, TC-Sec-06 |
| `tests/test_snapshots.py` | Unit / integration | 10 | 10 | 0 | supporting tests |
| `tests/test_sync_gateway.py` | Unit / integration | 48 | 48 | 0 | TC-Board-02, TC-Board-03, TC-Board-04, TC-Sec-03, TC-Sec-04, TC-Sec-06, TC-Sync-01, TC-Sync-02, TC-Sync-03, TC-Sync-04, TC-Sync-05 |
| `tests/test_version_service.py` | Unit / integration | 12 | 12 | 0 | TC-Ver-01, TC-Ver-02, TC-Ver-03, TC-Ver-04, TC-Ver-05 |

## Results by STP test case

| Test case | Tests | Passed | Result |
|---|---|---|---|
| TC-Board-01 | 13 | 13 | Pass |
| TC-Board-02 | 13 | 13 | Pass |
| TC-Board-03 | 3 | 3 | Pass |
| TC-Board-04 | 5 | 5 | Pass |
| TC-Draw-01 | 1 | 1 | Pass |
| TC-Draw-02 | 1 | 1 | Pass |
| TC-Draw-03 | 2 | 2 | Pass |
| TC-Draw-04 | 2 | 2 | Pass |
| TC-Draw-05 | 1 | 1 | Pass |
| TC-Draw-06 | 1 | 1 | Pass |
| TC-Persist-01 | 3 | 3 | Pass |
| TC-Sec-02 | 7 | 7 | Pass |
| TC-Sec-03 | 14 | 14 | Pass |
| TC-Sec-04 | 4 | 4 | Pass |
| TC-Sec-05 | 3 | 3 | Pass |
| TC-Sec-06 | 3 | 3 | Pass |
| TC-Sync-01 | 5 | 5 | Pass |
| TC-Sync-02 | 3 | 3 | Pass |
| TC-Sync-03 | 5 | 5 | Pass |
| TC-Sync-04 | 7 | 7 | Pass |
| TC-Sync-05 | 22 | 22 | Pass |
| TC-Ver-01 | 3 | 3 | Pass |
| TC-Ver-02 | 3 | 3 | Pass |
| TC-Ver-03 | 2 | 2 | Pass |
| TC-Ver-04 | 3 | 3 | Pass |
| TC-Ver-05 | 6 | 6 | Pass |

Cases with no pytest test: TC-Perf-01, TC-Perf-02 (k6, see system validation report), TC-Ops-01 (script `tests/ops/check_availability.sh`, run: restart in 1.7 s), TC-Perf-03 and TC-Compat-01 (not run) and TC-Sec-01 (script `tests/ops/check_tls.sh`, not run because the system is not deployed).

## Every test

| # | File | Test | Result | Time (s) |
|---|---|---|---|---|
| 1 | `test_canvas_sync.py` | `test_tc_draw_01_colour_and_thickness_sync` | passed | 0.75 |
| 2 | `test_canvas_sync.py` | `test_tc_draw_02_shapes_sync` | passed | 0.83 |
| 3 | `test_canvas_sync.py` | `test_tc_draw_03_text_can_be_edited` | passed | 0.57 |
| 4 | `test_canvas_sync.py` | `test_tc_draw_03_text_syncs` | passed | 0.53 |
| 5 | `test_canvas_sync.py` | `test_tc_draw_04_other_user_can_move_and_delete` | passed | 0.85 |
| 6 | `test_canvas_sync.py` | `test_tc_draw_04_resize` | passed | 0.73 |
| 7 | `test_canvas_sync.py` | `test_tc_draw_05_eraser_removes_for_everyone` | passed | 0.83 |
| 8 | `test_canvas_sync.py` | `test_tc_draw_06_undo_only_undoes_own_work` | passed | 0.68 |
| 9 | `test_canvas_sync.py` | `test_tc_sync_01_drawing_reaches_the_other_browser` | passed | 2.62 |
| 10 | `test_canvas_sync.py` | `test_tc_sync_02_remote_cursor_shows_name` | passed | 0.95 |
| 11 | `test_canvas_sync.py` | `test_tc_sync_04_joiner_receives_the_full_board_state` | passed | 0.81 |
| 12 | `test_canvas_sync.py` | `test_tc_sync_04_reconnect_and_resync` | passed | 1.43 |
| 13 | `test_canvas_sync.py` | `test_tc_ver_02_named_version_is_saved_and_listed` | passed | 0.87 |
| 14 | `test_canvas_sync.py` | `test_tc_ver_04_preview_is_read_only` | passed | 1.21 |
| 15 | `test_canvas_sync.py` | `test_tc_ver_05_restore_updates_everyone` | passed | 1.34 |
| 16 | `test_board_api.py` | `test_tc_board_01_create_board` | passed | 0.05 |
| 17 | `test_board_api.py` | `test_tc_board_01_create_board_default_name` | passed | 0.02 |
| 18 | `test_board_api.py` | `test_tc_board_01_get_board_roundtrip` | passed | 0.04 |
| 19 | `test_board_api.py` | `test_tc_board_01_ids_are_unique` | passed | 0.72 |
| 20 | `test_board_api.py` | `test_tc_board_01_invalid_name_rejected` | passed | 0.03 |
| 21 | `test_board_api.py` | `test_tc_board_01_unknown_board_404` | passed | 0.02 |
| 22 | `test_board_api_edge_cases.py` | `test_tc_board_01_malformed_id_not_found` | passed | 0.03 |
| 23 | `test_board_api_edge_cases.py` | `test_tc_board_01_name_length_boundaries_accepted[100]` | passed | 0.03 |
| 24 | `test_board_api_edge_cases.py` | `test_tc_board_01_name_length_boundaries_accepted[1]` | passed | 0.03 |
| 25 | `test_board_api_edge_cases.py` | `test_tc_board_01_wrong_type_name_rejected[123]` | passed | 0.02 |
| 26 | `test_board_api_edge_cases.py` | `test_tc_board_01_wrong_type_name_rejected[None]` | passed | 0.02 |
| 27 | `test_board_api_edge_cases.py` | `test_tc_board_01_wrong_type_name_rejected[bad_name2]` | passed | 0.02 |
| 28 | `test_board_api_edge_cases.py` | `test_tc_board_01_wrong_type_name_rejected[bad_name3]` | passed | 0.02 |
| 29 | `test_board_api_edge_cases.py` | `test_tc_sec_03_script_in_name_does_not_break_api` | passed | 0.04 |
| 30 | `test_convergence.py` | `test_concurrent_edits_to_different_fields_both_survive` | passed | 0.00 |
| 31 | `test_convergence.py` | `test_delete_after_update_removes_object` | passed | 0.00 |
| 32 | `test_convergence.py` | `test_merge_matches_seq_replay_for_in_order_ops` | passed | 0.05 |
| 33 | `test_convergence.py` | `test_re_add_after_delete_starts_fresh` | passed | 0.00 |
| 34 | `test_convergence.py` | `test_redelivered_ops_are_idempotent` | passed | 0.00 |
| 35 | `test_convergence.py` | `test_same_field_later_timestamp_beats_higher_client_id` | passed | 0.00 |
| 36 | `test_convergence.py` | `test_same_field_same_timestamp_higher_client_id_wins` | passed | 0.00 |
| 37 | `test_convergence.py` | `test_seq_order_replay_is_order_dependent` | passed | 0.00 |
| 38 | `test_convergence.py` | `test_tc_sync_05_every_client_ends_with_same_board` | passed | 0.01 |
| 39 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[0]` | passed | 0.01 |
| 40 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[10]` | passed | 0.01 |
| 41 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[11]` | passed | 0.01 |
| 42 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[12]` | passed | 0.01 |
| 43 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[13]` | passed | 0.01 |
| 44 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[14]` | passed | 0.01 |
| 45 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[15]` | passed | 0.01 |
| 46 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[16]` | passed | 0.01 |
| 47 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[17]` | passed | 0.01 |
| 48 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[18]` | passed | 0.01 |
| 49 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[19]` | passed | 0.01 |
| 50 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[1]` | passed | 0.01 |
| 51 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[2]` | passed | 0.01 |
| 52 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[3]` | passed | 0.01 |
| 53 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[4]` | passed | 0.01 |
| 54 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[5]` | passed | 0.01 |
| 55 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[6]` | passed | 0.01 |
| 56 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[7]` | passed | 0.01 |
| 57 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[8]` | passed | 0.01 |
| 58 | `test_convergence.py` | `test_tc_sync_05_random_workloads_converge[9]` | passed | 0.01 |
| 59 | `test_convergence.py` | `test_update_after_delete_does_not_resurrect` | passed | 0.00 |
| 60 | `test_convergence.py` | `test_update_for_unknown_object_is_ignored` | passed | 0.00 |
| 61 | `test_gateway_persistence.py` | `test_database_failure_does_not_break_the_live_board` | passed | 0.02 |
| 62 | `test_gateway_persistence.py` | `test_load_state_resets_log_so_resume_cannot_replay_stale_ops` | passed | 0.00 |
| 63 | `test_gateway_persistence.py` | `test_objects_from_state_skips_entries_without_a_type` | passed | 0.00 |
| 64 | `test_gateway_persistence.py` | `test_ops_are_stored_in_the_flat_format_with_matching_seq` | passed | 0.03 |
| 65 | `test_gateway_persistence.py` | `test_rejected_and_duplicate_ops_are_not_saved` | passed | 0.03 |
| 66 | `test_gateway_persistence.py` | `test_restore_then_restart_shows_the_restored_board` | passed | 0.13 |
| 67 | `test_gateway_persistence.py` | `test_resume_after_restart_falls_back_to_a_full_welcome` | passed | 0.03 |
| 68 | `test_gateway_persistence.py` | `test_room_from_db_of_an_empty_board_is_empty` | passed | 0.01 |
| 69 | `test_gateway_persistence.py` | `test_seq_continues_after_a_restart_with_no_gap` | passed | 0.03 |
| 70 | `test_gateway_persistence.py` | `test_tc_persist_01_updates_and_deletes_survive_a_restart` | passed | 0.04 |
| 71 | `test_gateway_persistence.py` | `test_tc_persist_01_ws_objects_survive_a_server_restart` | passed | 0.12 |
| 72 | `test_gateway_persistence.py` | `test_type_cannot_be_used_as_a_property_name` | passed | 0.00 |
| 73 | `test_gateway_persistence.py` | `test_wb_f_030_auto_snapshot_after_100_ops` | passed | 0.10 |
| 74 | `test_health.py` | `test_healthz` | passed | 0.01 |
| 75 | `test_persistence.py` | `test_delete_removes_object` | passed | 0.04 |
| 76 | `test_persistence.py` | `test_duplicate_seq_rejected_by_db` | passed | 0.04 |
| 77 | `test_persistence.py` | `test_invalid_op_type_rejected` | passed | 0.02 |
| 78 | `test_persistence.py` | `test_list_ops_after_seq_supports_resync` | passed | 0.05 |
| 79 | `test_persistence.py` | `test_sequence_numbers_are_gapless_per_board` | passed | 0.05 |
| 80 | `test_persistence.py` | `test_tc_persist_01_state_survives_restart` | passed | 0.05 |
| 81 | `test_restore_notifies.py` | `test_tc_ver_05_restore_notifies_connected_clients` | passed | 0.13 |
| 82 | `test_restore_notifies.py` | `test_tc_ver_05_restore_with_nobody_connected_still_works` | passed | 0.09 |
| 83 | `test_security.py` | `test_tc_sec_02_generated_ids_are_long_and_unique` | passed | 0.06 |
| 84 | `test_security.py` | `test_tc_sec_02_malformed_ids_are_404_not_errors[%00]` | passed | 0.02 |
| 85 | `test_security.py` | `test_tc_sec_02_malformed_ids_are_404_not_errors[../etc/passwd]` | passed | 0.02 |
| 86 | `test_security.py` | `test_tc_sec_02_malformed_ids_are_404_not_errors[0000000000000000000000000000000]` | passed | 0.02 |
| 87 | `test_security.py` | `test_tc_sec_02_malformed_ids_are_404_not_errors[1]` | passed | 0.02 |
| 88 | `test_security.py` | `test_tc_sec_02_malformed_ids_are_404_not_errors[admin]` | passed | 0.02 |
| 89 | `test_security.py` | `test_tc_sec_02_random_ids_never_find_a_board` | passed | 11.30 |
| 90 | `test_security.py` | `test_tc_sec_05_each_restore_has_an_audit_entry` | passed | 0.10 |
| 91 | `test_security.py` | `test_tc_sec_05_restores_never_lose_a_snapshot` | passed | 0.14 |
| 92 | `test_security.py` | `test_tc_sec_05_versions_cannot_be_deleted_through_the_api` | passed | 0.08 |
| 93 | `test_session_service.py` | `test_client_ids_are_unique` | passed | 0.00 |
| 94 | `test_session_service.py` | `test_tc_board_02_invalid_name_rejected[   ]` | passed | 0.00 |
| 95 | `test_session_service.py` | `test_tc_board_02_invalid_name_rejected[None]` | passed | 0.00 |
| 96 | `test_session_service.py` | `test_tc_board_02_invalid_name_rejected[]` | passed | 0.00 |
| 97 | `test_session_service.py` | `test_tc_board_02_invalid_name_rejected[xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx]` | passed | 0.00 |
| 98 | `test_session_service.py` | `test_tc_board_02_name_is_trimmed` | passed | 0.00 |
| 99 | `test_session_service.py` | `test_tc_board_02_name_of_30_characters_is_accepted` | passed | 0.00 |
| 100 | `test_session_service.py` | `test_tc_board_02_valid_name_joins` | passed | 0.00 |
| 101 | `test_session_service.py` | `test_tc_board_03_participants_follow_join_and_leave` | passed | 0.00 |
| 102 | `test_session_service.py` | `test_tc_board_04_21st_participant_is_refused` | passed | 0.00 |
| 103 | `test_session_service.py` | `test_tc_board_04_boards_are_independent` | passed | 0.00 |
| 104 | `test_session_service.py` | `test_tc_board_04_slot_frees_when_someone_leaves` | passed | 0.00 |
| 105 | `test_session_service.py` | `test_tc_sec_06_is_member_only_for_the_joined_board_and_client` | passed | 0.00 |
| 106 | `test_snapshots.py` | `test_auto_snapshot_after_100_ops` | passed | 0.41 |
| 107 | `test_snapshots.py` | `test_auto_snapshot_after_5_minutes_of_activity` | passed | 0.05 |
| 108 | `test_snapshots.py` | `test_counter_resets_after_snapshot` | passed | 0.43 |
| 109 | `test_snapshots.py` | `test_load_does_not_mutate_stored_snapshot` | passed | 0.06 |
| 110 | `test_snapshots.py` | `test_no_auto_snapshot_without_new_ops` | passed | 0.05 |
| 111 | `test_snapshots.py` | `test_prune_keeps_newest_50` | passed | 0.48 |
| 112 | `test_snapshots.py` | `test_prune_returns_removed_count` | passed | 0.06 |
| 113 | `test_snapshots.py` | `test_snapshot_on_empty_board` | passed | 0.04 |
| 114 | `test_snapshots.py` | `test_snapshot_plus_tail_equals_full_replay` | passed | 0.07 |
| 115 | `test_snapshots.py` | `test_snapshot_records_seq_and_state` | passed | 0.06 |
| 116 | `test_sync_gateway.py` | `test_board_reset_replaces_state_for_everyone_and_keeps_seq_in_step_with_the_log` | passed | 0.00 |
| 117 | `test_sync_gateway.py` | `test_persistence_listener_sees_every_applied_op_once` | passed | 0.00 |
| 118 | `test_sync_gateway.py` | `test_tc_board_02_bad_names_are_refused[   ]` | passed | 0.00 |
| 119 | `test_sync_gateway.py` | `test_tc_board_02_bad_names_are_refused[]` | passed | 0.00 |
| 120 | `test_sync_gateway.py` | `test_tc_board_02_bad_names_are_refused[xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx]` | passed | 0.00 |
| 121 | `test_sync_gateway.py` | `test_tc_board_02_join_gets_welcome_with_client_id_and_state` | passed | 0.00 |
| 122 | `test_sync_gateway.py` | `test_tc_board_02_ws_empty_name_closes_with_4003` | passed | 0.04 |
| 123 | `test_sync_gateway.py` | `test_tc_board_02_ws_unknown_board_closes_with_4001` | passed | 0.02 |
| 124 | `test_sync_gateway.py` | `test_tc_board_03_presence_follows_join_and_leave` | passed | 0.00 |
| 125 | `test_sync_gateway.py` | `test_tc_board_03_ws_leaver_disappears_from_presence` | passed | 0.16 |
| 126 | `test_sync_gateway.py` | `test_tc_board_04_21st_client_refused_then_admitted_after_a_leave` | passed | 0.01 |
| 127 | `test_sync_gateway.py` | `test_tc_board_04_ws_21st_client_refused_with_4002` | passed | 0.35 |
| 128 | `test_sync_gateway.py` | `test_tc_sec_03_bad_messages_get_4003_and_connection_stays_open[[]]` | passed | 0.00 |
| 129 | `test_sync_gateway.py` | `test_tc_sec_03_bad_messages_get_4003_and_connection_stays_open[not json]` | passed | 0.00 |
| 130 | `test_sync_gateway.py` | `test_tc_sec_03_bad_messages_get_4003_and_connection_stays_open[{"no": "type"}]` | passed | 0.00 |
| 131 | `test_sync_gateway.py` | `test_tc_sec_03_bad_messages_get_4003_and_connection_stays_open[{"type": "cursor:move", "x": "left", "y": 1}]` | passed | 0.00 |
| 132 | `test_sync_gateway.py` | `test_tc_sec_03_bad_messages_get_4003_and_connection_stays_open[{"type": "evil"}]` | passed | 0.00 |
| 133 | `test_sync_gateway.py` | `test_tc_sec_03_bad_messages_get_4003_and_connection_stays_open[{"type": "op:add", "opId": "x", "object": {"id": "1", "type": "nope", "props": {"a": 1}}}]` | passed | 0.00 |
| 134 | `test_sync_gateway.py` | `test_tc_sec_03_bad_messages_get_4003_and_connection_stays_open[{"type": "op:add", "opId": "x"}]` | passed | 0.00 |
| 135 | `test_sync_gateway.py` | `test_tc_sec_03_bad_messages_get_4003_and_connection_stays_open[{"type": "op:update", "opId": "x", "objectId": "1", "changes": {}}]` | passed | 0.00 |
| 136 | `test_sync_gateway.py` | `test_tc_sec_03_bad_messages_get_4003_and_connection_stays_open[{"type": "resume", "lastSeq": -1}]` | passed | 0.00 |
| 137 | `test_sync_gateway.py` | `test_tc_sec_03_oversized_message_rejected_with_413` | passed | 0.00 |
| 138 | `test_sync_gateway.py` | `test_tc_sec_03_script_text_is_stored_and_relayed_as_plain_text` | passed | 0.00 |
| 139 | `test_sync_gateway.py` | `test_tc_sec_03_text_length_and_point_count_limits` | passed | 0.01 |
| 140 | `test_sync_gateway.py` | `test_tc_sec_03_ws_garbage_does_not_drop_the_connection` | passed | 0.05 |
| 141 | `test_sync_gateway.py` | `test_tc_sec_04_bucket_refills_over_time` | passed | 0.00 |
| 142 | `test_sync_gateway.py` | `test_tc_sec_04_flooder_is_throttled_to_about_60_per_second_and_gets_4290` | passed | 0.01 |
| 143 | `test_sync_gateway.py` | `test_tc_sec_04_occasional_bursts_do_not_add_up_to_a_disconnect` | passed | 0.01 |
| 144 | `test_sync_gateway.py` | `test_tc_sec_04_persistent_flooding_closes_the_connection` | passed | 0.01 |
| 145 | `test_sync_gateway.py` | `test_tc_sec_06_connection_can_only_ever_touch_its_own_board` | passed | 0.00 |
| 146 | `test_sync_gateway.py` | `test_tc_sec_06_message_after_leaving_is_rejected_and_changes_nothing` | passed | 0.00 |
| 147 | `test_sync_gateway.py` | `test_tc_sync_01_ack_carries_op_id_and_server_seq` | passed | 0.00 |
| 148 | `test_sync_gateway.py` | `test_tc_sync_01_boards_are_isolated` | passed | 0.00 |
| 149 | `test_sync_gateway.py` | `test_tc_sync_01_every_client_gets_all_100_ops_in_order_without_duplicates` | passed | 0.02 |
| 150 | `test_sync_gateway.py` | `test_tc_sync_01_ws_two_browsers_see_each_others_strokes` | passed | 0.06 |
| 151 | `test_sync_gateway.py` | `test_tc_sync_02_cursor_is_relayed_with_name_to_others_only` | passed | 0.00 |
| 152 | `test_sync_gateway.py` | `test_tc_sync_02_cursor_is_throttled_to_about_20_per_second_and_never_stored` | passed | 0.00 |
| 153 | `test_sync_gateway.py` | `test_tc_sync_03_concurrent_edits_end_identical_for_all_clients` | passed | 0.00 |
| 154 | `test_sync_gateway.py` | `test_tc_sync_03_different_properties_both_kept` | passed | 0.00 |
| 155 | `test_sync_gateway.py` | `test_tc_sync_03_rejected_ops_are_not_broadcast_and_sender_gets_an_error` | passed | 0.00 |
| 156 | `test_sync_gateway.py` | `test_tc_sync_03_same_property_higher_seq_wins` | passed | 0.00 |
| 157 | `test_sync_gateway.py` | `test_tc_sync_03_update_after_delete_is_ignored_tombstone` | passed | 0.00 |
| 158 | `test_sync_gateway.py` | `test_tc_sync_04_gap_larger_than_log_falls_back_to_full_state` | passed | 0.00 |
| 159 | `test_sync_gateway.py` | `test_tc_sync_04_offline_stroke_reaches_others_exactly_once_even_if_resent` | passed | 0.00 |
| 160 | `test_sync_gateway.py` | `test_tc_sync_04_resume_from_the_future_gets_full_state` | passed | 0.00 |
| 161 | `test_sync_gateway.py` | `test_tc_sync_04_resume_replays_missed_ops` | passed | 0.00 |
| 162 | `test_sync_gateway.py` | `test_tc_sync_04_ws_reconnect_with_resume_catches_up` | passed | 0.06 |
| 163 | `test_sync_gateway.py` | `test_tc_sync_05_ten_clients_200_random_ops_each_all_converge` | passed | 0.47 |
| 164 | `test_version_service.py` | `test_tc_ver_01_auto_snapshot_after_100_ops` | passed | 0.22 |
| 165 | `test_version_service.py` | `test_tc_ver_01_auto_snapshot_after_5_minutes` | passed | 0.04 |
| 166 | `test_version_service.py` | `test_tc_ver_01_no_snapshot_without_changes` | passed | 0.03 |
| 167 | `test_version_service.py` | `test_tc_ver_02_named_snapshot` | passed | 0.06 |
| 168 | `test_version_service.py` | `test_tc_ver_02_unknown_board_404` | passed | 0.03 |
| 169 | `test_version_service.py` | `test_tc_ver_03_empty_list` | passed | 0.04 |
| 170 | `test_version_service.py` | `test_tc_ver_03_list_is_newest_first_and_capped_at_50` | passed | 1.20 |
| 171 | `test_version_service.py` | `test_tc_ver_04_preview_returns_the_saved_state` | passed | 0.09 |
| 172 | `test_version_service.py` | `test_tc_ver_04_unknown_version_404` | passed | 0.04 |
| 173 | `test_version_service.py` | `test_tc_ver_05_restore_creates_new_version_and_keeps_history` | passed | 0.13 |
| 174 | `test_version_service.py` | `test_tc_ver_05_restore_unknown_version_404` | passed | 0.03 |
| 175 | `test_version_service.py` | `test_tc_ver_05_restore_writes_audit_log` | passed | 0.07 |
