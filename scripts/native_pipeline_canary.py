#!/usr/bin/env python3
"""Real native DB primitive canary; deliberately never dispatch named workers.

This is not a controller or model of task state. Every transition/readback below
uses Hermes' domain API and a new disposable DB. Governed admitted execution,
timing, frozen reviews and remediation are separate root-owned canaries.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def exercise() -> dict:
    root = Path.cwd().resolve()
    if (Path(os.environ.get('HOME', '')).resolve() != root / 'home'
            or Path(os.environ.get('HERMES_HOME', '')).resolve() != root / 'home/.hermes'
            or any(name in os.environ for name in ('HERMES_KANBAN_TASK', 'HERMES_PROFILE',
                                                   'OPENAI_API_KEY', 'ANTHROPIC_API_KEY'))):
        raise ValueError('scrubbed disposable state required')
    from hermes_cli import kanban_db as k
    from hermes_cli import kanban_db_notify as notify
    path = root / 'native-pipeline.db'
    if path.exists() or path.is_symlink():
        raise ValueError('new disposable DB required')
    required = ('release_maker_child', 'seal_staged_verification_packet',
                'create_task', 'claim_task', 'block_task', 'complete_task')
    if not all(callable(getattr(k, name, None)) for name in required):
        raise ValueError('compatible native governed API unavailable; stock equivalence is not assumed')
    connection = k.connect(path)
    try:
        controller = k.create_task(connection, title='fictional controller fixture',
                                   assignee='default', initial_status='blocked',
                                   authority_grants=['local_test'])
        assert k.claim_task(connection, controller) is None
        notify.add_notify_sub(connection, task_id=controller, platform='test',
                              chat_id='fictional-room', thread_id='',
                              notifier_profile='default', delivery_mode='notify+wake')
        rows = notify.list_notify_subs(connection, task_id=controller)
        assert len(rows) == 1
        assert rows[0]['chat_id'] == 'fictional-room'
        assert rows[0]['delivery_mode'] == 'notify+wake'
        assert rows[0]['notifier_profile'] == 'default'
        maker = k.create_task(connection, title='fictional fenced maker fixture',
                              body='stage: forge_implementation\n', assignee='forge',
                              creator_task_id=controller, initial_status='blocked',
                              authority_grants=['local_test'])
        k.link_tasks(connection, maker, controller)
        refused = k.release_maker_child(connection, controller, maker,
                                         caller_task_id=maker, caller_run_id=None)
        assert refused.reason == 'caller_not_root'
        refused = k.release_maker_child(connection, controller, maker,
                                         caller_task_id=controller, caller_run_id=None)
        assert refused.reason == 'release_not_admitted'
        assert k.get_task(connection, maker).status == 'blocked'
        assert k.claim_task(connection, maker) is None
        # A separate UNGOVERNED harmless substrate graph proves real dependency
        # readiness/recovery. It neither fabricates a governed verdict nor launches.
        producer = k.create_task(connection, title='fictional producer', assignee='fixture')
        verifier = k.create_task(connection, title='fictional dependency consumer',
                                 assignee='fixture', parents=[producer])
        reviewer = k.create_task(connection, title='fictional chained consumer',
                                 assignee='fixture', parents=[verifier])
        assert k.claim_task(connection, reviewer) is None
        assert k.claim_task(connection, verifier) is None
        assert k.claim_task(connection, producer) is not None
        assert k.complete_task(connection, producer, summary='fixture computation complete')
        assert k.get_task(connection, verifier).status == 'ready'
        assert k.claim_task(connection, reviewer) is None
        assert k.claim_task(connection, verifier) is not None
        assert k.complete_task(connection, verifier, summary='fixture computation complete, not formal PASS')
        assert k.get_task(connection, reviewer).status == 'ready'
        assert k.claim_task(connection, reviewer) is not None
        dependency = k.create_task(connection, title='fictional recovery dependency', assignee='fixture')
        k.link_tasks(connection, dependency, reviewer)
        assert k.block_task(connection, reviewer, kind='dependency', reason='fixture dependency wait')
        assert k.get_task(connection, reviewer).status == 'todo'
        assert k.claim_task(connection, dependency) is not None
        assert k.complete_task(connection, dependency, summary='fixture recovery computation complete')
        assert k.get_task(connection, reviewer).status == 'ready'
        assert k.claim_task(connection, reviewer) is not None
        assert k.complete_task(connection, reviewer, summary='fixture recovery complete')
        return {'native_dependencies': 'passed',
                'notification_readback': 'passed-exact-notify+wake',
                'unadmitted_release_refused': True, 'review_dependency_fence': True,
                'dependency_resume': 'passed', 'named_worker_launches': 0,
                'governed_end_to_end': 'root-owned-pending',
                'root_owned_canaries': ['admitted Gateway worker execution',
                    'installed timing start/readback/transitions/terminal durations',
                    'frozen exact-head stateless evidence', 'Verifier PASS then dependent Reviewer',
                    'one substantive remediation and exact-stop recovery'],
                'delegate_task': 0, 'async_delegations': 0}
    finally:
        connection.close()


if __name__ == '__main__':
    print(json.dumps(exercise(), sort_keys=True))
