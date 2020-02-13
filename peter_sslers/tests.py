from __future__ import print_function

# pyramid
from pyramid import testing
from pyramid.paster import get_appsettings

# pypi
import transaction
from webtest import TestApp
from webtest import Upload
from webtest.http import StopableWSGIServer
import sqlalchemy

# stdlib
import datetime
import json
import os
import sys
import unittest
import re
from io import open  # overwrite `open` in Python2

# local
from .web import main
from .lib import cert_utils
from .lib import db
from .lib import utils

from .model import meta as model_meta
from .model import objects as model_objects
from .model import utils as model_utils


# ==============================================================================

DEFAULT_acme_account_provider = "letsencrypt-v2-staging"

"""
queue tests:
- add existing active domain to queue
- add existing inactive domain to queue
- add non-existing domain to queue
- turn off existing, active domain
- turn off existing, inactive domain
- turn off non-existing, inactive domain
"""

# set these by environment variables,
"""
export SSL_RUN_NGINX_TESTS=True
export SSL_RUN_REDIS_TESTS=True
export SSL_RUN_LETSENCRYPT_API_TESTS=True
export SSL_LETSENCRYPT_API_VALIDATES=True
export SSL_TEST_DOMAINS=dev.cliqued.in  # can be a comma-separated string
export SSL_TEST_PORT=7201

if running letsencrypt tests, you need to specify a domain and make sure to proxy to this app so letsencrypt can access it

see the nginx test config file `testing.conf`

"""
# run tests that expire nginx caches
RUN_NGINX_TESTS = os.environ.get("SSL_RUN_NGINX_TESTS", False)
# run tests to prime redis
RUN_REDIS_TESTS = os.environ.get("SSL_RUN_REDIS_TESTS", False)
# run tests against LE API
RUN_LETSENCRYPT_API_TESTS = os.environ.get("SSL_RUN_LETSENCRYPT_API_TESTS", False)
# does the LE validation work?  LE must be able to reach this
LETSENCRYPT_API_VALIDATES = os.environ.get("SSL_LETSENCRYPT_API_VALIDATES", False)

SSL_TEST_DOMAINS = os.environ.get("SSL_TEST_DOMAINS", "example.com")
SSL_TEST_PORT = int(os.environ.get("SSL_TEST_PORT", 7201))

DISABLE_UNWRITTEN_TESTS = True


# ==============================================================================


DEFAULT_acme_account_provider_id = None
for pvd in model_utils.AcmeAccountProvider.registry.values():
    if pvd["name"] == DEFAULT_acme_account_provider:
        DEFAULT_acme_account_provider_id = pvd["id"]
        break


TEST_FILES = {
    "AcmeAccountKey": {
        "1": "acme_account_1.key",
        "2": "acme_account_2.key",
        "3": "acme_account_3.key",
        "4": "acme_account_4.key",
        "5": "acme_account_5.key",
    },
    "CACertificates": {
        "order": (
            "isrgrootx1",
            "le_x1_auth",
            "le_x2_auth",
            "le_x1_cross_signed",
            "le_x2_cross_signed",
            "le_x3_cross_signed",
            "le_x4_cross_signed",
        ),
        "cert": {
            "isrgrootx1": "isrgrootx1.pem.txt",
            "le_x1_auth": "letsencryptauthorityx1.pem.txt",
            "le_x2_auth": "letsencryptauthorityx2.pem.txt",
            "le_x1_cross_signed": "lets-encrypt-x1-cross-signed.pem.txt",
            "le_x2_cross_signed": "lets-encrypt-x2-cross-signed.pem.txt",
            "le_x3_cross_signed": "lets-encrypt-x3-cross-signed.pem.txt",
            "le_x4_cross_signed": "lets-encrypt-x4-cross-signed.pem.txt",
        },
    },
    "CertificateRequests": {
        "1": {
            "domains": "foo.example.com, bar.example.com",
            "account_key": "account_1.key",
            "private_key": "private_1.key",
        },
        "acme_test": {
            "domains": SSL_TEST_DOMAINS,
            "account_key": "account_2.key",
            "private_key": "private_2.key",
        },
    },
    # the certificates are a tuple of: (CommonName, crt, csr, key)
    "ServerCertificates": {
        "SelfSigned": {
            "1": {
                "domain": "selfsigned-1.example.com",
                "cert": "selfsigned_1-server.crt",
                "csr": "selfsigned_1-server.csr",
                "pkey": "selfsigned_1-server.key",
            },
            "2": {
                "domain": "selfsigned-2.example.com",
                "cert": "selfsigned_2-server.crt",
                "csr": "selfsigned_2-server.csr",
                "pkey": "selfsigned_2-server.key",
            },
            "3": {
                "domain": "selfsigned-3.example.com",
                "cert": "selfsigned_3-server.crt",
                "csr": "selfsigned_3-server.csr",
                "pkey": "selfsigned_3-server.key",
            },
            "4": {
                "domain": "selfsigned-4.example.com",
                "cert": "selfsigned_4-server.crt",
                "csr": "selfsigned_4-server.csr",
                "pkey": "selfsigned_4-server.key",
            },
            "5": {
                "domain": "selfsigned-5.example.com",
                "cert": "selfsigned_5-server.crt",
                "csr": "selfsigned_5-server.csr",
                "pkey": "selfsigned_5-server.key",
            },
        },
        "LetsEncrypt": {},
    },
    "PrivateKey": {
        "1": {
            "file": "private_1.key",
            "key_pem_md5": "462dc10731254d7f5fa7f0e99cbece73",
            "key_pem_modulus_md5": "5d0f596ace3ea1a9ce40dc9b087759a1",
        },
        "2": {
            "file": "private_2.key",
            "key_pem_md5": "cdde9325bdbfe03018e4119549c3a7eb",
            "key_pem_modulus_md5": "db45c5dce9fffbe21fc82a5e26b0bf8e",
        },
        "3": {
            "file": "private_3.key",
            "key_pem_md5": "399236401eb91c168762da425669ad06",
            "key_pem_modulus_md5": "c2b3abfb8fa471977b6df77aafd30bee",
        },
        "4": {
            "file": "private_4.key",
            "key_pem_md5": "6867998790e09f18432a702251bb0e11",
            "key_pem_modulus_md5": "e33389025a223c8a36958dc56de08840",
        },
        "5": {
            "file": "private_5.key",
            "key_pem_md5": "1b13814854d8cee8c64732a2e2f7e73e",
            "key_pem_modulus_md5": "a2ea95b3aa5f5b337ac981c2024bcb3a",
        },
    },
    "Domains": {
        "Queue": {
            "1": {
                "add": "qadd1.example.com, qadd2.example.com, qadd3.example.com",
                "add.json": "qaddjson1.example.com, qaddjson2.example.com, qaddjson3.example.com",
            }
        }
    },
}


class AppTestCore(unittest.TestCase):
    _data_root = None
    testapp = None
    testapp_http = None

    def _filepath_testfile(self, filename):
        return os.path.join(self._data_root, filename)

    def _filedata_testfile(self, filename):
        with open(os.path.join(self._data_root, filename), "rt", encoding="utf-8") as f:
            data = f.read()
        return data

    def setUp(self):
        settings = get_appsettings(
            "test.ini", name="main"
        )  # this can cause an unclosed resource
        # sqlalchemy.url = sqlite:///%(here)s/example_ssl_minnow_test.sqlite
        if False:
            settings["sqlalchemy.url"] = "sqlite://"
        app = main(global_config=None, **settings)
        self.testapp = TestApp(app)
        self._data_root = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "test_data"
        )

    def tearDown(self):
        if self.testapp_http is not None:
            self.testapp_http.shutdown()


