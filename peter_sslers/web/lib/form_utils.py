# pypi
import six

# local
from ...lib import db as lib_db
from ...model import objects as model_objects
from ...model import utils as model_utils
from . import formhandling


# ==============================================================================


def decode_args(getcreate_args):
    """
    support for Python2/3
    """
    if six.PY3:
        for (k, v) in list(getcreate_args.items()):
            if isinstance(v, bytes):
                getcreate_args[k] = v.decode("utf8")
    return getcreate_args


class AcmeAccountKeyUploadParser(object):
    """
    An AcmeAccountKey may be uploaded multiple ways:
    * a single PEM file
    * an intra-associated three file triplet from a Certbot installation

    This parser operates on a validated FormEncode results object (via `pyramid_formencode_classic`)
    """

    # overwritten in __init__
    getcreate_args = None
    formStash = None
    # tracked
    acme_account_provider_id = None
    account_key_pem = None
    le_meta_jsons = None
    le_pkey_jsons = None
    le_reg_jsons = None
    private_key_cycle_id = None
    upload_type = None  # pem OR letsencrypt

    def __init__(self, formStash):
        self.formStash = formStash
        self.getcreate_args = {}

    def require_new(self, require_contact=None):
        """
        routine for creating a NEW AcmeAccountKey (peter_sslers generates the credentials)
        """
        formStash = self.formStash

        acme_account_provider_id = formStash.results.get(
            "acme_account_provider_id", None
        )
        if acme_account_provider_id is None:
            # `formStash.fatal_field()` will raise `FormFieldInvalid(FormInvalid)`
            formStash.fatal_field(
                field="acme_account_provider_id", message="No provider submitted."
            )

        private_key_cycle = formStash.results.get(
            "account_key__private_key_cycle", None
        )
        if private_key_cycle is None:
            # `formStash.fatal_field()` will raise `FormFieldInvalid(FormInvalid)`
            formStash.fatal_field(
                field="account_key__private_key_cycle",
                message="No PrivateKey cycle submitted.",
            )
        private_key_cycle_id = model_utils.PrivateKeyCycle.from_string(
            private_key_cycle
        )

        contact = formStash.results.get("account_key__contact", None)
        if not contact and require_contact:
            # `formStash.fatal_field()` will raise `FormFieldInvalid(FormInvalid)`
            formStash.fatal_field(
                field="account_key__contact",
                message="`account_key__contact` is required.",
            )

        getcreate_args = {}
        self.contact = getcreate_args["contact"] = contact
        self.acme_account_provider_id = getcreate_args[
            "acme_account_provider_id"
        ] = acme_account_provider_id
        self.private_key_cycle_id = getcreate_args[
            "private_key_cycle_id"
        ] = private_key_cycle_id
        self.getcreate_args = decode_args(getcreate_args)

    def require_upload(self, require_contact=None):
        """
        routine for uploading an exiting AcmeAccountKey
        """
        formStash = self.formStash

        # -------------------
        # do a quick parse...
        requirements_either_or = (
            (
                "account_key_file_pem",
                # "acme_account_provider_id",
            ),
            (
                "account_key_file_le_meta",
                "account_key_file_le_pkey",
                "account_key_file_le_reg",
            ),
        )
        failures = []
        passes = []
        for idx, option_set in enumerate(requirements_either_or):
            option_set_results = [
                True if formStash.results[option_set_item] is not None else False
                for option_set_item in option_set
            ]
            # if we have any item, we need all of them
            if any(option_set_results):
                if not all(option_set_results):
                    failures.append(
                        "If any of %s is provided, all must be provided."
                        % str(option_set)
                    )
                else:
                    passes.append(idx)

        if (len(passes) != 1) or failures:
            # `formStash.fatal_form()` will raise `FormInvalid()`
            formStash.fatal_form(
                "You must upload `account_key_file_pem` or all of (`account_key_file_le_meta`, `account_key_file_le_pkey`, `account_key_file_le_reg`)."
            )

        # -------------------

        # validate the provider option
        # will be None unless a pem is uploaded
        # required for PEM, ignored otherwise
        acme_account_provider_id = formStash.results.get(
            "acme_account_provider_id", None
        )

        private_key_cycle = formStash.results.get(
            "account_key__private_key_cycle", None
        )
        if private_key_cycle is None:
            # `formStash.fatal_field()` will raise `FormFieldInvalid(FormInvalid)`
            formStash.fatal_field(
                field="account_key__private_key_cycle",
                message="No PrivateKey cycle submitted.",
            )
        private_key_cycle_id = model_utils.PrivateKeyCycle.from_string(
            private_key_cycle
        )

        getcreate_args = {}
        _contact = formStash.results.get("account_key__contact")
        if _contact:  # `None` or `""`
            getcreate_args["contact"] = _contact
        else:
            if require_contact:
                formStash.fatal_field(
                    field="account_key__contact",
                    message="Missing `account_key__contact`.",
                )

        self.private_key_cycle_id = getcreate_args[
            "private_key_cycle_id"
        ] = private_key_cycle_id

        if formStash.results["account_key_file_pem"] is not None:
            if acme_account_provider_id is None:
                # `formStash.fatal_field()` will raise `FormFieldInvalid(FormInvalid)`
                formStash.fatal_field(
                    field="acme_account_provider_id", message="No provider submitted."
                )
            self.upload_type = "pem"
            self.acme_account_provider_id = getcreate_args[
                "acme_account_provider_id"
            ] = acme_account_provider_id
            self.account_key_pem = getcreate_args[
                "key_pem"
            ] = formhandling.slurp_file_field(formStash, "account_key_file_pem")
        else:
            # note that we use `jsonS` to indicate a string
            self.le_meta_jsons = getcreate_args[
                "le_meta_jsons"
            ] = formhandling.slurp_file_field(formStash, "account_key_file_le_meta")
            self.le_pkey_jsons = getcreate_args[
                "le_pkey_jsons"
            ] = formhandling.slurp_file_field(formStash, "account_key_file_le_pkey")
            self.le_reg_jsons = getcreate_args[
                "le_reg_jsons"
            ] = formhandling.slurp_file_field(formStash, "account_key_file_le_reg")
        self.getcreate_args = decode_args(getcreate_args)


