# pyramid
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.renderers import render, render_to_response
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPSeeOther

# stdlib
import json
import pdb

# pypi
import sqlalchemy

# localapp
from .. import lib
from ..lib import formhandling
from ..lib import form_utils as form_utils
from ..lib import text as lib_text
from ..lib.forms import Form_AcmeOrder_new_freeform
from ..lib.forms import Form_AcmeOrder_renew_custom
from ..lib.forms import Form_AcmeOrder_renew_quick
from ..lib.handler import Handler, items_per_page
from ..lib.handler import json_pagination
from ...lib import acme_v2
from ...lib import cert_utils
from ...lib import db as lib_db
from ...lib import errors
from ...lib import utils
from ...model import utils as model_utils


# ==============================================================================


class ViewAdmin_List(Handler):
    @view_config(route_name="admin:acme_orders", renderer="/admin/acme_orders.mako")
    @view_config(route_name="admin:acme_orders|json", renderer="json")
    @view_config(
        route_name="admin:acme_orders_paginated", renderer="/admin/acme_orders.mako"
    )
    @view_config(route_name="admin:acme_orders_paginated|json", renderer="json")
    def list(self):
        wants_active = True if self.request.params.get("status") == "active" else False
        if wants_active:
            sidenav_option = "active"
            active_only = True
            if self.request.wants_json:
                url_template = (
                    "%s/acme-orders/{0}.json?status=active"
                    % self.request.registry.settings["app_settings"]["admin_prefix"]
                )
            else:
                url_template = (
                    "%s/acme-orders/{0}?status=active"
                    % self.request.registry.settings["app_settings"]["admin_prefix"]
                )
        else:
            sidenav_option = "all"
            active_only = False
            if self.request.wants_json:
                url_template = (
                    "%s/acme-orders/{0}.json"
                    % self.request.registry.settings["app_settings"]["admin_prefix"]
                )
            else:
                url_template = (
                    "%s/acme-orders/{0}"
                    % self.request.registry.settings["app_settings"]["admin_prefix"]
                )

        items_count = lib_db.get.get__AcmeOrder__count(
            self.request.api_context, active_only=active_only
        )
        (pager, offset) = self._paginate(items_count, url_template=url_template)
        items_paged = lib_db.get.get__AcmeOrder__paginated(
            self.request.api_context,
            active_only=active_only,
            limit=items_per_page,
            offset=offset,
        )
        if self.request.wants_json:
            admin_url = self.request.admin_url
            return {
                "AcmeOrders": [i._as_json(admin_url=admin_url) for i in items_paged],
                "pagination": json_pagination(items_count, pager),
            }
        return {
            "project": "peter_sslers",
            "AcmeOrders_count": items_count,
            "AcmeOrders": items_paged,
            "pager": pager,
        }


# ------------------------------------------------------------------------------


class ViewAdmin_Focus(Handler):
    def _focus(self, eagerload_web=False):
        dbAcmeOrder = lib_db.get.get__AcmeOrder__by_id(
            self.request.api_context,
            self.request.matchdict["id"],
            eagerload_web=eagerload_web,
        )
        if not dbAcmeOrder:
            raise HTTPNotFound("the order was not found")
        self._focus_url = "%s/acme-order/%s" % (self.request.admin_url, dbAcmeOrder.id,)
        return dbAcmeOrder

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @view_config(
        route_name="admin:acme_order:focus", renderer="/admin/acme_order-focus.mako"
    )
    @view_config(route_name="admin:acme_order:focus|json", renderer="json")
    def focus(self):
        dbAcmeOrder = self._focus(eagerload_web=True)
        if self.request.wants_json:
            return {
                "AcmeOrder": dbAcmeOrder._as_json(admin_url=self.request.admin_url),
            }
        return {"project": "peter_sslers", "AcmeOrder": dbAcmeOrder}

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @view_config(
        route_name="admin:acme_order:focus:audit",
        renderer="/admin/acme_order-focus-audit.mako",
    )
    @view_config(route_name="admin:acme_order:focus:audit|json", renderer="json")
    def audit(self):
        dbAcmeOrder = self._focus(eagerload_web=True)
        if self.request.wants_json:
            audit_report = {
                "result": "success",
                "AuditReport": {
                    "AcmeOrder": {
                        "id": dbAcmeOrder.id,
                        "timestamp_created": dbAcmeOrder.timestamp_created_isoformat,
                        "acme_order_type": dbAcmeOrder.acme_order_type,
                        "acme_order_processing_strategy": dbAcmeOrder.acme_order_processing_strategy,
                        "acme_order_processing_status": dbAcmeOrder.acme_order_processing_status,
                        "is_processing": dbAcmeOrder.is_processing,
                        "acme_status_order": dbAcmeOrder.acme_status_order,
                        "timestamp_expires": dbAcmeOrder.timestamp_expires_isoformat,
                        "private_key_strategy__requested": dbAcmeOrder.private_key_strategy__requested,
                        "private_key_strategy__final": dbAcmeOrder.private_key_strategy__final,
                        "domains": dbAcmeOrder.domains_as_list,
                    },
                    "AcmeAccountKey": {
                        "id": dbAcmeOrder.acme_account_key_id,
                        "contact": dbAcmeOrder.acme_account_key.contact,
                        "private_key_cycle": dbAcmeOrder.acme_account_key.private_key_cycle,
                    },
                    "AcmeAccountProvider": {
                        "id": dbAcmeOrder.acme_account_key.acme_account_provider_id,
                        "name": dbAcmeOrder.acme_account_key.acme_account_provider.name,
                        "url": dbAcmeOrder.acme_account_key.acme_account_provider.url,
                    },
                    "PrivateKey": {
                        "id": dbAcmeOrder.private_key_id,
                        "private_key_source": dbAcmeOrder.private_key.private_key_source,
                        "private_key_type": dbAcmeOrder.private_key.private_key_type,
                    },
                    "UniqueFQDNSet": {"id": dbAcmeOrder.unique_fqdn_set_id,},
                    "AcmeAuthorizations": [],
                },
            }
            auths_list = []
            for to_acme_authorization in dbAcmeOrder.to_acme_authorizations:
                dbAcmeAuthorization = to_acme_authorization.acme_authorization
                dbAcmeChallenge = dbAcmeAuthorization.acme_challenge_http01
                auth_local = {
                    "AcmeAuthorization": {
                        "id": dbAcmeAuthorization.id,
                        "acme_status_authorization": dbAcmeAuthorization.acme_status_authorization,
                        "timestamp_updated": dbAcmeAuthorization.timestamp_updated_isoformat,
                    },
                    "AcmeChallenge": None,
                    "Domain": None,
                }
                if dbAcmeAuthorization.domain_id:
                    auth_local["Domain"] = {
                        "id": dbAcmeAuthorization.domain_id,
                        "domain_name": dbAcmeAuthorization.domain.domain_name,
                    }
                if dbAcmeChallenge:
                    auth_local["AcmeChallenge"] = {
                        "id": dbAcmeChallenge.id,
                        "acme_status_challenge": dbAcmeChallenge.acme_status_challenge,
                        "timestamp_updated": dbAcmeChallenge.timestamp_updated_isoformat,
                        "keyauthorization": dbAcmeChallenge.keyauthorization,
                    }

                auths_list.append(auth_local)
            audit_report["AuditReport"]["AcmeAuthorizations"] = auths_list
            return audit_report
        return {"project": "peter_sslers", "AcmeOrder": dbAcmeOrder}