class AppTest(AppTestCore):

    _ctx = None
    _DB_INTIALIZED = False

    def setUp(self):
        AppTestCore.setUp(self)
        if not AppTest._DB_INTIALIZED:

            print("---------------")
            print("INITIALIZING DB")
            engine = self.testapp.app.registry["dbSession_factory"]().bind

            model_meta.Base.metadata.drop_all(engine)
            engine.execute("VACUUM")
            model_meta.Base.metadata.create_all(engine)

            try:
                """
                This setup pre-populates the DB with some objects needed for routes to work:

                    AccountKey:
                        account_1.key
                    CACertificates:
                        isrgrootx1.pem.txt
                        selfsigned_1-server.crt
                    PrivateKey
                        selfsigned_1-server.key

                    AcmeEventLog
                """

                #
                # insert AcmeAccountKey
                # this should create `/acme-account-key/1`
                #
                _key_filename = TEST_FILES["AcmeAccountKey"]["1"]
                key_pem = self._filedata_testfile(_key_filename)
                _key_account1, _is_created = db.getcreate.getcreate__AcmeAccountKey(
                    self.ctx,
                    key_pem,
                    acme_account_provider_id=DEFAULT_acme_account_provider_id,
                )
                # print(_key_account1, _is_created)
                self.ctx.dbSession.commit()

                #
                # insert CACertificate
                # this should create `/ca-certificate/1`
                #
                _ca_cert_id = "isrgrootx1"
                _ca_cert_filename = TEST_FILES["CACertificates"]["cert"][_ca_cert_id]
                ca_cert_pem = self._filedata_testfile(_ca_cert_filename)
                (
                    _ca_cert_1,
                    _is_created,
                ) = db.getcreate.getcreate__CACertificate__by_pem_text(
                    self.ctx,
                    ca_cert_pem,
                    ca_chain_name="ISRG Root",
                    le_authority_name="ISRG ROOT",
                    is_authority_certificate=True,
                    is_cross_signed_authority_certificate=False,
                )
                # print(_ca_cert_1, _is_created)
                self.ctx.dbSession.commit()

                #
                # insert CACertificate - self signed
                # this should create `/ca-certificate/2`
                #
                _ca_cert_filename = TEST_FILES["ServerCertificates"]["SelfSigned"]["1"][
                    "cert"
                ]
                ca_cert_pem = self._filedata_testfile(_ca_cert_filename)
                (
                    _ca_cert_selfsigned1,
                    _is_created,
                ) = db.getcreate.getcreate__CACertificate__by_pem_text(
                    self.ctx, ca_cert_pem, ca_chain_name=_ca_cert_filename
                )
                # print(_ca_cert_selfsigned1, _is_created)
                self.ctx.dbSession.commit()

                #
                # insert PrivateKey
                # this should create `/private-key/1`
                #
                _pkey_filename = TEST_FILES["ServerCertificates"]["SelfSigned"]["1"][
                    "pkey"
                ]
                pkey_pem = self._filedata_testfile(_pkey_filename)
                (
                    _key_private1,
                    _is_created,
                ) = db.getcreate.getcreate__PrivateKey__by_pem_text(self.ctx, pkey_pem)
                # print(_key_private1, _is_created)
                self.ctx.dbSession.commit()

                #
                # insert ServerCertificate
                # this should create `/certificate/1`
                #
                _cert_filename = TEST_FILES["ServerCertificates"]["SelfSigned"]["1"][
                    "cert"
                ]
                cert_pem = self._filedata_testfile(_cert_filename)
                (
                    _cert_1,
                    _is_created,
                ) = db.getcreate.getcreate__ServerCertificate__by_pem_text(
                    self.ctx,
                    cert_pem,
                    dbCACertificate=_ca_cert_selfsigned1,
                    dbAcmeAccountKey=_key_account1,
                    dbPrivateKey=_key_private1,
                )
                # print(_cert_1, _is_created)
                self.ctx.dbSession.commit()

                # ensure we have domains?
                domains = db.get.get__Domain__paginated(self.ctx)
                domain_names = [d.domain_name for d in domains]
                assert (
                    TEST_FILES["ServerCertificates"]["SelfSigned"]["1"][
                        "domain"
                    ].lower()
                    in domain_names
                )

                # this shouldn't need to be handled here, because creating a cert would populate this table
                if False:
                    # insert a domain name
                    # one should be extracted from uploading a ServerCertificate though
                    (
                        _domain,
                        _is_created,
                    ) = db.getcreate.getcreate__Domain__by_domainName(
                        self.ctx, "www.example.com"
                    )
                    self.ctx.dbSession.commit()

                    # insert a domain name
                    # one should be extracted from uploading a ServerCertificate though
                    # getcreate__UniqueFQDNSet__by_domainObjects

                # upload a csr
                _csr_filename = TEST_FILES["ServerCertificates"]["SelfSigned"]["1"][
                    "csr"
                ]
                csr_pem = self._filedata_testfile(_csr_filename)
                (
                    _csr_1,
                    _is_created,
                ) = db.getcreate.getcreate__CertificateRequest__by_pem_text(
                    self.ctx,
                    csr_pem,
                    certificate_request_source_id=model_utils.CertificateRequestSource.ACME_FLOW,
                    dbPrivateKey=_key_private1,
                )
                self.ctx.dbSession.commit()

                # AcmeEventLog
                dbAcmeEventLog = model_objects.AcmeEventLog()
                dbAcmeEventLog.timestamp_event = datetime.datetime.utcnow()
                dbAcmeEventLog.acme_event_id = model_utils.AcmeEvent.from_string(
                    "v1|/acme/new-reg"
                )
                self.ctx.dbSession.add(dbAcmeEventLog)
                self.ctx.dbSession.flush()
                self.ctx.dbSession.commit()

                # AcmeChallenge
                dbAcmeChallenge = model_objects.AcmeChallenge()
                dbAcmeChallenge.timestamp_created = datetime.datetime.utcnow()
                dbAcmeChallenge.acme_event_log_id = dbAcmeEventLog.id
                dbAcmeChallenge.domain = "example.com"
                dbAcmeChallenge.acme_account_key_id = _key_account1.id
                self.ctx.dbSession.add(dbAcmeChallenge)
                self.ctx.dbSession.flush()
                self.ctx.dbSession.commit()

                # queue a domain
                # this MUST be a new domain to add to the queue
                # if it is existing, a domain will not be added
                db.queues.queue_domains__add(self.ctx, ["queue.example.com"])
                self.ctx.dbSession.commit()

                # renew a csr
                # this MUST be a new domain to add to the queue
                # if it is existing, a domain will not be added
                event_type = model_utils.OperationsEventType.from_string(
                    "queue_renewal__update"
                )
                event_payload_dict = utils.new_event_payload_dict()
                dbOperationsEvent = db.logger.log__OperationsEvent(
                    self.ctx, event_type, event_payload_dict
                )
                dbQueue = db.create._create__QueueRenewal(self.ctx, _cert_1)
                self.ctx.dbSession.commit()

            except Exception as exc:
                print("")
                print("")
                print("")
                print("EXCEPTION IN SETUP")
                print("")
                print(exc)
                print("")
                print("")
                print("")
                raise
            print("DB INITIALIZED")
            AppTest._DB_INTIALIZED = True

    def tearDown(self):
        AppTestCore.tearDown(self)
        if self._ctx is not None:
            self._ctx.dbSession.close()

    @property
    def ctx(self):
        if self._ctx is None:
            dbSession_factory = self.testapp.app.registry["dbSession_factory"]
            dbSessionLogger_factory = self.testapp.app.registry[
                "dbSessionLogger_factory"
            ]
            self._ctx = utils.ApiContext(
                dbSession=dbSession_factory(),
                dbSessionLogger=dbSessionLogger_factory(),
                timestamp=datetime.datetime.utcnow(),
            )
        return self._ctx


