from unittest.mock import MagicMock

import pytest

from lizzy.apps.senza import Senza
from lizzy.version import VERSION
from lizzy.exceptions import (ExecutionError, SenzaPatchError,
                              SenzaRespawnInstancesError, SenzaTrafficError,
                              SenzaDomainsError, SenzaRenderError)


@pytest.fixture
def popen(monkeypatch):
    mock_popen = MagicMock()
    mock_popen.return_value = mock_popen
    mock_popen.returncode = 0
    mock_popen.communicate.return_value = b'{"stream": "stdout"}', b'stderr'
    monkeypatch.setattr('lizzy.apps.common.Popen', mock_popen)
    return mock_popen


@pytest.mark.parametrize(
    "version, parameters, region, disable_rollback, dry_run, tags",
    [
        ("new_version", ['param1', 'param2'], None, False, False, {'RandomTag': 'tag_value'}),
        ("new_version", [], "eu-central-1", True, False, {'TagName': 'random_tag'}),
        ("other_version", ['p1'], "us-central-1", False, True, {'RandomTag': 'value2'}),
        ("42", ['param1', 'param2'], None, True, True, {'RandomTag': 'tag_value', 'TagName': 'random_tag'}),
    ])
def test_create(monkeypatch, popen, version, parameters, region, disable_rollback, dry_run, tags):
    mock_named_tempfile = MagicMock()
    mock_tempfile = MagicMock()
    mock_tempfile.name = 'filename'
    mock_named_tempfile.__enter__.return_value = mock_tempfile
    mock_named_tempfile.return_value = mock_named_tempfile
    monkeypatch.setattr('tempfile.NamedTemporaryFile', mock_named_tempfile)
    lizzy_version_tag = 'LizzyVersion={}'.format(VERSION)

    region = region or 'region'
    senza = Senza(region)
    senza.logger = MagicMock()
    senza.create('yaml: yaml', version, parameters, disable_rollback,
                 dry_run, tags)

    mock_named_tempfile.assert_called_with()
    mock_tempfile.write.assert_called_with(b'yaml: yaml')

    expected_disabled_rollback = ['--disable-rollback'] if disable_rollback else []
    expected_dry_run = ['--dry-run'] if dry_run else []

    extra_tags = []
    for key, value in tags.items():
        extra_tags.extend(['-t', '{0}={1}'.format(key, value)])

    popen.assert_called_with(['senza', 'create',
                              '--region', region,
                              '--force']
                             + expected_disabled_rollback
                             + expected_dry_run
                             + ['filename', version]
                             + parameters
                             + ['-t', lizzy_version_tag]
                             + extra_tags,
                             stdout=-1,
                             stderr=-2)
    assert not senza.logger.error.called


def test_create_error(monkeypatch, popen):
    mock_named_tempfile = MagicMock()
    mock_tempfile = MagicMock()
    mock_tempfile.name = 'filename'
    mock_named_tempfile.__enter__.return_value = mock_tempfile
    mock_named_tempfile.return_value = mock_named_tempfile
    monkeypatch.setattr('tempfile.NamedTemporaryFile', mock_named_tempfile)

    senza = Senza('region')
    senza.logger = MagicMock()
    popen.returncode = 1

    with pytest.raises(ExecutionError):
        senza.create('yaml: yaml', '10', ['param1', 'param2'], False, False, {})


def test_domain(monkeypatch, popen):
    senza = Senza('region')
    senza.logger = MagicMock()
    domains = senza.domains()

    cmd = 'senza domains --region region -o json'
    senza.logger.debug.assert_called_with('Executing %s.', 'senza', extra={'command': cmd})
    assert not senza.logger.error.called
    assert not senza.logger.exception.called

    popen.assert_called_with(['senza', 'domains', '--region', 'region', '-o', 'json'],
                             stdout=-1,
                             stderr=-1)

    assert domains == {'stream': 'stdout'}

    senza.logger.reset_mock()
    popen.reset_mock()

    popen.communicate.return_value = b'{"test": "domain2"}', b'stderr'
    domains = senza.domains('lizzy')

    cmd = 'senza domains --region region -o json lizzy'
    senza.logger.debug.assert_called_with('Executing %s.', 'senza', extra={'command': cmd})
    assert not senza.logger.error.called
    assert not senza.logger.exception.called

    popen.assert_called_with(['senza', 'domains', '--region', 'region', '-o', 'json', 'lizzy'], stdout=-1, stderr=-1)

    assert domains == {'test': 'domain2'}

    # test error case
    popen.side_effect = ExecutionError('', '')

    with pytest.raises(SenzaDomainsError):
        senza.domains()