class _PrivateKeyUploadParser(object):
    """
    A PrivateKey is not a complex upload to parse itself
    This code exists to mimic the AcmeAccountKey uploading.
    """

    # overwritten in __init__
    getcreate_args = None
    formStash = None

    # tracked
    private_key_pem = None
    upload_type = None  # pem

    def __init__(self, formStash):
        self.formStash = formStash
        self.getcreate_args = {}

    def require_upload(self):
        """
        routine for uploading an exiting PrivateKey
        """
        formStash = self.formStash

        getcreate_args = {}

        if formStash.results["private_key_file_pem"] is not None:
            self.upload_type = "pem"
            self.private_key_pem = getcreate_args[
                "key_pem"
            ] = formhandling.slurp_file_field(formStash, "private_key_file_pem")

        self.getcreate_args = decode_args(getcreate_args)


class _AcmeAccountKeySelection(object):
    """
    Class used to manage an uploaded AcmeAccountKey
    """

    selection = None
    upload_parsed = None  # instance of AcmeAccountKeyUploadParser or None
    AcmeAccountKey = None


class _PrivateKeySelection(object):
    selection = None
    upload_parsed = None  # instance of AcmeAccountKeyUploadParser or None
    private_key_strategy__requested = None
    PrivateKey = None


def parse_AcmeAccountKeySelection(
    request, formStash, account_key_option=None, allow_none=None, require_contact=None,
):
    account_key_pem = None
    account_key_pem_md5 = None
    dbAcmeAccountKey = None
    is_global_default = None

    # handle the explicit-option
    accountKeySelection = _AcmeAccountKeySelection()
    if account_key_option == "account_key_file":
        # this will handle form validation and raise errors.
        parser = AcmeAccountKeyUploadParser(formStash)

        # this will have `contact` and `private_key_cycle`
        parser.require_upload(require_contact=require_contact)

        # update our object
        accountKeySelection.selection = "upload"
        accountKeySelection.upload_parsed = parser

        return accountKeySelection
    else:
        if account_key_option == "account_key_global_default":
            accountKeySelection.selection = "global_default"
            account_key_pem_md5 = formStash.results["account_key_global_default"]
            is_global_default = True
        elif account_key_option == "account_key_existing":
            accountKeySelection.selection = "existing"
            account_key_pem_md5 = formStash.results["account_key_existing"]
        elif account_key_option == "account_key_reuse":
            accountKeySelection.selection = "reuse"
            account_key_pem_md5 = formStash.results["account_key_reuse"]
        elif account_key_option == "none":
            if not allow_none:
                # `formStash.fatal_form()` will raise `FormInvalid()`
                formStash.fatal_form(
                    "This form does not support no AcmeAccountKey selection."
                )
            # note the lowercase "none"; this is an explicit "no item" selection
            # only certain routes allow this
            accountKeySelection.selection = "none"
            account_key_pem_md5 = None
            return accountKeySelection
        else:
            formStash.fatal_form(message="Invalid `account_key_option`",)
        if not account_key_pem_md5:
            # `formStash.fatal_field()` will raise `FormFieldInvalid(FormInvalid)`
            formStash.fatal_field(
                field=account_key_option, message="You did not provide a value"
            )
        dbAcmeAccountKey = lib_db.get.get__AcmeAccountKey__by_pemMd5(
            request.api_context, account_key_pem_md5, is_active=True
        )
        if not dbAcmeAccountKey:
            # `formStash.fatal_field()` will raise `FormFieldInvalid(FormInvalid)`
            formStash.fatal_field(
                field=account_key_option,
                message="The selected AcmeAccountKey is not enrolled in the system.",
            )
        if is_global_default and not dbAcmeAccountKey.is_global_default:
            # `formStash.fatal_field()` will raise `FormFieldInvalid(FormInvalid)`
            formStash.fatal_field(
                field=account_key_option,
                message="The selected AcmeAccountKey is not the current default.",
            )
        accountKeySelection.AcmeAccountKey = dbAcmeAccountKey
        return accountKeySelection
    # `formStash.fatal_form()` will raise `FormInvalid()`
    formStash.fatal_form("There was an error validating your form.")