class UnitTestOpenSSL(AppTestCore):
    """python -m unittest peter_sslers.tests.UnitTestOpenSSL"""

    def test_modulus_PrivateKey(self):
        for pkey_set_id, set_data in TEST_FILES["PrivateKey"].items():
            pem_filepath = self._filepath_testfile(set_data["file"])
            _computed_modulus_md5 = cert_utils.modulus_md5_key__pem_filepath(
                pem_filepath
            )
            _expected_modulus_md5 = set_data["key_pem_modulus_md5"]
            assert _computed_modulus_md5 == _expected_modulus_md5
            _computed_md5 = utils.md5_text(self._filedata_testfile(pem_filepath))
            _expected_md5 = set_data["key_pem_md5"]
            assert _computed_md5 == _expected_md5


class UnitTestCSR(AppTestCore):
    """python -m unittest peter_sslers.tests.UnitTestCSR"""

    def test_AcmeV2_Automated(self):
        """
        test some flows that trigger different challenge/auth scenarios
        """
        raise ValueError("test this")
        ctx = ""
        domain_names = TEST_FILES["CertificateRequests"]["1"]["domains"]
        dbAcmeAccountKey = (None,)
        dbPrivateKey = (None,)
        private_key_pem = (None,)
        dbAcmeOrder = db.actions_acme.do__AcmeOrder__AcmeV2__automated(
            ctx,
            domain_names=domain_names,
            dbAcmeAccountKey=None,
            dbPrivateKey=None,
            dbServerCertificate__renewal_of=None,
            dbQueueRenewal__of=None,
        )


class FunctionalTests_Main(AppTest):
    """
    python -m unittest peter_sslers.tests.FunctionalTests_Main
    """

    def test_root(self):
        res = self.testapp.get("/.well-known/admin", status=200)

    def test_whoami(self):
        res = self.testapp.get("/.well-known/admin/whoami", status=200)

    def test_help(self):
        res = self.testapp.get("/.well-known/admin/help", status=200)

    def test_settings(self):
        res = self.testapp.get("/.well-known/admin/settings", status=200)

    def test_api_docs(self):
        res = self.testapp.get("/.well-known/admin/api", status=200)

    def test_search(self):
        res = self.testapp.get("/.well-known/admin/search", status=200)


class FunctionalTests_Passes(AppTest):
    """
    python -m unittest peter_sslers.tests.FunctionalTests_Passes
    this is only used to test setup
    """

    def tests_passes(self):
        return True


class FunctionalTests_AcmeEventLog(AppTest):
    """python -m unittest peter_sslers.tests.FunctionalTests_AcmeEventLog"""

    def _get_item(self):
        # grab an event
        focus_item = self.ctx.dbSession.query(model_objects.AcmeEventLog).first()
        return focus_item

    def test_list(self):
        # root
        res = self.testapp.get("/.well-known/admin/acme-event-logs", status=200)
        # paginated
        res = self.testapp.get("/.well-known/admin/acme-event-logs/1", status=200)

    def test_focus(self):
        # focus
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id
        res = self.testapp.get(
            "/.well-known/admin/acme-event-log/%s" % focus_id, status=200
        )


class FunctionalTests_AcmeProviders(AppTest):
    """python -m unittest peter_sslers.tests.FunctionalTests_AcmeProviders"""

    def test_list(self):
        # root
        res = self.testapp.get("/.well-known/admin/acme-providers", status=200)

        # json root
        res = self.testapp.get("/.well-known/admin/acme-providers.json", status=200)
        res_json = json.loads(res.body)
        assert "AcmeProviders" in res_json


