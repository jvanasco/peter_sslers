# logging
import logging

log = logging.getLogger(__name__)


# stdlib
import datetime

# pypi
import transaction

# localapp
from ... import lib
from .. import errors
from .. import utils
from ...model import utils as model_utils
from ...model import objects as model_objects

# local
from .logger import log__SslOperationsEvent
from .logger import _log_object_event


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def dequeue_QueuedDomain(
    ctx,
    dbQueueDomain,
    dbOperationsEvent=None,
    event_status="queue_domain__mark__cancelled",
    action="de-queued",
):
    event_payload_dict = utils.new_event_payload_dict()
    event_payload_dict["ssl_queue_domain.id"] = dbQueueDomain.id
    event_payload_dict["action"] = action
    dbQueueDomain.is_active = False
    dbQueueDomain.timestamp_processed = ctx.timestamp
    ctx.dbSession.flush(objects=[dbQueueDomain])

    _log_object_event(
        ctx,
        dbOperationsEvent=dbOperationsEvent,
        event_status_id=model_utils.SslOperationsObjectEventStatus.from_string(
            event_status
        ),
        dbQueueDomain=dbQueueDomain,
    )
    return True


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def queue_domains__add(ctx, domain_names):
    """
    Adds domains to the queue if needed
    2016.06.04 - dbOperationsEvent compliant
    """
    # bookkeeping
    event_payload_dict = utils.new_event_payload_dict()
    dbOperationsEvent = log__SslOperationsEvent(
        ctx,
        model_utils.SslOperationsEventType.from_string("queue_domain__add"),
        event_payload_dict,
    )

    domain_names = utils.domains_from_list(domain_names)
    results = {d: None for d in domain_names}
    _timestamp = dbOperationsEvent.timestamp_event
    for domain_name in domain_names:
        _dbDomain = lib.db.get.get__SslDomain__by_name(
            ctx, domain_name, preload=False, active_only=False
        )
        _result = None
        _logger_args = {"event_status_id": None}
        if _dbDomain:
            if not _dbDomain.is_active:
                # set this active
                _dbDomain.is_active = True

                _logger_args[
                    "event_status_id"
                ] = model_utils.SslOperationsObjectEventStatus.from_string(
                    "queue_domain__add__already_exists_activate"
                )
                _logger_args["dbDomain"] = _dbDomain
                _result = "exists"

            else:
                _logger_args[
                    "event_status_id"
                ] = model_utils.SslOperationsObjectEventStatus.from_string(
                    "queue_domain__add__already_exists"
                )
                _logger_args["dbDomain"] = _dbDomain
                _result = "exists"

        elif not _dbDomain:
            _dbQueueDomain = lib.db.get.get__SslQueueDomain__by_name(ctx, domain_name)
            if _dbQueueDomain:
                _logger_args[
                    "event_status_id"
                ] = model_utils.SslOperationsObjectEventStatus.from_string(
                    "queue_domain__add__already_queued"
                )
                _logger_args["dbQueueDomain"] = _dbQueueDomain
                _result = "already_queued"

            else:
                _dbQueueDomain = model_objects.SslQueueDomain()
                _dbQueueDomain.domain_name = domain_name
                _dbQueueDomain.timestamp_entered = _timestamp
                _dbQueueDomain.ssl_operations_event_id__created = dbOperationsEvent.id
                ctx.dbSession.add(_dbQueueDomain)
                ctx.dbSession.flush(objects=[_dbQueueDomain])

                _logger_args[
                    "event_status_id"
                ] = model_utils.SslOperationsObjectEventStatus.from_string(
                    "queue_domain__add__success"
                )
                _logger_args["dbQueueDomain"] = _dbQueueDomain
                _result = "queued"

        # note result
        results[domain_name] = _result

        # log request
        _log_object_event(ctx, dbOperationsEvent=dbOperationsEvent, **_logger_args)

    return results


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def _get_default_AccountKey(ctx):
    # raises an error if we fail
    dbAccountKeyDefault = lib.db.get.get__SslAcmeAccountKey__default(
        ctx, active_only=True
    )
    if not dbAccountKeyDefault:
        raise ValueError("Could not load a default AccountKey.")
    return dbAccountKeyDefault