def test_list(monkeypatch, popen):
    popen.communicate.return_value = b'["item1", "item2"]', b'stderr'
    senza = Senza('region')
    senza.logger = MagicMock()
    list = senza.list()

    cmd = 'senza list --region region -o json'
    senza.logger.debug.assert_called_with('Executing %s.', 'senza', extra={'command': cmd})
    assert not senza.logger.error.called
    assert not senza.logger.exception.called

    popen.assert_called_with(['senza', 'list', '--region', 'region', '-o', 'json'], stdout=-1, stderr=-1)

    assert list == ["item1", "item2"]

    # Test invalid json
    popen.communicate.return_value = b'"', b'stderr'
    with pytest.raises(ExecutionError):
        senza.list()


def test_remove(monkeypatch, popen):
    senza = Senza('region')
    senza.logger = MagicMock()
    senza.remove('lizzy', 'version')

    popen.assert_called_with(['senza', 'delete', '--region', 'region', 'lizzy', 'version'], stdout=-1, stderr=-2)

    cmd = 'senza delete --region region lizzy version'
    senza.logger.debug.assert_called_with('Executing %s.', 'senza', extra={'command': cmd})
    assert not senza.logger.error.called
    assert not senza.logger.exception.called

    popen.returncode = 1
    senza.logger.reset_mock()

    with pytest.raises(ExecutionError):
        senza.remove('lizzy', 'version')


def test_traffic(monkeypatch, popen):
    senza = Senza('region')
    senza.logger = MagicMock()
    traffic = senza.traffic('lizzy', 'version42', 25)

    cmd = 'senza traffic --region region -o json lizzy version42 25'
    senza.logger.debug.assert_called_with('Executing %s.', 'senza', extra={'command': cmd})
    assert not senza.logger.error.called
    assert not senza.logger.exception.called

    popen.assert_called_with(['senza', 'traffic', '--region', 'region', '-o', 'json', 'lizzy', 'version42', '25'],
                             stdout=-1,
                             stderr=-1)

    assert traffic == {'stream': 'stdout'}

    # test error case
    popen.side_effect = ExecutionError('', '')

    with pytest.raises(SenzaTrafficError):
        senza.traffic('lizzy', 'version42', 25)


def test_respawn_instances(monkeypatch, popen):
    senza = Senza('region')
    senza.logger = MagicMock()
    senza.respawn_instances('lizzy', 'version42')

    cmd = 'senza respawn-instances --region region -o json lizzy version42'
    senza.logger.debug.assert_called_with('Executing %s.', 'senza',
                                          extra={'command': cmd})
    assert not senza.logger.error.called
    assert not senza.logger.exception.called

    popen.assert_called_with(['senza', 'respawn-instances', '--region',
                             'region', '-o', 'json', 'lizzy', 'version42'],
                             stdout=-1, stderr=-1)

    # test error case
    popen.side_effect = ExecutionError('', '')

    with pytest.raises(SenzaRespawnInstancesError):
        senza.respawn_instances('lizzy', 'version42')


def test_patch(monkeypatch, popen):
    senza = Senza('region')
    senza.logger = MagicMock()
    senza.patch('lizzy', 'version42', 'latest')

    cmd = 'senza patch --region region -o json lizzy version42 --image=latest'
    senza.logger.debug.assert_called_with('Executing %s.', 'senza',
                                          extra={'command': cmd})
    assert not senza.logger.error.called
    assert not senza.logger.exception.called

    popen.assert_called_with(['senza', 'patch', '--region', 'region', '-o',
                             'json', 'lizzy', 'version42', '--image=latest'],
                             stdout=-1, stderr=-1)

    # test error case
    popen.side_effect = ExecutionError('', '')

    with pytest.raises(SenzaPatchError):
        senza.patch('lizzy', 'version42', 'latest')


def test_render_definition(monkeypatch, popen):
    senza = Senza('region')
    senza.logger = MagicMock()

    mock_named_tempfile = MagicMock()
    mock_tempfile = MagicMock()
    mock_tempfile.name = 'lizzy.yaml'
    mock_named_tempfile.__enter__.return_value = mock_tempfile
    mock_named_tempfile.return_value = mock_named_tempfile
    monkeypatch.setattr('tempfile.NamedTemporaryFile', mock_named_tempfile)

    senza.render_definition('yaml content', 'version42', 'imgversion22',
                            ['Param1=app', 'SecondParam=3'])

    cmd = 'senza print --region region -o json --force lizzy.yaml version42 ' \
          'imgversion22 Param1=app SecondParam=3'

    popen.assert_called_with(cmd.split(" "), stdout=-1, stderr=-1)
    assert not senza.logger.error.called

    senza.render_definition('yaml content', None, 'imgversion22',
                            ['Param1=app', 'SecondParam=3'])
    assert not senza.logger.error.called

    # test error case
    popen.side_effect = ExecutionError('', '')

    with pytest.raises(SenzaRenderError):
        senza.render_definition('yaml content', 'version42', 'imgversion22',
                                ['Param1=app', 'SecondParam=3'])


def test_exception():
    try:
        raise ExecutionError(20, '  Output         ')
    except ExecutionError as e:
        assert str(e) == '(20): Output'