def parse_PrivateKeySelection(request, formStash, private_key_option=None):
    private_key_pem = None
    private_key_pem_md5 = None
    PrivateKey = None  # `:class:model.objects.PrivateKey`

    # handle the explicit-option
    privateKeySelection = _PrivateKeySelection()
    if private_key_option == "private_key_file":
        # this will handle form validation and raise errors.
        parser = _PrivateKeyUploadParser(formStash)
        parser.require_upload()

        # update our object
        privateKeySelection.selection = "upload"
        privateKeySelection.upload_parsed = parser
        privateKeySelection.private_key_strategy__requested = "specified"

        return privateKeySelection

    else:
        if private_key_option == "private_key_existing":
            privateKeySelection.selection = "existing"
            privateKeySelection.private_key_strategy__requested = "specified"
            private_key_pem_md5 = formStash.results["private_key_existing"]
        elif private_key_option == "private_key_reuse":
            privateKeySelection.selection = "reuse"
            privateKeySelection.private_key_strategy__requested = "specified"
            private_key_pem_md5 = formStash.results["private_key_reuse"]
        elif private_key_option in (
            "private_key_generate",
            "private_key_for_account_key",
        ):
            dbPrivateKey = lib_db.get.get__PrivateKey__by_id(request.api_context, 0)
            if not dbPrivateKey:
                formStash.fatal_field(
                    field=private_key_option,
                    message="Could not load the placeholder PrivateKey.",
                )
            privateKeySelection.PrivateKey = dbPrivateKey
            if private_key_option == "private_key_generate":
                privateKeySelection.selection = "generate"
                privateKeySelection.private_key_strategy__requested = (
                    "deferred-generate"
                )
            elif private_key_option == "private_key_for_account_key":
                privateKeySelection.selection = "private_key_for_account_key"
                privateKeySelection.private_key_strategy__requested = (
                    "deferred-associate"
                )
            return privateKeySelection
        else:
            # `formStash.fatal_form()` will raise `FormInvalid()`
            formStash.fatal_form("Invalid `private_key_option`")

        if not private_key_pem_md5:
            # `formStash.fatal_field()` will raise `FormFieldInvalid(FormInvalid)`
            formStash.fatal_field(
                field=private_key_option, message="You did not provide a value"
            )
        dbPrivateKey = lib_db.get.get__PrivateKey__by_pemMd5(
            request.api_context, private_key_pem_md5, is_active=True
        )
        if not dbPrivateKey:
            # `formStash.fatal_field()` will raise `FormFieldInvalid(FormInvalid)`
            formStash.fatal_field(
                field=private_key_option,
                message="The selected PrivateKey is not enrolled in the system.",
            )
        privateKeySelection.PrivateKey = dbPrivateKey
        return privateKeySelection

    # `formStash.fatal_form()` will raise `FormInvalid()`
    formStash.fatal_form("There was an error validating your form.")


def form_key_selection(request, formStash, require_contact=None):
    accountKeySelection = parse_AcmeAccountKeySelection(
        request,
        formStash,
        account_key_option=formStash.results["account_key_option"],
        require_contact=require_contact,
    )
    if accountKeySelection.selection == "upload":
        key_create_args = accountKeySelection.upload_parsed.getcreate_args
        key_create_args["event_type"] = "AcmeAccountKey__insert"
        key_create_args[
            "acme_account_key_source_id"
        ] = model_utils.AcmeAccountKeySource.from_string("imported")
        (dbAcmeAccountKey, _is_created,) = lib_db.getcreate.getcreate__AcmeAccountKey(
            request.api_context, **key_create_args
        )
        accountKeySelection.AcmeAccountKey = dbAcmeAccountKey

    privateKeySelection = parse_PrivateKeySelection(
        request, formStash, private_key_option=formStash.results["private_key_option"],
    )

    if privateKeySelection.selection == "upload":
        key_create_args = privateKeySelection.upload_parsed.getcreate_args
        key_create_args["event_type"] = "PrivateKey__insert"
        key_create_args[
            "private_key_source_id"
        ] = model_utils.PrivateKeySource.from_string("imported")
        key_create_args["private_key_type_id"] = model_utils.PrivateKeyType.from_string(
            "standard"
        )
        (
            dbPrivateKey,
            _is_created,
        ) = lib_db.getcreate.getcreate__PrivateKey__by_pem_text(
            request.api_context, **key_create_args
        )
        privateKeySelection.PrivateKey = dbPrivateKey

    elif privateKeySelection.selection == "generate":
        dbPrivateKey = lib_db.get.get__PrivateKey__by_id(request.api_context, 0)
        if not dbPrivateKey:
            formStash.fatal_field(
                field="private_key_option",
                message="Could not load the placeholder PrivateKey for autogeneration.",
            )
        privateKeySelection.PrivateKey = dbPrivateKey

    return (accountKeySelection, privateKeySelection)