def _get_default_PrivateKey(ctx):
    # raises an error if we fail
    # which private-key should we use?

    if not ctx.request:
        # ToDo: refactor `ctx.request.registry.settings`
        raise ValueError("must be invoked within Pyramid")

    use_weekly_key = ctx.request.registry.settings["queue_domains_use_weekly_key"]
    if use_weekly_key:
        dbPrivateKey = lib.db.get.get__SslPrivateKey__current_week(ctx)
        if not dbPrivateKey:
            dbPrivateKey = lib.db.create.create__SslPrivateKey__autogenerated(ctx)
    else:
        dbPrivateKey = lib.db.get.get__SslPrivateKey__default(ctx, active_only=True)
    if not dbPrivateKey:
        raise errors.DisplayableError("Could not load a default PrivateKey")
    return dbPrivateKey


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def queue_domains__process(ctx, dbAccountKey=None, dbPrivateKey=None):
    """
    This endpoint should pull `1-100[configurable]` domains from the queue, and create a certificate for them

    * if there are more than 100, should we process them, or return that info in json?

    """
    if not ctx.request:
        # ToDo: refactor `ctx.request.registry.settings`
        raise ValueError("must be invoked within Pyramid")

    if dbAccountKey is None:
        # raises an error if we fail
        dbAccountKey = _get_default_AccountKey(ctx)

    if dbPrivateKey is None:
        # raises an error if we fail
        dbPrivateKey = _get_default_PrivateKey(ctx)

    try:
        min_domains = ctx.request.registry.settings["queue_domains_min_per_cert"]
        max_domains = ctx.request.registry.settings["queue_domains_max_per_cert"]

        items_paged = lib.db.get.get__SslQueueDomain__paginated(
            ctx, unprocessed_only=True, limit=max_domains, offset=0
        )
        if len(items_paged) < min_domains:
            raise errors.DisplayableError(
                "Not enough domains to issue. Only found `%s`, need `%s`."
                % (len(items_paged), min_domains)
            )

        event_payload_dict = utils.new_event_payload_dict()
        event_payload_dict["batch_size"] = len(items_paged)
        event_payload_dict["status"] = "attempt"
        event_payload_dict["queue_domain_ids"] = ",".join(
            [str(d.id) for d in items_paged]
        )
        dbOperationsEvent = log__SslOperationsEvent(
            ctx,
            model_utils.SslOperationsEventType.from_string("queue_domain__process"),
            event_payload_dict,
        )

        _timestamp = ctx.timestamp
        for qDomain in items_paged:
            _log_object_event(
                ctx,
                dbOperationsEvent=dbOperationsEvent,
                event_status_id=model_utils.SslOperationsEventType.from_string(
                    "queue_domain__process"
                ),
                dbQueueDomain=qDomain,
            )

        # commit this so we have the attempt recorded.
        transaction.commit()

        # exit out
        if not items_paged:
            raise errors.DisplayableError("No items in queue")

        # cache the timestamp
        timestamp_transaction = datetime.datetime.utcnow()

        # generate domains
        domainObjects = []
        for qDomain in items_paged:
            (
                domainObject,
                _is_created,
            ) = lib.db.getcreate.getcreate__SslDomain__by_domainName(
                ctx, qDomain.domain_name, is_from_queue_domain=True
            )
            domainObjects.append(domainObject)
            qDomain.ssl_domain_id = domainObject.id
            ctx.dbSession.flush(objects=[qDomain])

        # create a dbUniqueFqdnSet for this.
        # TODO - should we delete this if we fail? or keep for the CSR record
        #      - rationale is that on another pass, we would have a different fqdn set
        (
            dbUniqueFqdnSet,
            _is_created,
        ) = lib.db.getcreate.getcreate__SslUniqueFQDNSet__by_domainObjects(
            ctx, domainObjects
        )

        # update the event
        event_payload_dict["ssl_unique_fqdn_set_id"] = dbUniqueFqdnSet.id
        dbOperationsEvent.set_event_payload(event_payload_dict)
        ctx.dbSession.flush(objects=[dbOperationsEvent])
        transaction.commit()

        # do commit, just because we may have created a private key
        transaction.commit()

        dbServerCertificate = None
        try:
            domain_names = [d.domain_name for d in domainObjects]
            dbServerCertificate = lib.db.actions.do__CertificateRequest__AcmeV2_Automated(
                ctx, domain_names, dbAccountKey=dbAccountKey, dbPrivateKey=dbPrivateKey
            )
            for qdomain in items_paged:
                # this may have committed
                qdomain.timestamp_processed = timestamp_transaction
                ctx.dbSession.flush(objects=[qdomain])

            event_payload_dict["status"] = "success"
            event_payload_dict["certificate.id"] = dbServerCertificate.id
            dbOperationsEvent.set_event_payload(event_payload_dict)
            ctx.dbSession.flush(objects=[dbOperationsEvent])

        except errors.DomainVerificationError as exc:
            event_payload_dict["status"] = "error - DomainVerificationError"
            event_payload_dict["error"] = str(exc)
            dbOperationsEvent.set_event_payload(event_payload_dict)
            ctx.dbSession.flush(objects=[dbOperationsEvent])

            _timestamp = ctx.timestamp
            for qd in items_paged:
                _log_object_event(
                    ctx,
                    dbOperationsEvent=dbOperationsEvent,
                    event_status_id=model_utils.SslOperationsEventType.from_string(
                        "queue_domain__process__fail"
                    ),
                    dbQueueDomain=qd,
                )
            raise

        _timestamp = ctx.timestamp
        for qd in items_paged:
            _log_object_event(
                ctx,
                dbOperationsEvent=dbOperationsEvent,
                event_status_id=model_utils.SslOperationsEventType.from_string(
                    "queue_domain__process__success"
                ),
                dbQueueDomain=qd,
            )

        return True

    except Exception as exc:
        raise


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def queue_renewals__update(ctx, fqdns_ids_only=None):
    renewals = []
    results = []
    try:
        event_type = model_utils.SslOperationsEventType.from_string(
            "queue_renewal__update"
        )
        event_payload_dict = utils.new_event_payload_dict()
        dbOperationsEvent = log__SslOperationsEvent(ctx, event_type, event_payload_dict)
        if fqdns_ids_only:
            for fqdns_id in fqdns_ids_only:
                dbQueueRenewal = lib.db.create._create__SslQueueRenewal_fqdns(
                    ctx, fqdns_id
                )
                renewals.append(dbQueueRenewal)
            event_payload_dict["ssl_unique_fqdn_set-queued.ids"] = ",".join(
                [str(sid) for sid in fqdns_ids_only]
            )
        else:
            _expiring_days = 28
            _until = ctx.timestamp + datetime.timedelta(days=_expiring_days)
            _subquery_already_queued = (
                ctx.dbSession.query(
                    model_objects.SslQueueRenewal.ssl_server_certificate_id
                )
                .filter(
                    model_objects.SslQueueRenewal.timestamp_processed.op("IS")(None),
                    model_objects.SslQueueRenewal.process_result.op("IS NOT")(True),
                )
                .subquery()
            )
            _core_query = ctx.dbSession.query(
                model_objects.SslServerCertificate
            ).filter(
                model_objects.SslServerCertificate.is_active.op("IS")(True),
                model_objects.SslServerCertificate.is_auto_renew.op("IS")(True),
                model_objects.SslServerCertificate.is_renewed.op("IS NOT")(True),
                model_objects.SslServerCertificate.timestamp_expires <= _until,
                model_objects.SslServerCertificate.id.notin_(_subquery_already_queued),
            )
            results = _core_query.all()
            for cert in results:
                # this will call `_log_object_event` as needed
                dbQueueRenewal = lib.db.create._create__SslQueueRenewal(ctx, cert)
                renewals.append(dbQueueRenewal)
            event_payload_dict["ssl_certificate-queued.ids"] = ",".join(
                [str(c.id) for c in results]
            )

        event_payload_dict["sql_queue_renewals.ids"] = ",".join(
            [str(c.id) for c in renewals]
        )
        dbOperationsEvent.set_event_payload(event_payload_dict)
        ctx.dbSession.flush(objects=[dbOperationsEvent])

        return True

    except Exception as exc:
        raise


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def queue_renewals__process(ctx):
    """
    process the queue
    in order to best deal with transactions, we do 1 queue item at a time and redirect to process more
    """
    rval = {
        "count_total": None,
        "count_success": 0,
        "count_fail": 0,
        "count_remaining": 0,
        "failures": {},
    }
    event_type = model_utils.SslOperationsEventType.from_string(
        "queue_renewal__process"
    )
    event_payload_dict = utils.new_event_payload_dict()
    dbOperationsEvent = log__SslOperationsEvent(ctx, event_type, event_payload_dict)
    items_count = lib.db.get.get__SslQueueRenewal__count(ctx, unprocessed_only=True)
    rval["count_total"] = items_count
    rval["count_remaining"] = items_count
    if items_count:
        items_paged = lib.db.get.get__SslQueueRenewal__paginated(
            ctx, unprocessed_only=True, limit=1, offset=0, eagerload_renewal=True
        )

        dbAccountKeyDefault = None
        _need_default_AccountKey = False
        for dbQueueRenewal in items_paged:
            if (
                (not dbQueueRenewal.server_certificate)
                or (not dbQueueRenewal.server_certificate.ssl_acme_account_key_id)
                or (
                    not dbQueueRenewal.server_certificate.ssl_acme_account_key.is_active
                )
            ):
                _need_default_AccountKey = True
                break

        dbPrivateKeyDefault = None
        _need_default_PrivateKey = False
        for dbQueueRenewal in items_paged:
            if (
                (not dbQueueRenewal.server_certificate)
                or (not dbQueueRenewal.server_certificate.ssl_private_key_id__signed_by)
                or (not dbQueueRenewal.server_certificate.private_key.is_active)
            ):
                _need_default_PrivateKey = True
                break

        if _need_default_AccountKey:
            # raises an error if we fail
            dbAccountKeyDefault = _get_default_AccountKey(ctx)

        if _need_default_PrivateKey:
            # raises an error if we fail
            dbPrivateKeyDefault = _get_default_PrivateKey(ctx)

        for dbQueueRenewal in items_paged:
            if dbQueueRenewal not in ctx.dbSession:
                dbQueueRenewal = ctx.dbSession.merge(dbQueueRenewal)

            if dbAccountKeyDefault:
                if dbAccountKeyDefault not in ctx.dbSession:
                    dbAccountKeyDefault = ctx.dbSession.merge(dbAccountKeyDefault)
            if ctx.dbOperationsEvent not in ctx.dbSession:
                ctx.dbOperationsEvent = ctx.dbSession.merge(ctx.dbOperationsEvent)
            if dbOperationsEvent not in ctx.dbSession:
                dbOperationsEvent = ctx.dbSession.merge(dbOperationsEvent)

            dbServerCertificate = None
            _dbAccountKey = dbQueueRenewal.renewal_AccountKey or dbAccountKeyDefault
            _dbPrivateKey = dbQueueRenewal.renewal_PrivateKey or dbPrivateKeyDefault
            try:
                timestamp_attempt = datetime.datetime.utcnow()
                dbServerCertificate = lib.db.actions.do__CertificateRequest__AcmeV2_Automated(
                    ctx,
                    dbQueueRenewal.domains_as_list,
                    dbAccountKey=_dbAccountKey,
                    dbPrivateKey=_dbPrivateKey,
                    dbServerCertificate__renewal_of=dbQueueRenewal.server_certificate,
                    dbQueueRenewal__of=dbQueueRenewal,
                )
                if dbServerCertificate:
                    _log_object_event(
                        ctx,
                        dbOperationsEvent=dbOperationsEvent,
                        event_status_id=model_utils.SslOperationsEventType.from_string(
                            "queue_renewal__process__success"
                        ),
                        dbQueueRenewal=dbQueueRenewal,
                    )
                    rval["count_success"] += 1
                    rval["count_remaining"] -= 1
                    dbQueueRenewal.process_result = True
                    dbQueueRenewal.timestamp_process_attempt = timestamp_attempt
                    dbQueueRenewal.ssl_server_certificate_id__renewed = (
                        dbServerCertificate.id
                    )
                    ctx.dbSession.flush(objects=[dbQueueRenewal])

                else:
                    raise ValueError("what happened?")

            except Exception as exc:

                if dbOperationsEvent not in ctx.dbSession:
                    dbOperationsEvent = ctx.dbSession.merge(dbOperationsEvent)
                if dbQueueRenewal not in ctx.dbSession:
                    dbQueueRenewal = ctx.dbSession.merge(dbQueueRenewal)
                dbQueueRenewal.process_result = False
                dbQueueRenewal.timestamp_process_attempt = timestamp_attempt
                ctx.dbSession.flush(objects=[dbQueueRenewal])

                _log_object_event(
                    ctx,
                    dbOperationsEvent=dbOperationsEvent,
                    event_status_id=model_utils.SslOperationsEventType.from_string(
                        "queue_renewal__process__fail"
                    ),
                    dbQueueRenewal=dbQueueRenewal,
                )
                rval["count_fail"] += 1
                if isinstance(exc, errors.DomainVerificationError):
                    rval["failures"][dbQueueRenewal.id] = str(exc)
                elif isinstance(exc, errors.DomainVerificationError):
                    rval["failures"][dbQueueRenewal.id] = str(exc)
                else:
                    raise
        event_payload_dict["rval"] = rval
        if dbOperationsEvent not in ctx.dbSession:
            dbOperationsEvent = ctx.dbSession.merge(dbOperationsEvent)
        dbOperationsEvent.set_event_payload(event_payload_dict)
        ctx.dbSession.flush(objects=[dbOperationsEvent])
    return rval


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


__all__ = (
    "dequeue_QueuedDomain",
    "queue_domains__add",
    "queue_domains__process",
    "queue_renewals__update",
    "queue_renewals__process",
)
