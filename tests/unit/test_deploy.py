import json
import os
from pathlib import Path
import secrets
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
CURRENT = "example/app@sha256:" + "a" * 64
PREVIOUS = "example/app@sha256:" + "b" * 64


@pytest.fixture
def deployment(tmp_path):
    binary = tmp_path / "docker"
    binary.write_text("#!/usr/bin/env python3\n" + '''
import json, os, sys
args = sys.argv[1:]
if args[:1] == ['--config']:
    args = args[2:]
with open(os.environ['CALL_LOG'], 'a') as output:
    output.write(json.dumps({'args': args, 'image': os.environ.get('IMAGE_REF'), 'port': os.environ.get('APP_PORT')}) + '\\n')
mode = os.environ.get('DEPLOY_TEST_MODE')
if args == ['info'] and os.environ.get('NEEDS_SUDO') == '1' and not os.environ.get('FAKE_SUDO'):
    sys.exit(1)
if args[:1] == ['login']:
    sys.stdin.read()
if args[:1] == ['pull'] and mode == 'pull-fails':
    sys.exit(1)
if args[:1] == ['inspect']:
    if mode == 'first-install-fails':
        sys.exit(1)
    print(os.environ['PREVIOUS_IMAGE'])
if args[:1] == ['compose'] and 'up' in args:
    if mode in ('health-fails', 'first-install-fails') and os.environ['IMAGE_REF'] == os.environ['NEW_IMAGE']:
        sys.exit(1)
''')
    binary.chmod(0o755)
    sudo = tmp_path / "sudo"
    sudo.write_text("#!/usr/bin/env python3\n" + '''
import os, sys
args = sys.argv[1:]
assert args.pop(0) == '-n'
os.environ['FAKE_SUDO'] = '1'
os.execvpe(args[0], args, os.environ)
''')
    sudo.chmod(0o755)
    token = secrets.token_hex(24)
    environment = dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ['PATH'],
                       IMAGE_REF=CURRENT, NEW_IMAGE=CURRENT, PREVIOUS_IMAGE=PREVIOUS,
                       DOCKERHUB_USERNAME='example', DOCKERHUB_TOKEN=token,
                       DEPLOY_DIR=str(ROOT / 'deploy'), CALL_LOG=str(tmp_path / 'calls.jsonl'))

    def execute(mode='success', image=CURRENT, sudo=False):
        environment.update(DEPLOY_TEST_MODE=mode, IMAGE_REF=image, NEEDS_SUDO='1' if sudo else '0')
        result = subprocess.run(['bash', str(ROOT / 'scripts/deploy.sh')],
                                env=environment, capture_output=True, text=True)
        assert token not in result.stdout + result.stderr
        log = Path(environment['CALL_LOG'])
        calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
        return result, calls

    return execute


def updates(calls):
    return [call for call in calls if call['args'][0] == 'compose' and 'up' in call['args']]


@pytest.mark.parametrize('sudo', [False, True])
def test_success_deploys_only_one_service_and_checks_health(deployment, sudo):
    result, calls = deployment(sudo=sudo)
    assert result.returncode == 0, result.stderr
    assert len(updates(calls)) == 1
    assert updates(calls)[0]['image'] == CURRENT
    assert updates(calls)[0]['port'] == '8029'
    assert any(call['args'] == ['exec', 'soubirou-pouey_thomas', 'python', 'healthcheck.py'] for call in calls)
    for call in calls:
        args = call['args']
        if '--project-name' in args:
            assert args[args.index('--project-name') + 1] == 'tp-deploiement-thomas-soubirou-pouey'
        if args[0] == 'inspect':
            assert args[-1] == 'soubirou-pouey_thomas'


def test_pull_failure_leaves_current_service_untouched(deployment):
    result, calls = deployment('pull-fails')
    assert result.returncode != 0
    assert not updates(calls)


@pytest.mark.parametrize('sudo', [False, True])
def test_unhealthy_release_restores_previous_image_and_fails_ci(deployment, sudo):
    result, calls = deployment('health-fails', sudo=sudo)
    assert result.returncode != 0
    assert [call['image'] for call in updates(calls)] == [CURRENT, PREVIOUS]


def test_first_failed_deployment_does_not_invent_a_previous_image(deployment):
    result, calls = deployment('first-install-fails')
    assert result.returncode != 0
    assert len(updates(calls)) == 1


def test_mutable_tag_is_rejected_before_docker_operations(deployment):
    result, calls = deployment(image='example/app:latest')
    assert result.returncode != 0
    assert not calls