class FunctionalTests_AccountKeys(AppTest):
    """python -m unittest peter_sslers.tests.FunctionalTests_AccountKeys"""

    """python -m unittest peter_sslers.tests.FunctionalTests_AccountKeys.test_new"""

    def _get_item(self):
        # grab a Key
        focus_item = (
            self.ctx.dbSession.query(model_objects.AcmeAccountKey)
            .filter(model_objects.AcmeAccountKey.is_active.op("IS")(True))
            .order_by(model_objects.AcmeAccountKey.id.asc())
            .first()
        )
        return focus_item

    def test_list(self):
        # root
        res = self.testapp.get("/.well-known/admin/acme-account-keys", status=200)
        # paginated
        res = self.testapp.get("/.well-known/admin/acme-account-keys/1", status=200)

        # json root
        res = self.testapp.get("/.well-known/admin/acme-account-keys.json", status=200)
        # json paginated
        res = self.testapp.get(
            "/.well-known/admin/acme-account-keys/1.json", status=200
        )

    def test_focus(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id

        res = self.testapp.get(
            "/.well-known/admin/acme-account-key/%s" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/acme-account-key/%s.json" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/acme-account-key/%s/config.json" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/acme-account-key/%s/parse.json" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/acme-account-key/%s/key.key" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/acme-account-key/%s/key.pem" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/acme-account-key/%s/key.pem.txt" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/acme-account-key/%s/certificate-requests" % focus_id,
            status=200,
        )
        res = self.testapp.get(
            "/.well-known/admin/acme-account-key/%s/certificate-requests/1" % focus_id,
            status=200,
        )
        res = self.testapp.get(
            "/.well-known/admin/acme-account-key/%s/certificates" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/acme-account-key/%s/certificates/1" % focus_id,
            status=200,
        )

    def test_manipulate(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id

        # TODO:
        # config.add_route_7('admin:acme_account_key:focus:authenticate', '/acme-account-key/{@id}/authenticate')

        if not focus_item.is_default:
            # make sure to roundtrip!
            # note we expect a 303 on success!
            if focus_item.is_active:
                res = self.testapp.get(
                    "/.well-known/admin/acme-account-key/%s/mark" % focus_id,
                    {"action": "inactive"},
                    status=303,
                )
                res = self.testapp.get(
                    "/.well-known/admin/acme-account-key/%s/mark.json" % focus_id,
                    {"action": "active"},
                    status=200,
                )
            else:
                res = self.testapp.get(
                    "/.well-known/admin/acme-account-key/%s/mark" % focus_id,
                    {"action": "active"},
                    status=303,
                )
                res = self.testapp.get(
                    "/.well-known/admin/acme-account-key/%s/mark.json" % focus_id,
                    {"action": "inactive"},
                    status=200,
                )
        else:
            # TODO
            print("MUST TEST non-default")

    def test_new(self):
        # this should be creating a new key
        _key_filename = TEST_FILES["AcmeAccountKey"]["2"]
        key_filepath = self._filepath_testfile(_key_filename)

        res = self.testapp.get("/.well-known/admin/acme-account-key/upload", status=200)
        form = res.form
        form["account_key_file_pem"] = Upload(key_filepath)
        form["acme_account_provider_id"].force_value(
            str(DEFAULT_acme_account_provider_id)
        )  # why aren't any valid options showing?'
        res2 = form.submit()
        assert res2.status_code == 303
        assert res2.location in (
            """http://localhost/.well-known/admin/acme-account-key/2?result=success&is_created=1""",
            """http://localhost:80/.well-known/admin/acme-account-key/2?result=success&is_created=1""",
        )
        res3 = self.testapp.get(res2.location, status=200)

        res = self.testapp.get(
            "/.well-known/admin/acme-account-key/upload.json", status=200
        )
        res_json = json.loads(res.body)
        assert "instructions" in res_json

        form = {}
        form["account_key_file_pem"] = Upload(key_filepath)
        form["acme_account_provider_id"] = str(DEFAULT_acme_account_provider_id)
        res2 = self.testapp.post(
            "/.well-known/admin/acme-account-key/upload.json", form
        )
        assert res2.status_code == 200
        res2_json = json.loads(res2.body)
        assert "result" in res2_json
        assert res2_json["result"] == "success"

    @unittest.skipUnless(
        RUN_LETSENCRYPT_API_TESTS, "not running against letsencrypt api"
    )
    def tests_letsencrypt_api(self):
        # this hits LE
        res = self.testapp.get(
            "/.well-known/admin/acme-account-key/1/authenticate", status=303
        )
        assert (
            res.location
            == "http://localhost/.well-known/admin/acme-account-key/1?operation=authenticate&result=post+required"
        )
        res = self.testapp.post(
            "/.well-known/admin/acme-account-key/1/authenticate", {}
        )
        assert res.location in (
            """http://localhost/.well-known/admin/acme-account-key/1?result=success&is_authenticated=existing-account""",
            """http://localhost/.well-known/admin/acme-account-key/1?result=success&is_authenticated=new-account""",
        )

        res = self.testapp.get(
            "/.well-known/admin/acme-account-key/1/authenticate.json", status=200
        )
        res = self.testapp.post(
            "/.well-known/admin/acme-account-key/1/authenticate.json", {}
        )
        assert res.status == 200


class FunctionalTests_CACertificate(AppTest):
    """python -m unittest peter_sslers.tests.FunctionalTests_CACertificate"""

    """python -m unittest peter_sslers.tests.FunctionalTests_CACertificate.test_upload"""

    def test_list(self):
        # root
        res = self.testapp.get("/.well-known/admin/ca-certificates", status=200)
        # paginated
        res = self.testapp.get("/.well-known/admin/ca-certificates/1", status=200)

        # JSON root
        res = self.testapp.get("/.well-known/admin/ca-certificates.json", status=200)
        # JSON paginated
        res = self.testapp.get("/.well-known/admin/ca-certificates/1.json", status=200)

    def test_focus(self):
        res = self.testapp.get("/.well-known/admin/ca-certificate/1", status=200)
        res = self.testapp.get("/.well-known/admin/ca-certificate/1.json", status=200)
        res = self.testapp.get(
            "/.well-known/admin/ca-certificate/1/parse.json", status=200
        )

        res = self.testapp.get(
            "/.well-known/admin/ca-certificate/1/chain.cer", status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/ca-certificate/1/chain.crt", status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/ca-certificate/1/chain.der", status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/ca-certificate/1/chain.pem", status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/ca-certificate/1/chain.pem.txt", status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/ca-certificate/1/certificates-signed", status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/ca-certificate/1/certificates-signed/1", status=200
        )

    def test_upload(self):
        """This should enter in item #3, but the CACertificates.order is 1; the other cert is a self-signed"""
        _ca_cert_id = TEST_FILES["CACertificates"]["order"][1]
        _ca_cert_filename = TEST_FILES["CACertificates"]["cert"][_ca_cert_id]
        _ca_cert_filepath = self._filepath_testfile(_ca_cert_filename)

        res = self.testapp.get("/.well-known/admin/ca-certificate/upload", status=200)
        form = res.form
        form["chain_file"] = Upload(_ca_cert_filepath)
        res2 = form.submit()
        assert res2.status_code == 303
        assert (
            res2.location
            == """http://localhost/.well-known/admin/ca-certificate/3?result=success&is_created=1"""
        )
        res3 = self.testapp.get(res2.location, status=200)

        """This should enter in item #4"""
        _ca_cert_id = TEST_FILES["CACertificates"]["order"][2]
        _ca_cert_filename = TEST_FILES["CACertificates"]["cert"][_ca_cert_id]
        _ca_cert_filepath = self._filepath_testfile(_ca_cert_filename)

        res = self.testapp.get(
            "/.well-known/admin/ca-certificate/upload.json", status=200
        )
        _data = {"chain_file": Upload(_ca_cert_filepath)}
        res2 = self.testapp.post("/.well-known/admin/ca-certificate/upload.json", _data)
        assert res2.status_code == 200
        res2_json = json.loads(res2.body)
        assert res2_json["result"] == "success"
        assert res2_json["ca_certificate"]["id"] == 4
        assert res2_json["ca_certificate"]["created"] is True
        res3 = self.testapp.get("/.well-known/admin/ca-certificate/4", status=200)

        # try a bundle
        res = self.testapp.get(
            "/.well-known/admin/ca-certificate/upload-bundle", status=200
        )
        form = res.form
        form["isrgrootx1_file"] = Upload(
            self._filepath_testfile(TEST_FILES["CACertificates"]["cert"]["isrgrootx1"])
        )
        form["le_x1_auth_file"] = Upload(
            self._filepath_testfile(TEST_FILES["CACertificates"]["cert"]["le_x1_auth"])
        )
        form["le_x2_auth_file"] = Upload(
            self._filepath_testfile(TEST_FILES["CACertificates"]["cert"]["le_x2_auth"])
        )
        form["le_x1_cross_signed_file"] = Upload(
            self._filepath_testfile(
                TEST_FILES["CACertificates"]["cert"]["le_x1_cross_signed"]
            )
        )
        form["le_x2_cross_signed_file"] = Upload(
            self._filepath_testfile(
                TEST_FILES["CACertificates"]["cert"]["le_x2_cross_signed"]
            )
        )
        form["le_x3_cross_signed_file"] = Upload(
            self._filepath_testfile(
                TEST_FILES["CACertificates"]["cert"]["le_x3_cross_signed"]
            )
        )
        form["le_x4_cross_signed_file"] = Upload(
            self._filepath_testfile(
                TEST_FILES["CACertificates"]["cert"]["le_x4_cross_signed"]
            )
        )
        res2 = form.submit()
        assert res2.status_code == 303
        assert (
            res2.location
            == """http://localhost/.well-known/admin/ca-certificates?uploaded=1"""
        )
        res3 = self.testapp.get(res2.location, status=200)

        res = self.testapp.get(
            "/.well-known/admin/ca-certificate/upload-bundle.json", status=200
        )
        chain_filepath = self._filepath_testfile("lets-encrypt-x1-cross-signed.pem.txt")
        form = {}
        form["isrgrootx1_file"] = Upload(
            self._filepath_testfile(TEST_FILES["CACertificates"]["cert"]["isrgrootx1"])
        )
        form["le_x1_auth_file"] = Upload(
            self._filepath_testfile(TEST_FILES["CACertificates"]["cert"]["le_x1_auth"])
        )
        form["le_x2_auth_file"] = Upload(
            self._filepath_testfile(TEST_FILES["CACertificates"]["cert"]["le_x2_auth"])
        )
        form["le_x1_cross_signed_file"] = Upload(
            self._filepath_testfile(
                TEST_FILES["CACertificates"]["cert"]["le_x1_cross_signed"]
            )
        )
        form["le_x2_cross_signed_file"] = Upload(
            self._filepath_testfile(
                TEST_FILES["CACertificates"]["cert"]["le_x2_cross_signed"]
            )
        )
        form["le_x3_cross_signed_file"] = Upload(
            self._filepath_testfile(
                TEST_FILES["CACertificates"]["cert"]["le_x3_cross_signed"]
            )
        )
        form["le_x4_cross_signed_file"] = Upload(
            self._filepath_testfile(
                TEST_FILES["CACertificates"]["cert"]["le_x4_cross_signed"]
            )
        )
        res2 = self.testapp.post(
            "/.well-known/admin/ca-certificate/upload-bundle.json", form
        )
        assert res2.status_code == 200
        res2_json = json.loads(res2.body)
        assert res2_json["result"] == "success"
        # this is going to be too messy to check all the vars
        # {u'isrgrootx1_pem': {u'id': 5, u'created': False}, u'le_x2_auth_pem': {u'id': 3, u'created': False}, u'le_x4_cross_signed_pem': {u'id': 6, u'created': False}, u'le_x2_cross_signed_pem': {u'id': 7, u'created': False}, u'le_x3_cross_signed_pem': {u'id': 8, u'created': False}, u'result': u'success', u'le_x1_cross_signed_pem': {u'id': 4, u'created': False}, u'le_x1_auth_pem': {u'id': 1, u'created': False}}


class FunctionalTests_Certificate(AppTest):
    """python -m unittest peter_sslers.tests.FunctionalTests_Certificate"""

    def _get_item(self):
        # grab a certificate
        focus_item = (
            self.ctx.dbSession.query(model_objects.ServerCertificate)
            .filter(model_objects.ServerCertificate.is_active.op("IS")(True))
            .order_by(model_objects.ServerCertificate.id.asc())
            .first()
        )
        return focus_item

    def test_list(self):
        # root
        res = self.testapp.get("/.well-known/admin/certificates", status=200)
        res = self.testapp.get("/.well-known/admin/certificates/expiring", status=200)
        # paginated
        res = self.testapp.get("/.well-known/admin/certificates/1", status=200)
        res = self.testapp.get("/.well-known/admin/certificates/expiring/1", status=200)

        # json
        res = self.testapp.get("/.well-known/admin/certificates.json", status=200)
        res = self.testapp.get(
            "/.well-known/admin/certificates/expiring.json", status=200
        )
        res = self.testapp.get("/.well-known/admin/certificates/1.json", status=200)
        res = self.testapp.get(
            "/.well-known/admin/certificates/expiring/1.json", status=200
        )

    def test_focus(self):
        focus_item = self._get_item()
        if focus_item is None:
            raise ValueError(
                """This test currently fails when the ENTIRE SUITE is run """
                """because `FunctionalTests_API.tests_manipulate` will """
                """deactivate the certificate. Try running this test or """
                """this tests's class directly to ensure a pass."""
            )
        focus_id = focus_item.id

        res = self.testapp.get(
            "/.well-known/admin/certificate/%s" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/config.json" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/parse.json" % focus_id, status=200
        )

        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/chain.cer" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/chain.crt" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/chain.der" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/chain.pem" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/chain.pem.txt" % focus_id, status=200
        )

        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/fullchain.pem" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/fullchain.pem.txt" % focus_id, status=200
        )

        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/privkey.key" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/privkey.pem" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/privkey.pem.txt" % focus_id, status=200
        )

        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/cert.crt" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/cert.pem" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/cert.pem.txt" % focus_id, status=200
        )

        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/renew/queue" % focus_id, status=303
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/renew/queue.json" % focus_id, status=200
        )

        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/renew/quick" % focus_id, status=303
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/renew/quick.json" % focus_id, status=200
        )

        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/renew/custom" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/renew/custom.json" % focus_id, status=200
        )

    def test_manipulate(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id

        if not focus_item.is_revoked:
            # make sure to roundtrip!
            # note we expect a 303 on success!
            if focus_item.is_active:
                res = self.testapp.get(
                    "/.well-known/admin/certificate/%s/mark" % focus_id,
                    {"action": "inactive"},
                    status=303,
                )
                res = self.testapp.get(
                    "/.well-known/admin/certificate/%s/mark.json" % focus_id,
                    {"action": "active"},
                    status=200,
                )
            else:
                res = self.testapp.get(
                    "/.well-known/admin/certificate/%s/mark" % focus_id,
                    {"action": "active"},
                    status=303,
                )
                res = self.testapp.get(
                    "/.well-known/admin/certificate/%s/mark.json" % focus_id,
                    {"action": "inactive"},
                    status=200,
                )
        else:
            # TODO
            print("MUST TEST revoked")

        #
        # upload a new cert
        #
        res = self.testapp.get("/.well-known/admin/certificate/upload", status=200)
        _SelfSigned_id = "1"
        form = res.form
        form["certificate_file"] = Upload(
            self._filepath_testfile(
                TEST_FILES["ServerCertificates"]["SelfSigned"][_SelfSigned_id]["cert"]
            )
        )
        form["chain_file"] = Upload(
            self._filepath_testfile(
                TEST_FILES["ServerCertificates"]["SelfSigned"][_SelfSigned_id]["cert"]
            )
        )
        form["private_key_file_pem"] = Upload(
            self._filepath_testfile(
                TEST_FILES["ServerCertificates"]["SelfSigned"][_SelfSigned_id]["pkey"]
            )
        )
        res2 = form.submit()
        assert res2.status_code == 303
        assert res2.location.startswith(
            """http://localhost/.well-known/admin/certificate/"""
        )

        res = self.testapp.get("/.well-known/admin/certificate/upload.json", status=200)
        chain_filepath = self._filepath_testfile("lets-encrypt-x1-cross-signed.pem.txt")
        _SelfSigned_id = "2"
        form = {}
        form["certificate_file"] = Upload(
            self._filepath_testfile(
                TEST_FILES["ServerCertificates"]["SelfSigned"][_SelfSigned_id]["cert"]
            )
        )
        form["chain_file"] = Upload(
            self._filepath_testfile(
                TEST_FILES["ServerCertificates"]["SelfSigned"][_SelfSigned_id]["cert"]
            )
        )
        form["private_key_file_pem"] = Upload(
            self._filepath_testfile(
                TEST_FILES["ServerCertificates"]["SelfSigned"][_SelfSigned_id]["pkey"]
            )
        )
        res2 = self.testapp.post("/.well-known/admin/certificate/upload.json", form)
        assert res2.status_code == 200
        res2_json = json.loads(res2.body)
        assert res2_json["result"] == "success"
        assert res2_json["certificate"]["created"] is True
        certificate_id = res2_json["certificate"]["id"]
        res3 = self.testapp.get(
            "/.well-known/admin/certificate/%s" % certificate_id, status=200
        )

    @unittest.skipUnless(
        RUN_LETSENCRYPT_API_TESTS, "not running against letsencrypt api"
    )
    def tests_letsencrypt_api(self):
        if DISABLE_UNWRITTEN_TESTS:
            return True
        raise NotImplementedError()
        # config.add_route_7('admin:certificate:focus:renew:quick', '/certificate/{@id}/renew/quick')
        # config.add_route_7('admin:certificate:focus:renew:quick.json', '/certificate/{@id}/renew/quick.json')
        # config.add_route_7('admin:certificate:focus:renew:custom', '/certificate/{@id}/renew/custom')
        # config.add_route_7('admin:certificate:focus:renew:custom.json', '/certificate/{@id}/renew/custom.json')

    @unittest.skipUnless(RUN_NGINX_TESTS, "not running against nginx")
    def tests_nginx(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id

        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/nginx-cache-expire" % focus_id,
            status=303,
        )
        assert (
            "/.well-known/admin/certificate/%s?operation=nginx_cache_expire&result=success&event.id="
            % focus_id
            in res.location
        )

        res = self.testapp.get(
            "/.well-known/admin/certificate/%s/nginx-cache-expire.json" % focus_id,
            status=200,
        )
        res_json = json.loads(res.body)
        assert res_json["result"] == "success"


class FunctionalTests_CertificateRequest(AppTest):
    """python -m unittest peter_sslers.tests.FunctionalTests_CertificateRequest"""

    def _get_item(self):
        # grab a certificate
        focus_item = (
            self.ctx.dbSession.query(model_objects.CertificateRequest)
            .filter(model_objects.CertificateRequest.is_active.op("IS")(True))
            .order_by(model_objects.CertificateRequest.id.asc())
            .first()
        )
        return focus_item

    def test_list(self):
        # root
        res = self.testapp.get("/.well-known/admin/certificate-requests", status=200)

        # paginated
        res = self.testapp.get("/.well-known/admin/certificate-requests/1", status=200)

        # root
        res = self.testapp.get(
            "/.well-known/admin/certificate-requests.json", status=200
        )

        # paginated
        res = self.testapp.get(
            "/.well-known/admin/certificate-requests/1.json", status=200
        )

    def test_focus(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id

        res = self.testapp.get(
            "/.well-known/admin/certificate-request/%s" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate-request/%s.json" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate-request/%s/csr.csr" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate-request/%s/csr.pem" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/certificate-request/%s/csr.pem.txt" % focus_id,
            status=200,
        )

    @unittest.skipUnless(
        RUN_LETSENCRYPT_API_TESTS, "not running against letsencrypt api"
    )
    def tests_letsencrypt_api(self):
        self.testapp_http = StopableWSGIServer.create(
            self.testapp.app, port=SSL_TEST_PORT
        )
        self.testapp_http.wait()
        res = self.testapp.get(
            "/.well-known/admin/acme-order/new/automated", status=200
        )
        form = res.form
        form["account_key_file_pem"] = Upload(
            self._filepath_testfile(
                TEST_FILES["CertificateRequests"]["acme_test"]["account_key"]
            )
        )
        form["private_key_file_pem"] = Upload(
            self._filepath_testfile(
                TEST_FILES["CertificateRequests"]["acme_test"]["private_key"]
            )
        )
        form["domain_names"] = TEST_FILES["CertificateRequests"]["acme_test"]["domains"]
        res2 = form.submit()
        assert res2.status_code == 303
        if not LETSENCRYPT_API_VALIDATES:
            if (
                "/.well-known/admin/certificate-requests?error=new-AcmeAutomated&message=Wrote keyauth challenge, but couldn't download"
                not in res2.location
            ):
                raise ValueError("Expected an error: failure to validate")
        else:
            if (
                "/.well-known/admin/certificate-requests?error=new-AcmeAutomated&message=Wrote keyauth challenge, but couldn't download"
                in res2.location
            ):
                raise ValueError("Failed to validate domain")
            if "/.well-known/admin/certificate/2" not in res2.location:
                raise ValueError("Expected certificate/2")

    def tests_acme_flow(self):
        res = self.testapp.get("/.well-known/admin/acme-flow/new", status=200)
        form = res.form
        form["domain_names"] = TEST_FILES["CertificateRequests"]["1"]["domains"]
        res2 = form.submit()
        assert res2.status_code == 303
        re_expected = re.compile(
            r"""^http://localhost/\.well-known/admin/certificate-request/(\d+)/acme-flow/manage$"""
        )
        matched = re_expected.match(res2.location)
        assert matched
        url_id = matched.groups()[0]

        # make sure we can get this
        res = self.testapp.get(
            "/.well-known/admin/certificate-request/%s/acme-flow/manage" % url_id,
            status=200,
        )
        domains = [
            i.strip().lower()
            for i in TEST_FILES["CertificateRequests"]["1"]["domains"].split(",")
        ]
        for _domain in domains:
            res = self.testapp.get(
                "/.well-known/admin/certificate-request/%s/acme-flow/manage/domain/%s"
                % (url_id, _domain),
                status=200,
            )
            form = res.form
            form["challenge_key"] = "foo"
            form["challenge_text"] = "foo"
            res2 = form.submit()
            # we're not sure what the domain id is, so just check the location
            assert "?result=success" in res2.location

        # deactivate!
        res = self.testapp.get(
            "/.well-known/admin/certificate-request/%s/acme-flow/deactivate" % url_id,
            status=303,
        )
        assert "?result=success" in res.location

        res = self.testapp.get(
            "/.well-known/admin/certificate-request/%s/acme-flow/deactivate.json"
            % url_id,
            status=200,
        )


class FunctionalTests_Domain(AppTest):
    """python -m unittest peter_sslers.tests.FunctionalTests_Domain"""

    def _get_item(self):
        # grab a certificate
        focus_item = (
            self.ctx.dbSession.query(model_objects.Domain)
            .filter(model_objects.Domain.is_active.op("IS")(True))
            .order_by(model_objects.Domain.id.asc())
            .first()
        )
        return focus_item

    def test_list(self):
        # root
        res = self.testapp.get("/.well-known/admin/domains", status=200)
        res = self.testapp.get("/.well-known/admin/domains/expiring", status=200)

        # paginated
        res = self.testapp.get("/.well-known/admin/domains/1", status=200)
        res = self.testapp.get("/.well-known/admin/domains/expiring/1", status=200)

        # json root
        res = self.testapp.get("/.well-known/admin/domains.json", status=200)
        res = self.testapp.get("/.well-known/admin/domains/expiring.json", status=200)

        # json paginated
        res = self.testapp.get("/.well-known/admin/domains/1.json", status=200)
        res = self.testapp.get("/.well-known/admin/domains/expiring/1.json", status=200)

    def test_focus(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id
        focus_name = focus_item.domain_name

        res = self.testapp.get("/.well-known/admin/domain/%s" % focus_id, status=200)
        res = self.testapp.get("/.well-known/admin/domain/%s" % focus_name, status=200)

        res = self.testapp.get(
            "/.well-known/admin/domain/%s.json" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/domain/%s.json" % focus_name, status=200
        )

        res = self.testapp.get(
            "/.well-known/admin/domain/%s/config.json" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/domain/%s/calendar.json" % focus_id, status=200
        )

        res = self.testapp.get(
            "/.well-known/admin/domain/%s/certificates" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/domain/%s/certificates/1" % focus_id, status=200
        )

        res = self.testapp.get(
            "/.well-known/admin/domain/%s/certificate-requests" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/domain/%s/certificate-requests/1" % focus_id, status=200
        )

        res = self.testapp.get(
            "/.well-known/admin/domain/%s/unique-fqdn-sets" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/domain/%s/unique-fqdn-sets/1" % focus_id, status=200
        )

    def test_manipulate(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id

        # make sure to roundtrip!
        # note we expect a 303 on success!
        if focus_item.is_active:
            res = self.testapp.get(
                "/.well-known/admin/domain/%s/mark" % focus_id,
                {"action": "inactive"},
                status=303,
            )
            res = self.testapp.get(
                "/.well-known/admin/domain/%s/mark.json" % focus_id,
                {"action": "active"},
                status=200,
            )
        else:
            res = self.testapp.get(
                "/.well-known/admin/domain/%s/mark" % focus_id,
                {"action": "active"},
                status=303,
            )
            res = self.testapp.get(
                "/.well-known/admin/domain/%s/mark.json" % focus_id,
                {"action": "inactive"},
                status=200,
            )

    @unittest.skipUnless(RUN_NGINX_TESTS, "not running against nginx")
    def tests_nginx(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id
        focus_name = focus_item.domain_name

        res = self.testapp.get(
            "/.well-known/admin/domain/%s/nginx-cache-expire" % focus_id, status=303
        )
        assert (
            "/.well-known/admin/domain/%s?operation=nginx_cache_expire&result=success&event.id="
            % focus_id
            in res.location
        )

        res = self.testapp.get(
            "/.well-known/admin/domain/%s/nginx-cache-expire.json" % focus_id,
            status=200,
        )
        res_json = json.loads(res.body)
        assert res_json["result"] == "success"

    def test_search(self):
        res = self.testapp.get("/.well-known/admin/domains/search", status=200)
        res2 = self.testapp.post(
            "/.well-known/admin/domains/search", {"domain": "example.com"}
        )

        res = self.testapp.get("/.well-known/admin/domains/search.json", status=200)
        res2 = self.testapp.post(
            "/.well-known/admin/domains/search.json", {"domain": "example.com"}
        )


class FunctionalTests_PrivateKeys(AppTest):
    """python -m unittest peter_sslers.tests.FunctionalTests_PrivateKeys"""

    def _get_item(self):
        # grab a Key
        focus_item = (
            self.ctx.dbSession.query(model_objects.PrivateKey)
            .filter(model_objects.PrivateKey.is_active.op("IS")(True))
            .order_by(model_objects.PrivateKey.id.asc())
            .first()
        )
        return focus_item

    def test_list(self):
        # root
        res = self.testapp.get("/.well-known/admin/private-keys", status=200)
        # paginated
        res = self.testapp.get("/.well-known/admin/private-keys/1", status=200)

    def test_focus(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id

        res = self.testapp.get(
            "/.well-known/admin/private-key/%s" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/private-key/%s/parse.json" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/private-key/%s/key.key" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/private-key/%s/key.pem" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/private-key/%s/key.pem.txt" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/private-key/%s/certificate-requests" % focus_id,
            status=200,
        )
        res = self.testapp.get(
            "/.well-known/admin/private-key/%s/certificate-requests/1" % focus_id,
            status=200,
        )
        res = self.testapp.get(
            "/.well-known/admin/private-key/%s/certificates" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/private-key/%s/certificates/1" % focus_id, status=200
        )

    def test_manipulate(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id

        if not focus_item.is_compromised:
            # make sure to roundtrip!
            # note we expect a 303 on success!
            if focus_item.is_active:
                res = self.testapp.get(
                    "/.well-known/admin/private-key/%s/mark" % focus_id,
                    {"action": "inactive"},
                    status=303,
                )
                res = self.testapp.get(
                    "/.well-known/admin/private-key/%s/mark.json" % focus_id,
                    {"action": "active"},
                    status=200,
                )
            else:
                res = self.testapp.get(
                    "/.well-known/admin/private-key/%s/mark" % focus_id,
                    {"action": "active"},
                    status=303,
                )
                res = self.testapp.get(
                    "/.well-known/admin/private-key/%s/mark.json" % focus_id,
                    {"action": "inactive"},
                    status=200,
                )
        else:
            # TODO
            print("MUST TEST compromised")

    def test_new(self):
        # this should be creating a new key
        _key_filename = TEST_FILES["PrivateKey"]["2"]["file"]
        key_filepath = self._filepath_testfile(_key_filename)
        res = self.testapp.get("/.well-known/admin/private-key/upload", status=200)
        form = res.form
        form["private_key_file_pem"] = Upload(key_filepath)
        res2 = form.submit()
        assert res2.status_code == 303
        assert """/.well-known/admin/private-key/""" in res2.location
        # for some reason, we don't always "create" this.
        assert """?result=success""" in res2.location
        res3 = self.testapp.get(res2.location, status=200)

        res = self.testapp.get("/.well-known/admin/private-key/upload.json", status=200)
        form = {}
        form["private_key_file_pem"] = Upload(key_filepath)
        res2 = self.testapp.post("/.well-known/admin/private-key/upload.json", form)
        assert res2.status_code == 200


class FunctionalTests_UniqueFQDNSets(AppTest):
    """python -m unittest peter_sslers.tests.FunctionalTests_UniqueFQDNSets"""

    def _get_item(self):
        # grab a Key
        focus_item = (
            self.ctx.dbSession.query(model_objects.UniqueFQDNSet)
            .order_by(model_objects.UniqueFQDNSet.id.asc())
            .first()
        )
        return focus_item

    def test_list(self):
        # root
        res = self.testapp.get("/.well-known/admin/unique-fqdn-sets", status=200)
        res = self.testapp.get("/.well-known/admin/unique-fqdn-sets.json", status=200)
        # paginated
        res = self.testapp.get("/.well-known/admin/unique-fqdn-sets/1", status=200)
        res = self.testapp.get("/.well-known/admin/unique-fqdn-sets/1.json", status=200)

    def test_focus(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id

        res = self.testapp.get(
            "/.well-known/admin/unique-fqdn-set/%s" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/unique-fqdn-set/%s.json" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/unique-fqdn-set/%s/calendar.json" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/unique-fqdn-set/%s/certificate-requests" % focus_id,
            status=200,
        )
        res = self.testapp.get(
            "/.well-known/admin/unique-fqdn-set/%s/certificate-requests/1" % focus_id,
            status=200,
        )
        res = self.testapp.get(
            "/.well-known/admin/unique-fqdn-set/%s/certificates" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/unique-fqdn-set/%s/certificates/1" % focus_id,
            status=200,
        )

    def test_manipulate(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id

        res = self.testapp.get(
            "/.well-known/admin/unique-fqdn-set/%s/renew/queue" % focus_id,
            {"action": "cancel"},
            status=303,
        )
        res = self.testapp.get(
            "/.well-known/admin/unique-fqdn-set/%s/renew/queue.json" % focus_id,
            {"action": "cancel"},
            status=200,
        )


class FunctionalTests_QueueDomains(AppTest):
    """python -m unittest peter_sslers.tests.FunctionalTests_QueueDomains"""

    def _get_item(self):
        # grab an item
        focus_item = (
            self.ctx.dbSession.query(model_objects.QueueDomain)
            .order_by(model_objects.QueueDomain.id.asc())
            .first()
        )
        return focus_item

    def test_list(self):
        # root
        res = self.testapp.get("/.well-known/admin/queue-domains", status=200)
        res = self.testapp.get("/.well-known/admin/queue-domains/all", status=200)
        # paginated
        res = self.testapp.get("/.well-known/admin/queue-domains/1", status=200)
        res = self.testapp.get("/.well-known/admin/queue-domains/all/1", status=200)

        # json root
        res = self.testapp.get("/.well-known/admin/queue-domains.json", status=200)
        res = self.testapp.get("/.well-known/admin/queue-domains/all.json", status=200)
        # json paginated
        res = self.testapp.get("/.well-known/admin/queue-domains/1.json", status=200)
        res = self.testapp.get(
            "/.well-known/admin/queue-domains/all/1.json", status=200
        )

    def test_focus(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id

        res = self.testapp.get(
            "/.well-known/admin/queue-domain/%s" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/queue-domain/%s.json" % focus_id, status=200
        )

    def tests_add(self):
        res = self.testapp.get("/.well-known/admin/queue-domains/add", status=200)
        form = res.form
        form["domain_names"] = TEST_FILES["Domains"]["Queue"]["1"]["add"]
        res2 = form.submit()
        assert res2.status_code == 303
        assert (
            """http://localhost/.well-known/admin/queue-domains?result=success"""
            in res2.location
        )

        res = self.testapp.get("/.well-known/admin/queue-domains/add.json", status=200)
        _data = {"domain_names": TEST_FILES["Domains"]["Queue"]["1"]["add.json"]}
        res2 = self.testapp.post("/.well-known/admin/queue-domains/add.json", _data)
        assert res2.status_code == 200
        res2_json = json.loads(res2.body)
        assert res2_json["result"] == "success"

    @unittest.skip("tests not written yet")
    def tests_todo(self):
        # todo
        if DISABLE_UNWRITTEN_TESTS:
            return True
        res = self.testapp.get("/.well-known/admin/queue-domains/process", status=200)
        res = self.testapp.get(
            "/.well-known/admin/queue-domains/process.json", status=200
        )

    def test_manipulate(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id

        res = self.testapp.get(
            "/.well-known/admin/queue-domain/%s/mark" % focus_id,
            {"action": "cancel"},
            status=303,
        )
        res = self.testapp.get(
            "/.well-known/admin/queue-domain/%s/mark.json" % focus_id,
            {"action": "cancel"},
            status=200,
        )


class FunctionalTests_QueueRenewal(AppTest):
    """python -m unittest peter_sslers.tests.FunctionalTests_QueueRenewal"""

    def _get_item(self):
        # grab an item
        focus_item = (
            self.ctx.dbSession.query(model_objects.QueueRenewal)
            .order_by(model_objects.QueueRenewal.id.asc())
            .first()
        )
        return focus_item

    def test_list(self):
        # root
        res = self.testapp.get("/.well-known/admin/queue-renewals", status=200)
        res = self.testapp.get("/.well-known/admin/queue-renewals/all", status=200)
        res = self.testapp.get(
            "/.well-known/admin/queue-renewals/active-failures", status=200
        )
        # paginated
        res = self.testapp.get("/.well-known/admin/queue-renewals/1", status=200)
        res = self.testapp.get("/.well-known/admin/queue-renewals/all/1", status=200)
        res = self.testapp.get(
            "/.well-known/admin/queue-renewals/active-failures/1", status=200
        )

        # root|json
        res = self.testapp.get("/.well-known/admin/queue-renewals.json", status=200)
        res = self.testapp.get("/.well-known/admin/queue-renewals/all.json", status=200)
        res = self.testapp.get(
            "/.well-known/admin/queue-renewals/active-failures.json", status=200
        )
        # paginated|json
        res = self.testapp.get("/.well-known/admin/queue-renewals/1.json", status=200)
        res = self.testapp.get(
            "/.well-known/admin/queue-renewals/all/1.json", status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/queue-renewals/active-failures/1.json", status=200
        )

    def test_focus(self):
        """this doesn't work on solo tests"""
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id
        res = self.testapp.get(
            "/.well-known/admin/queue-renewal/%s" % focus_id, status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/queue-renewal/%s.json" % focus_id, status=200
        )

    @unittest.skip("tests not written yet")
    def tests_todo(self):
        # todo
        if DISABLE_UNWRITTEN_TESTS:
            return True
        res = self.testapp.get("/.well-known/admin/queue-renewals/process", status=200)
        res = self.testapp.get(
            "/.well-known/admin/queue-renewals/process.json", status=200
        )

    def test_manipulate(self):
        focus_item = self._get_item()
        assert focus_item is not None
        focus_id = focus_item.id

        res = self.testapp.get(
            "/.well-known/admin/queue-renewal/%s/mark" % focus_id,
            {"action": "cancel"},
            status=303,
        )
        res = self.testapp.get(
            "/.well-known/admin/queue-renewal/%s/mark.json" % focus_id,
            {"action": "cancel"},
            status=200,
        )


class FunctionalTests_Operations(AppTest):
    """python -m unittest peter_sslers.tests.FunctionalTests_Operations"""

    def tests_passive(self):
        # this should redirect
        res = self.testapp.get("/.well-known/admin/operations", status=302)
        assert res.location == "http://localhost/.well-known/admin/operations/log"

        res = self.testapp.get(
            "/.well-known/admin/operations/ca-certificate-probes", status=200
        )
        res = self.testapp.get(
            "/.well-known/admin/operations/ca-certificate-probes/1", status=200
        )
        res = self.testapp.get("/.well-known/admin/operations/log", status=200)
        res = self.testapp.get("/.well-known/admin/operations/log/1", status=200)
        res = self.testapp.get("/.well-known/admin/operations/nginx", status=200)
        res = self.testapp.get("/.well-known/admin/operations/nginx/1", status=200)
        res = self.testapp.get("/.well-known/admin/operations/redis", status=200)
        res = self.testapp.get("/.well-known/admin/operations/redis/1", status=200)
        res = self.testapp.get("/.well-known/admin/operations/object-log", status=200)
        res = self.testapp.get("/.well-known/admin/operations/object-log/1", status=200)

        focus_item = (
            self.ctx.dbSession.query(model_objects.OperationsEvent)
            .order_by(model_objects.OperationsEvent.id.asc())
            .limit(1)
            .one()
        )
        res = self.testapp.get(
            "/.well-known/admin/operations/log/item/%s" % focus_item.id, status=200
        )

        focus_item_event = (
            self.ctx.dbSession.query(model_objects.OperationsObjectEvent)
            .order_by(model_objects.OperationsObjectEvent.id.asc())
            .limit(1)
            .one()
        )
        res = self.testapp.get(
            "/.well-known/admin/operations/object-log/item/%s" % focus_item_event.id,
            status=200,
        )


class ZZZ_FunctionalTests_API(AppTest):
    """python -m unittest peter_sslers.tests.ZZZ_FunctionalTests_API"""

    """this is prefixed `ZZZ_` so it runs last.
    When run, some API endpoints will deactivate the test certificates – which will
    cause other tests to fail.
    """

    def tests_passive(self):
        res = self.testapp.get("/.well-known/admin/api", status=200)

    def tests_domains(self):
        # enable
        _data = {"domain_names": "example.com,foo.example.com, bar.example.com"}
        res = self.testapp.post("/.well-known/admin/api/domain/enable", _data)
        assert res.status_code == 200
        res_json = json.loads(res.body)
        assert res_json["result"] == "success"

        # disable
        _data = {"domain_names": "example.com,biz.example.com"}
        res = self.testapp.post("/.well-known/admin/api/domain/disable", _data)
        assert res.status_code == 200
        res_json = json.loads(res.body)
        assert res_json["result"] == "success"

    @unittest.skipUnless(RUN_NGINX_TESTS, "not running against nginx")
    def tests_nginx(self):
        res = self.testapp.get("/.well-known/admin/api/nginx/cache-flush", status=303)
        assert (
            "/.well-known/admin/operations/nginx?operation=nginx_cache_flush&result=success&event.id="
            in res.location
        )

        res = self.testapp.get(
            "/.well-known/admin/api/nginx/cache-flush.json", status=200
        )
        res_json = json.loads(res.body)
        assert res_json["result"] == "success"

    @unittest.skipUnless(RUN_REDIS_TESTS, "not running against nginx")
    def tests_redis(self):
        res = self.testapp.get("/.well-known/admin/api/redis/prime", status=303)
        assert (
            "/.well-known/admin/operations/redis?operation=redis_prime&result=success&event.id="
            in res.location
        )

        res = self.testapp.get("/.well-known/admin/api/redis/prime.json", status=200)
        res_json = json.loads(res.body)
        assert res_json["result"] == "success"

    def tests_manipulate(self):
        # deactivate-expired
        res = self.testapp.get("/.well-known/admin/api/deactivate-expired", status=303)
        assert (
            "/.well-known/admin/operations/log?result=success&event.id=" in res.location
        )

        res = self.testapp.get(
            "/.well-known/admin/api/deactivate-expired.json", status=200
        )
        res_json = json.loads(res.body)
        assert res_json["result"] == "success"

        # update-recents
        res = self.testapp.get("/.well-known/admin/api/update-recents", status=303)
        assert (
            "/.well-known/admin/operations/log?result=success&event.id=" in res.location
        )
        res = self.testapp.get("/.well-known/admin/api/update-recents.json", status=200)
        res_json = json.loads(res.body)
        assert res_json["result"] == "success"

    @unittest.skipUnless(
        RUN_LETSENCRYPT_API_TESTS, "not running against letsencrypt api"
    )
    def tests_letsencrypt_api(self):
        res = self.testapp.get(
            "/.well-known/admin/api/ca-certificate-probes/probe", status=303
        )
        assert (
            "/admin/operations/ca-certificate-probes?result=success&event.id="
            in res.location
        )

        res = self.testapp.get(
            "/.well-known/admin/api/ca-certificate-probes/probe.json", status=200
        )
        res_json = json.loads(res.body)
        assert res_json["result"] == "success"

    @unittest.skip("tests not written yet")
    def tests__certificate_if_needed(self):
        """
        api_domains__certificate_if_needed
        """
        pass
