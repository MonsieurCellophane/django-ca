"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import os
import shutil
import subprocess
import tempfile

from django.test import TestCase
from django.test.utils import override_settings as _override_settings
from django.utils.six.moves import reload_module

from django_ca import ca_settings
from django_ca.models import CertificateAuthority


class override_settings(_override_settings):
    """Enhance override_settings to also reload django_ca.ca_settings."""

    def __call__(self, test_func):
        if isinstance(test_func, type) and not issubclass(test_func, DjangoCATestCase):
            raise Exception("Only subclasses of DjangoCATestCase can use override_settings.")
        inner = super(override_settings, self).__call__(test_func)
        return inner

    def save_options(self, test_func):
        super(override_settings, self).save_options(test_func)
        reload_module(ca_settings)

    def enable(self):
        super(override_settings, self).enable()
        reload_module(ca_settings)

    def disable(self):
        super(override_settings, self).disable()
        reload_module(ca_settings)


class override_tmpcadir(override_settings):
    """Sets the CA_DIR directory to a temporary directory.

    .. NOTE: This also takes any additional settings.
    """

    def __init__(self, **kwargs):
        super(override_tmpcadir, self).__init__(**kwargs)
        self.options['CA_DIR'] = tempfile.mkdtemp()

    def disable(self):
        super(override_tmpcadir, self).disable()
        shutil.rmtree(self.options['CA_DIR'])


class DjangoCATestCase(TestCase):
    """Base class for all testcases with some enhancements."""

    @classmethod
    def setUpClass(cls):
        super(DjangoCATestCase, cls).setUpClass()

        if cls._overridden_settings:
            reload_module(ca_settings)

    def setUp(self):
        reload_module(ca_settings)

    def settings(self, **kwargs):
        return override_settings(**kwargs)

    def tmpcadir(self, **kwargs):
        return override_tmpcadir(**kwargs)

    @classmethod
    def init_ca(cls, **kwargs):
        kwargs.setdefault('key_size', 2048)
        return CertificateAuthority.objects.init(
            name='Root CA', key_type='RSA', algorithm='sha256', expires=720, parent=None, pathlen=0,
            subject={'CN': 'ca.example.com', }, **kwargs)

    def create_csr(self, name='example.com', key_size=512):
        key = os.path.join(ca_settings.CA_DIR, '%s.key' % name)
        csr = os.path.join(ca_settings.CA_DIR, '%s.csr' % name)
        subj = '/C=AT/ST=Vienna/L=Vienna/CN=csr.%s' % name

        p1 = subprocess.Popen(['openssl', 'genrsa', '-out', key, str(key_size)],
                              stderr=subprocess.PIPE)
        p1.communicate()
        p2 = subprocess.Popen(['openssl', 'req', '-new', '-key', key, '-out', csr, '-utf8',
                               '-batch', '-subj', '%s' % subj])
        p2.communicate()
        return key, csr