class ViewAdmin_Focus_Manipulate(ViewAdmin_Focus):
    @view_config(
        route_name="admin:acme_order:focus:acme_event_logs",
        renderer="/admin/acme_order-focus-acme_event_logs.mako",
    )
    @view_config(
        route_name="admin:acme_order:focus:acme_event_logs_paginated",
        renderer="/admin/acme_order-focus-acme_event_logs.mako",
    )
    def acme_event_logs(self):
        dbAcmeOrder = self._focus(eagerload_web=True)

        items_count = lib_db.get.get__AcmeEventLogs__by_AcmeOrderId__count(
            self.request.api_context, dbAcmeOrder.id
        )
        (pager, offset) = self._paginate(
            items_count, url_template="%s/acme-event-logs/{0}" % self._focus_url,
        )
        items_paged = lib_db.get.get__AcmeEventLogs__by_AcmeOrderId__paginated(
            self.request.api_context,
            dbAcmeOrder.id,
            limit=items_per_page,
            offset=offset,
        )
        return {
            "project": "peter_sslers",
            "AcmeOrder": dbAcmeOrder,
            "AcmeEventLogs_count": items_count,
            "AcmeEventLogs": items_paged,
            "pager": pager,
        }

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @view_config(route_name="admin:acme_order:focus:acme_server:sync", renderer=None)
    @view_config(
        route_name="admin:acme_order:focus:acme_server:sync|json", renderer="json"
    )
    def acme_server_sync(self):
        """
        Acme Refresh should just update the record against the acme server.
        """
        dbAcmeOrder = self._focus(eagerload_web=True)
        try:
            if not dbAcmeOrder.is_can_acme_server_sync:
                raise errors.InvalidRequest(
                    "ACME Server Sync is not allowed for this AcmeOrder"
                )
            dbAcmeOrder = lib_db.actions_acme.do__AcmeV2_AcmeOrder__acme_server_sync(
                self.request.api_context, dbAcmeOrder=dbAcmeOrder,
            )
            if self.request.wants_json:
                return {
                    "result": "success",
                    "operation": "acme-server/sync",
                    "AcmeOrder": dbAcmeOrder.as_json,
                }
            return HTTPSeeOther(
                "%s?result=success&operation=acme+server+sync" % self._focus_url
            )
        except (errors.AcmeError, errors.InvalidRequest,) as exc:
            if self.request.wants_json:
                return {
                    "result": "error",
                    "operation": "acme-server/sync",
                    "error": str(exc),
                }
            return HTTPSeeOther(
                "%s?result=error&error=%s&operation=acme+server+sync"
                % (self._focus_url, exc.as_querystring)
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @view_config(
        route_name="admin:acme_order:focus:acme_server:sync_authorizations",
        renderer=None,
    )
    @view_config(
        route_name="admin:acme_order:focus:acme_server:sync_authorizations|json",
        renderer="json",
    )
    def acme_server_sync_authorizations(self):
        """
        sync any auths on the server.
        """
        dbAcmeOrder = self._focus(eagerload_web=True)
        try:
            if not dbAcmeOrder.is_can_acme_server_sync:
                raise errors.InvalidRequest(
                    "ACME Server Sync is not allowed for this AcmeOrder"
                )
            dbAcmeOrder = lib_db.actions_acme.do__AcmeV2_AcmeOrder__acme_server_sync_authorizations(
                self.request.api_context, dbAcmeOrder=dbAcmeOrder,
            )
            if self.request.wants_json:
                return {
                    "result": "success",
                    "operation": "acme-server/sync-authorizations",
                    "AcmeOrder": dbAcmeOrder.as_json,
                }
            return HTTPSeeOther(
                "%s?result=success&operation=acme+server+sync+authorizations"
                % self._focus_url
            )
        except (errors.AcmeError, errors.InvalidRequest,) as exc:
            if self.request.wants_json:
                return {
                    "result": "error",
                    "operation": "acme-server/sync-authorizations",
                    "error": str(exc),
                }
            return HTTPSeeOther(
                "%s?result=error&error=%s&operation=acme+server+sync+authorizations"
                % (self._focus_url, exc.as_querystring)
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @view_config(
        route_name="admin:acme_order:focus:acme_server:deactivate_authorizations",
        renderer=None,
    )
    @view_config(
        route_name="admin:acme_order:focus:acme_server:deactivate_authorizations|json",
        renderer="json",
    )
    def acme_server_deactivate_authorizations(self):
        """
        deactivate any auths on the server.
        """
        dbAcmeOrder = self._focus(eagerload_web=True)
        try:
            if not dbAcmeOrder.is_can_acme_server_deactivate_authorizations:
                raise errors.InvalidRequest(
                    "ACME Server Deactivate Authorizations is not allowed for this AcmeOrder"
                )
            result = lib_db.actions_acme.do__AcmeV2_AcmeOrder__acme_server_deactivate_authorizations(
                self.request.api_context, dbAcmeOrder=dbAcmeOrder,
            )
            if self.request.wants_json:
                return {
                    "result": "success",
                    "operation": "acme-server/deactivate-authorizations",
                    "AcmeOrder": dbAcmeOrder.as_json,
                }
            return HTTPSeeOther(
                "%s?result=success&operation=acme+server+deactivate+authorizations"
                % self._focus_url
            )
        except (errors.AcmeError, errors.InvalidRequest,) as exc:
            if self.request.wants_json:
                return {
                    "result": "error",
                    "operation": "acme-server/deactivate-authorizations",
                    "error": str(exc),
                }
            return HTTPSeeOther(
                "%s?result=error&error=%s&operation=acme+server+deactivate+authorizations"
                % (self._focus_url, exc.as_querystring)
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @view_config(
        route_name="admin:acme_order:focus:acme_server:download_certificate",
        renderer=None,
    )
    @view_config(
        route_name="admin:acme_order:focus:acme_server:download_certificate|json",
        renderer="json",
    )
    def acme_server_download_certificate(self):
        """
        This endpoint is for Immediately Renewing the AcmeOrder with overrides on the keys
        """
        dbAcmeOrder = self._focus(eagerload_web=True)
        try:
            dbAcmeOrder = lib_db.actions_acme.do__AcmeV2_AcmeOrder__download_certificate(
                self.request.api_context, dbAcmeOrder=dbAcmeOrder,
            )
            if self.request.wants_json:
                return {
                    "result": "success",
                    "operation": "acme-server/download-certificate",
                    "AcmeOrder": dbAcmeOrder.as_json,
                }
            return HTTPSeeOther(
                "%s?result=success&operation=acme+server+download+certificate"
                % self._focus_url
            )
        except (errors.AcmeError, errors.InvalidRequest,) as exc:
            if self.request.wants_json:
                return {
                    "result": "error",
                    "operation": "acme-server/download-certificate",
                    "error": str(exc),
                }
            return HTTPSeeOther(
                "%s?result=error&error=%s&operation=acme+server+download+certificate"
                % (self._focus_url, exc.as_querystring)
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @view_config(route_name="admin:acme_order:focus:acme_process", renderer=None)
    @view_config(route_name="admin:acme_order:focus:acme_process|json", renderer="json")
    def process_order(self):
        """
        only certain orders can be processed
        """
        dbAcmeOrder = self._focus(eagerload_web=True)
        try:
            if not dbAcmeOrder.is_can_acme_process:
                raise errors.InvalidRequest(
                    "ACME Process is not allowed for this AcmeOrder"
                )
            dbAcmeOrder = lib_db.actions_acme.do__AcmeV2_AcmeOrder__process(
                self.request.api_context, dbAcmeOrder=dbAcmeOrder,
            )
            if self.request.wants_json:
                return {
                    "result": "success",
                    "operation": "acme-process",
                    "AcmeOrder": dbAcmeOrder.as_json,
                }
            return HTTPSeeOther(
                "%s?result=success&operation=acme+process" % self._focus_url
            )
        except (errors.AcmeError, errors.InvalidRequest,) as exc:
            if self.request.wants_json:
                return {
                    "result": "error",
                    "operation": "acme-process",
                    "error": str(exc),
                }
            return HTTPSeeOther(
                "%s?result=error&error=%s&operation=process+order"
                % (self._focus_url, exc.as_querystring)
            )

    @view_config(route_name="admin:acme_order:focus:finalize", renderer=None)
    @view_config(route_name="admin:acme_order:focus:finalize|json", renderer="json")
    def finalize_order(self):
        """
        only certain orders can be finalized
        """
        dbAcmeOrder = self._focus(eagerload_web=True)
        try:
            if not dbAcmeOrder.is_can_acme_finalize:
                raise errors.InvalidRequest(
                    "ACME Finalize is not allowed for this AcmeOrder"
                )
            dbAcmeOrder = lib_db.actions_acme.do__AcmeV2_AcmeOrder__finalize(
                self.request.api_context, dbAcmeOrder=dbAcmeOrder,
            )
            if self.request.wants_json:
                return {
                    "result": "success",
                    "operation": "finalize-order",
                    "AcmeOrder": dbAcmeOrder.as_json,
                }
            return HTTPSeeOther(
                "%s?result=success&operation=finalize+order" % self._focus_url
            )
        except (errors.AcmeError, errors.InvalidRequest,) as exc:
            if self.request.wants_json:
                return {
                    "result": "error",
                    "operation": "finalize-order",
                    "error": str(exc),
                }
            return HTTPSeeOther(
                "%s?result=error&error=%s&operation=finalize+order"
                % (self._focus_url, exc.as_querystring)
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @view_config(route_name="admin:acme_order:focus:mark", renderer=None)
    @view_config(route_name="admin:acme_order:focus:mark|json", renderer="json")
    def mark_order(self):
        """
        Mark an order
        """
        dbAcmeOrder = self._focus(eagerload_web=True)
        operation = self.request.params.get("operation")
        try:
            if operation == "invalid":
                if not dbAcmeOrder.is_can_mark_invalid:
                    raise errors.InvalidRequest("Can not mark this order as 'invalid'.")
                lib_db.actions_acme.updated_AcmeOrder_status(
                    self.request.api_context,
                    dbAcmeOrder,
                    {"status": "invalid",},
                    transaction_commit=True,
                )

            elif operation == "deactivate":
                """
                `deactivate` should mark the order as:
                    `is_processing = False`
                """
                if dbAcmeOrder.is_processing is not True:
                    raise errors.InvalidRequest("This AcmeOrder is not processing.")

                # todo: use the api
                dbAcmeOrder.is_processing = False
                dbAcmeOrder.timestamp_updated = self.request.api_context.timestamp
                self.request.api_context.dbSession.flush(objects=[dbAcmeOrder])

            elif operation == "renew.auto":
                if dbAcmeOrder.is_auto_renew:
                    raise errors.InvalidRequest("Can not mark this order for renewal.")

                # set the renewal
                dbAcmeOrder.is_auto_renew = True
                # cleanup options
                event_status = "AcmeOrder__mark__renew_auto"

            elif operation == "renew.manual":
                if not dbAcmeOrder.is_auto_renew:
                    raise errors.InvalidRequest(
                        "Can not unmark this order for renewal."
                    )

                # unset the renewal
                dbAcmeOrder.is_auto_renew = False
                # cleanup options
                event_status = "AcmeOrder__mark__renew_manual"

            else:
                raise errors.InvalidRequest("invalid `operation`")

            if self.request.wants_json:
                return {
                    "result": "success",
                    "operation": operation,
                    "AcmeOrder": dbAcmeOrder.as_json,
                }
            return HTTPSeeOther(
                "%s?result=success&operation=%s" % (self._focus_url, operation)
            )

        except (errors.InvalidRequest,) as exc:
            if self.request.wants_json:
                return {
                    "result": "error",
                    "operation": "mark",
                    "error": str(exc),
                }
            return HTTPSeeOther(
                "%s?result=error&error=%s&operation=mark"
                % (self._focus_url, exc.as_querystring)
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @view_config(route_name="admin:acme_order:focus:retry", renderer=None)
    @view_config(route_name="admin:acme_order:focus:retry|json", renderer="json")
    def retry_order(self):
        """
        Retry should create a new order
        """
        # todo - lock behind a POST
        dbAcmeOrder = self._focus(eagerload_web=True)
        try:
            if self.request.method != "POST":
                raise errors.InvalidRequest("This must be a POST request.")
            if not dbAcmeOrder.is_can_acme_server_sync:
                raise errors.InvalidRequest(
                    "ACME Retry is not allowed for this AcmeOrder"
                )
            try:
                dbAcmeOrderNew = lib_db.actions_acme.do__AcmeV2_AcmeOrder__retry(
                    self.request.api_context, dbAcmeOrder=dbAcmeOrder,
                )
            except errors.AcmeOrderCreatedError as exc:
                # unpack a `errors.AcmeOrderCreatedError` to local vars
                dbAcmeOrderNew = exc.acme_order
                exc = exc.original_exception
                if self.request.wants_json:
                    return {
                        "result": "error",
                        "error": exc.args[0],
                        "AcmeOrder": dbAcmeOrderNew.as_json,
                    }
                return HTTPSeeOther(
                    "%s/acme-order/%s?result=error&error=%s&opertion=retry+order"
                    % (self.request.admin_url, dbAcmeOrderNew.id, exc.as_querystring,)
                )
            if self.request.wants_json:
                return {
                    "result": "success",
                    "AcmeOrder": dbAcmeOrderNew.as_json,
                }
            return HTTPSeeOther(
                "%s/acme-order/%s?result=success&operation=retry+order"
                % (self.request.admin_url, dbAcmeOrderNew.id)
            )
        except (errors.AcmeError, errors.InvalidRequest,) as exc:
            if self.request.wants_json:
                return {
                    "result": "error",
                    "error": exc.args[0],
                }
            return HTTPSeeOther(
                "%s?result=error&error=%s&operation=retry+order"
                % (self._focus_url, exc.as_querystring)
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @view_config(route_name="admin:acme_order:focus:renew:custom", renderer=None)
    @view_config(route_name="admin:acme_order:focus:renew:custom|json", renderer="json")
    def renew_custom(self):
        """
        This endpoint is for Immediately Renewing the AcmeOrder with overrides on the keys
        """
        self._load_AcmeAccountKey_GlobalDefault()
        self._load_AcmeAccountProviders()
        if self.request.method == "POST":
            return self._renew_custom__submit()
        return self._renew_custom__print()

    def _renew_custom__print(self):
        dbAcmeOrder = self._focus()
        if not dbAcmeOrder.is_renewable_custom:
            raise errors.DisplayableError("This AcmeOrder can not use RenewCustom")

        if self.request.wants_json:
            return {
                "form_fields": {
                    "processing_strategy": "How should the order be processed?",
                    "account_key_option": "How is the AcmeAccountKey specified?",
                    "account_key_reuse": "pem_md5 of the existing account key. Must/Only submit if `account_key_option==account_key_reuse`",
                    "account_key_global_default": "pem_md5 of the Global Default account key. Must/Only submit if `account_key_option==account_key_global_default`",
                    "account_key_existing": "pem_md5 of any key. Must/Only submit if `account_key_option==account_key_existing`",
                    "account_key_file_pem": "pem of the account key file. Must/Only submit if `account_key_option==account_key_file`",
                    "acme_account_provider_id": "account provider. Must/Only submit if `account_key_option==account_key_file` and `account_key_file_pem` is used.",
                    "account_key_file_le_meta": "LetsEncrypt Certbot file. Must/Only submit if `account_key_option==account_key_file` and `account_key_file_pem` is not used",
                    "account_key_file_le_pkey": "LetsEncrypt Certbot file",
                    "account_key_file_le_reg": "LetsEncrypt Certbot file",
                    "private_key_option": "How is the PrivateKey being specified?",
                    "private_key_reuse": "pem_md5 of existing key",
                    "private_key_existing": "pem_md5 of existing key",
                    "private_key_file_pem": "pem to upload",
                },
                "form_fields_related": [
                    ["account_key_file_pem", "acme_account_provider_id"],
                    [
                        "account_key_file_le_meta",
                        "account_key_file_le_pkey",
                        "account_key_file_le_reg",
                    ],
                ],
                "valid_options": {
                    "acme_account_provider_id": {
                        i.id: "%s (%s)" % (i.name, i.url)
                        for i in self.dbAcmeAccountProviders
                    },
                    "account_key_option": model_utils.AcmeAccontKey_options_b,
                    "processing_strategy": model_utils.AcmeOrder_ProcessingStrategy.OPTIONS_ALL,
                    "private_key_option": model_utils.PrivateKey_options_b,
                    "AcmeAccountKey_GlobalDefault": self.dbAcmeAccountKey_GlobalDefault.as_json
                    if self.dbAcmeAccountKey_GlobalDefault
                    else None,
                },
                "requirements": [
                    "Submit corresponding field(s) to account_key_option. If `account_key_file` is your intent, submit either PEM+ProviderID or the three LetsEncrypt Certbot files."
                ],
                "instructions": [
                    """curl --form 'account_key_option=account_key_reuse' --form 'account_key_reuse=ff00ff00ff00ff00' 'private_key_option=private_key_reuse' --form 'private_key_reuse=ff00ff00ff00ff00' %s/acme-order/1/renew/custom.json"""
                    % self.request.admin_url
                ],
            }

        return render_to_response(
            "/admin/acme_order-focus-renew-custom.mako",
            {
                "AcmeOrder": dbAcmeOrder,
                "AcmeAccountKey_GlobalDefault": self.dbAcmeAccountKey_GlobalDefault,
                "AcmeAccountProviders": self.dbAcmeAccountProviders,
            },
            self.request,
        )

    def _renew_custom__submit(self):
        dbAcmeOrder = self._focus()
        try:
            if not dbAcmeOrder.is_renewable_custom:
                raise errors.DisplayableError("This AcmeOrder can not use RenewCustom")

            (result, formStash) = formhandling.form_validate(
                self.request, schema=Form_AcmeOrder_renew_custom, validate_get=False,
            )
            if not result:
                raise formhandling.FormInvalid()

            (accountKeySelection, privateKeySelection) = form_utils.form_key_selection(
                self.request, formStash, require_contact=False,
            )
            processing_strategy = formStash.results["processing_strategy"]
            private_key_cycle__renewal = formStash.results["private_key_cycle__renewal"]
            try:
                dbAcmeOrderNew = lib_db.actions_acme.do__AcmeV2_AcmeOrder__renew_custom(
                    self.request.api_context,
                    private_key_cycle__renewal=private_key_cycle__renewal,
                    processing_strategy=processing_strategy,
                    dbAcmeOrder=dbAcmeOrder,
                    dbAcmeAccountKey=accountKeySelection.AcmeAccountKey,
                    dbPrivateKey=privateKeySelection.PrivateKey,
                )
            except errors.AcmeOrderCreatedError as exc:
                # unpack a `errors.AcmeOrderCreatedError` to local vars
                dbAcmeOrderNew = exc.acme_order
                exc = exc.original_exception
                if self.request.wants_json:
                    return {
                        "result": "error",
                        "error": str(exc),
                        "AcmeOrder": dbAcmeOrderNew.as_json,
                    }
                return HTTPSeeOther(
                    "%s/acme-order/%s?result=error&error=%s&operation=renew+custom"
                    % (self.request.admin_url, dbAcmeOrderNew.id, exc.as_querystring)
                )

            if self.request.wants_json:
                return {
                    "result": "success",
                    "AcmeOrder": dbAcmeOrderNew.as_json,
                }
            return HTTPSeeOther(
                "%s/acme-order/%s?result=success&operation=renew+custom"
                % (self.request.admin_url, dbAcmeOrderNew.id)
            )
        except (errors.AcmeError, errors.InvalidRequest,) as exc:
            if self.request.wants_json:
                return {"result": "error", "error": str(exc)}
            raise HTTPSeeOther(
                "%s?result=error&error=%s&operation=renew+custom"
                % (self._focus_url, exc.as_querystring,)
            )
        except formhandling.FormInvalid as exc:
            if self.request.wants_json:
                return {"result": "error", "form_errors": formStash.errors}
            return formhandling.form_reprint(self.request, self._renew_custom__print)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    @view_config(route_name="admin:acme_order:focus:renew:quick", renderer=None)
    @view_config(route_name="admin:acme_order:focus:renew:quick|json", renderer="json")
    def renew_quick(self):
        """
        This endpoint is for Immediately Renewing the AcmeOrder with this same Account .
        """
        if self.request.method == "POST":
            return self._renew_quick__submit()
        return self._renew_quick__print()

    def _renew_quick__print(self):
        dbAcmeOrder = self._focus()
        if not dbAcmeOrder.is_renewable_quick:
            raise errors.DisplayableError("This AcmeOrder can not use Quick Renew")

        if self.request.wants_json:
            return {
                "form_fields": {
                    "processing_strategy": "How should the order be processed?",
                },
                "valid_options": {
                    "processing_strategy": model_utils.AcmeOrder_ProcessingStrategy.OPTIONS_ALL,
                },
                "instructions": [
                    """curl --form 'processing_strategy=create_order' %s/acme-order/1/renew/quick.json"""
                    % self.request.admin_url
                ],
            }

        return render_to_response(
            "/admin/acme_order-focus-renew-quick.mako",
            {"AcmeOrder": dbAcmeOrder,},
            self.request,
        )

    def _renew_quick__submit(self):
        dbAcmeOrder = self._focus()
        try:
            if not dbAcmeOrder.is_renewable_quick:
                raise errors.DisplayableError("This AcmeOrder can not use QuickRenew")

            (result, formStash) = formhandling.form_validate(
                self.request, schema=Form_AcmeOrder_renew_quick, validate_get=False,
            )
            if not result:
                raise formhandling.FormInvalid()
            processing_strategy = formStash.results["processing_strategy"]
            try:
                dbAcmeOrderNew = lib_db.actions_acme.do__AcmeV2_AcmeOrder__renew_quick(
                    self.request.api_context,
                    processing_strategy=processing_strategy,
                    dbAcmeOrder=dbAcmeOrder,
                )
            except errors.AcmeOrderCreatedError as exc:
                # unpack a `errors.AcmeOrderCreatedError` to local vars
                dbAcmeOrderNew = exc.acme_order
                exc = exc.original_exception
                if self.request.wants_json:
                    return {
                        "result": "error",
                        "error": str(exc),
                        "AcmeOrder": dbAcmeOrderNew.as_json,
                    }
                return HTTPSeeOther(
                    "%s/acme-order/%s?result=error&error=%s&operation=renew+quick"
                    % (self.request.admin_url, dbAcmeOrderNew.id, exc.as_querystring)
                )
            if self.request.wants_json:
                return {
                    "result": "success",
                    "AcmeOrder": dbAcmeOrderNew.as_json,
                }
            return HTTPSeeOther(
                "%s/acme-order/%s?result=success&operation=renew+quick"
                % (self.request.admin_url, dbAcmeOrderNew.id)
            )
        except (errors.AcmeError, errors.InvalidRequest,) as exc:
            if self.request.wants_json:
                return {"result": "error", "error": str(exc)}
            url_failure = "%s?result=error&error=%s&operation=renew+quick" % (
                self._focus_url,
                exc.as_querystring,
            )
            raise HTTPSeeOther(url_failure)
        except formhandling.FormInvalid as exc:
            if self.request.wants_json:
                return {"result": "error", "form_errors": formStash.errors}
            return formhandling.form_reprint(self.request, self._renew_quick__print)


# ------------------------------------------------------------------------------


class ViewAdmin_New(Handler):
    @view_config(route_name="admin:acme_order:new:freeform")
    @view_config(route_name="admin:acme_order:new:freeform|json", renderer="json")
    def new_freeform(self):
        self._load_AcmeAccountKey_GlobalDefault()
        self._load_AcmeAccountProviders()
        if self.request.method == "POST":
            return self._new_freeform__submit()
        return self._new_freeform__print()

    def _new_freeform__print(self):
        if self.request.wants_json:
            return {
                "form_fields": {
                    "domain_names": "required; a comma separated list of domain names to process",
                    "processing_strategy": "How should the order be processed?",
                    "account_key_option": "How is the AcmeAccountKey specified?",
                    "account_key_reuse": "pem_md5 of the existing account key. Must/Only submit if `account_key_option==account_key_reuse`",
                    "account_key_global_default": "pem_md5 of the Global Default account key. Must/Only submit if `account_key_option==account_key_global_default`",
                    "account_key_existing": "pem_md5 of any key. Must/Only submit if `account_key_option==account_key_existing`",
                    "account_key_file_pem": "pem of the account key file. Must/Only submit if `account_key_option==account_key_file`",
                    "acme_account_provider_id": "account provider. Must/Only submit if `account_key_option==account_key_file` and `account_key_file_pem` is used.",
                    "account_key_file_le_meta": "LetsEncrypt Certbot file. Must/Only submit if `account_key_option==account_key_file` and `account_key_file_pem` is not used",
                    "account_key_file_le_pkey": "LetsEncrypt Certbot file",
                    "account_key_file_le_reg": "LetsEncrypt Certbot file",
                    "private_key_option": "How is the PrivateKey being specified?",
                    "private_key_reuse": "pem_md5 of existing key",
                    "private_key_existing": "pem_md5 of existing key",
                    "private_key_file_pem": "pem to upload",
                },
                "form_fields_related": [
                    ["account_key_file_pem", "acme_account_provider_id"],
                    [
                        "account_key_file_le_meta",
                        "account_key_file_le_pkey",
                        "account_key_file_le_reg",
                    ],
                ],
                "valid_options": {
                    "acme_account_provider_id": {
                        i.id: "%s (%s)" % (i.name, i.url)
                        for i in self.dbAcmeAccountProviders
                    },
                    "account_key_option": model_utils.AcmeAccontKey_options_b,
                    "processing_strategy": model_utils.AcmeOrder_ProcessingStrategy.OPTIONS_ALL,
                    "private_key_option": model_utils.PrivateKey_options_b,
                    "AcmeAccountKey_GlobalDefault": self.dbAcmeAccountKey_GlobalDefault.as_json
                    if self.dbAcmeAccountKey_GlobalDefault
                    else None,
                },
                "requirements": [
                    "Submit corresponding field(s) to account_key_option. If `account_key_file` is your intent, submit either PEM+ProviderID or the three LetsEncrypt Certbot files."
                ],
                "instructions": [
                    """curl --form 'account_key_option=account_key_reuse' --form 'account_key_reuse=ff00ff00ff00ff00' 'private_key_option=private_key_reuse' --form 'private_key_reuse=ff00ff00ff00ff00' %s/acme-order/new/freeform.json"""
                    % self.request.admin_url
                ],
            }
        return render_to_response(
            "/admin/acme_order-new-freeform.mako",
            {
                "AcmeAccountKey_GlobalDefault": self.dbAcmeAccountKey_GlobalDefault,
                "AcmeAccountProviders": self.dbAcmeAccountProviders,
            },
            self.request,
        )

    def _new_freeform__submit(self):
        """
        much of this logic is shared with /api/domain-certificate-if-needed
        """
        try:
            (result, formStash) = formhandling.form_validate(
                self.request, schema=Form_AcmeOrder_new_freeform, validate_get=False,
            )
            if not result:
                raise formhandling.FormInvalid()

            try:
                domain_names = utils.domains_from_string(
                    formStash.results["domain_names"]
                )
            except ValueError as exc:
                # `formStash.fatal_field()` will raise `FormFieldInvalid(FormInvalid)`
                formStash.fatal_field(
                    field="domain_names", message="invalid domain names detected"
                )
            if not domain_names:
                # `formStash.fatal_field()` will raise `FormFieldInvalid(FormInvalid)`
                formStash.fatal_field(
                    field="domain_names",
                    message="invalid or no valid domain names detected",
                )

            accountKeySelection = form_utils.parse_AcmeAccountKeySelection(
                self.request,
                formStash,
                account_key_option=formStash.results["account_key_option"],
                require_contact=False,
            )
            if accountKeySelection.selection == "upload":
                key_create_args = accountKeySelection.upload_parsed.getcreate_args
                key_create_args["event_type"] = "AcmeAccountKey__insert"
                key_create_args[
                    "acme_account_key_source_id"
                ] = model_utils.AcmeAccountKeySource.from_string("imported")
                (
                    dbAcmeAccountKey,
                    _is_created,
                ) = lib_db.getcreate.getcreate__AcmeAccountKey(
                    self.request.api_context, **key_create_args
                )
                accountKeySelection.AcmeAccountKey = dbAcmeAccountKey

            privateKeySelection = form_utils.parse_PrivateKeySelection(
                self.request,
                formStash,
                private_key_option=formStash.results["private_key_option"],
            )

            if privateKeySelection.selection == "upload":
                key_create_args = privateKeySelection.upload_parsed.getcreate_args
                key_create_args["event_type"] = "PrivateKey__insert"
                key_create_args[
                    "private_key_source_id"
                ] = model_utils.PrivateKeySource.from_string("imported")
                key_create_args[
                    "private_key_type_id"
                ] = model_utils.PrivateKeyType.from_string("standard")
                (
                    dbPrivateKey,
                    _is_created,
                ) = lib_db.getcreate.getcreate__PrivateKey__by_pem_text(
                    self.request.api_context, **key_create_args
                )
                privateKeySelection.PrivateKey = dbPrivateKey

            elif privateKeySelection.selection in (
                "generate",
                "private_key_for_account_key",
            ):
                pass

            else:
                formStash.fatal_field(
                    field="private_key_option",
                    message="Could not load the default private key",
                )

            processing_strategy = formStash.results["processing_strategy"]
            private_key_cycle__renewal = formStash.results["private_key_cycle__renewal"]
            try:

                # check for blacklists here
                # this might be better in the AcmeOrder processor, but the orders are by UniqueFqdnSet
                _blacklisted_domain_names = []
                for _domain_name in domain_names:
                    _dbDomainBlacklisted = lib_db.get.get__DomainBlacklisted__by_name(
                        self.request.api_context, _domain_name
                    )
                    if _dbDomainBlacklisted:
                        _blacklisted_domain_names.append(_domain_name)
                if _blacklisted_domain_names:
                    raise errors.AcmeBlacklistedDomains(_blacklisted_domain_names)

                try:
                    dbAcmeOrder = lib_db.actions_acme.do__AcmeV2_AcmeOrder__new(
                        self.request.api_context,
                        acme_order_type_id=model_utils.AcmeOrderType.ACME_AUTOMATED_NEW,
                        domain_names=domain_names,
                        private_key_cycle__renewal=private_key_cycle__renewal,
                        private_key_strategy__requested=privateKeySelection.private_key_strategy__requested,
                        processing_strategy=processing_strategy,
                        dbAcmeAccountKey=accountKeySelection.AcmeAccountKey,
                        dbPrivateKey=privateKeySelection.PrivateKey,
                    )
                except Exception as exc:

                    # unpack a `errors.AcmeOrderCreatedError` to local vars
                    if isinstance(exc, errors.AcmeOrderCreatedError):
                        dbAcmeOrder = exc.acme_order
                        exc = exc.original_exception

                    if isinstance(exc, errors.AcmeError):
                        if self.request.wants_json:
                            return {
                                "result": "error",
                                "error": str(exc),
                                "AcmeOrder": dbAcmeOrder.as_json,
                            }
                        return HTTPSeeOther(
                            "%s/acme-order/%s?result=error&error=%s&operation=new+freeform"
                            % (
                                self.request.registry.settings["app_settings"][
                                    "admin_prefix"
                                ],
                                dbAcmeOrder.id,
                                exc.as_querystring,
                            )
                        )
                    raise

                if self.request.wants_json:
                    return {
                        "result": "success",
                        "AcmeOrder": dbAcmeOrder.as_json,
                    }

                return HTTPSeeOther(
                    "%s/acme-order/%s"
                    % (
                        self.request.registry.settings["app_settings"]["admin_prefix"],
                        dbAcmeOrder.id,
                    )
                )

            except errors.AcmeBlacklistedDomains as exc:
                if self.request.wants_json:
                    return {"result": "error", "error": str(exc)}
                formStash.fatal_field(field="domain_names", message=str(exc))

            except errors.AcmeDuplicateChallenges as exc:
                if self.request.wants_json:
                    return {"result": "error", "error": str(exc)}
                formStash.fatal_field(field="domain_names", message=str(exc))

            except (errors.AcmeError, errors.InvalidRequest,) as exc:
                if self.request.wants_json:
                    return {"result": "error", "error": str(exc)}
                return HTTPSeeOther(
                    "%s/acme-orders?result=error&error=%s&operation=new+freeform"
                    % (
                        self.request.registry.settings["app_settings"]["admin_prefix"],
                        exc.as_querystring,
                    )
                )
            except Exception as exc:
                raise
                # note: allow this on testing
                # raise
                if self.request.registry.settings["exception_redirect"]:
                    return HTTPSeeOther(
                        "%s/acme-orders?result=error&operation=new-freeform"
                        % self.request.registry.settings["app_settings"]["admin_prefix"]
                    )
                raise

        except formhandling.FormInvalid as exc:
            if self.request.wants_json:
                return {"result": "error", "form_errors": formStash.errors}
            return formhandling.form_reprint(self.request, self._new_freeform__print)