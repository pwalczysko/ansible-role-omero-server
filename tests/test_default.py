import testinfra.utils.ansible_runner
import pytest
import re

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    '.molecule/ansible_inventory').get_hosts('all')

OMERO = '/home/omero/OMERO.server/bin/omero'
OMERO_LOGIN = '-C -s localhost -u root -w omero'


@pytest.mark.parametrize("name", ["omero", "omero-web", "nginx"])
def test_services_running_and_enabled(Service, name):
    service = Service(name)
    assert service.is_running
    assert service.is_enabled


def test_omero_version(Command, Sudo, TestinfraBackend):
    host = TestinfraBackend.get_hostname()
    with Sudo('data-importer'):
        ver = Command.check_output("%s version" % OMERO)
    if host == 'omero-server-ice35':
        assert re.match('\d+\.\d+\.\d+-ice35-', ver)
    else:
        assert re.match('\d+\.\d+\.\d+-ice36-', ver)


def test_omero_root_login(Command, Sudo):
    with Sudo('data-importer'):
        Command.check_output('%s login %s' % (OMERO, OMERO_LOGIN))


def test_inplace_import(Command, File, Sudo):
    with Sudo('data-importer'):
        outimport = Command.check_output(
            '%s %s import -- --transfer=ln_s /data/import/test.fake' %
            (OMERO, OMERO_LOGIN))

    imageid = int(outimport)
    assert imageid

    query = ('SELECT concat(ofile.path, ofile.name) '
             'FROM FilesetEntry AS fse '
             'JOIN fse.fileset AS fileset '
             'JOIN fse.originalFile AS ofile '
             'JOIN fileset.images AS image '
             'WHERE image.id = %d' % imageid)
    with Sudo('data-importer'):
        outhql = Command.check_output(
            '%s %s hql -q --style plain "%s"' % (OMERO, OMERO_LOGIN, query))

    f = File('/OMERO/ManagedRepository/%s' % outhql.split(',', 1)[1])
    assert f.is_symlink
    assert f.linked_to == '/data/import/test.fake'


def test_omero_datadir(File):
    d = File('/OMERO')
    assert d.is_directory
    assert d.user == 'omero'
    assert d.group == 'root'
    assert d.mode == 0o755


def test_omero_managedrepo(File):
    d = File('/OMERO/ManagedRepository')
    assert d.is_directory
    assert d.user == 'omero'
    assert d.group == 'importer'
    assert d.mode == 0o2775
