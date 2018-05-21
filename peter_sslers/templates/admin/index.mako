<%inherit file="/admin/-site_template.mako"/>
<%namespace name="admin_partials" file="/admin/-partials.mako"/>


<%block name="page_header_col">
##    <h2>Admin Index</h2>
</%block>


<%block name="content_main">
    <div class="row">
        <div class="col-sm-4 pull-right">
            <a  href="${admin_prefix}/help"
                class="btn btn-xs btn-warning"
            >
                <span class="glyphicon glyphicon-info-sign" aria-hidden="true"></span>
                Help</a>
            <a  href="${admin_prefix}/settings"
                class="btn btn-xs btn-warning"
            >
                <span class="glyphicon glyphicon-info-sign" aria-hidden="true"></span>
                Settings</a>
            <a href="${admin_prefix}/api"
                class="btn btn-xs btn-warning"
            >
                <span class="glyphicon glyphicon-transfer" aria-hidden="true"></span>
                api endpoints
                </a>
        </div>
    </div>

    <div class="row">
        <div class="col-sm-4">
            <h3>Enrolled Records</h3>
            <ul class="nav nav-pills nav-stacked">
                <li><a href="${admin_prefix}/account-keys"
                       title="${request.text_library.info_AccountKeys[0]}"
                    >
                    <span class="glyphicon glyphicon-list" aria-hidden="true"></span>
                    account-keys</a></li>
                <li><a href="${admin_prefix}/certificate-requests"
                       title="${request.text_library.info_CertificateRequests[0]}"
                    >
                    <span class="glyphicon glyphicon-list" aria-hidden="true"></span>
                    certificate-requests
                    </a>
                    </li>
                <li><a href="${admin_prefix}/certificates"
                       title="${request.text_library.info_Certificates[0]}"
                    >
                    <span class="glyphicon glyphicon-list" aria-hidden="true"></span>
                    certificates</a></li>
                <li><a href="${admin_prefix}/domains"
                       title="${request.text_library.info_Domains[0]}"
                    >
                    <span class="glyphicon glyphicon-list" aria-hidden="true"></span>
                    domains</a></li>
                <li><a href="${admin_prefix}/private-keys"
                       title="${request.text_library.info_PrivateKeys[0]}"
                    >
                    <span class="glyphicon glyphicon-list" aria-hidden="true"></span>
                    private-keys</a></li>
            </ul>

            <h3>Configuration</h3>
            <ul class="nav nav-pills nav-stacked">
                <li><a href="${admin_prefix}/acme-providers"
                       title="Acme Providers"
                    >
                    <span class="glyphicon glyphicon-list" aria-hidden="true"></span>
                    acme-providers</a></li>
                <li><a href="${admin_prefix}/ca-certificates"
                       title="${request.text_library.info_CACertificates[0]}"
                    >
                    <span class="glyphicon glyphicon-list" aria-hidden="true"></span>
                    ca-certificates</a></li>
            </ul>


            <h3>Recordkeeping</h3>
            <ul class="nav nav-pills nav-stacked">
                <li><a href="${admin_prefix}/acme-event-logs"
                    >
                    <span class="glyphicon glyphicon-list" aria-hidden="true"></span>
                    acme-event-logs</a></li>
                <li><a href="${admin_prefix}/acme-challenge-logs"
                    >
                    <span class="glyphicon glyphicon-list" aria-hidden="true"></span>
                    acme-challenge-logs</a></li>
                <li><a href="${admin_prefix}/queue-domains"
                    >
                    <span class="glyphicon glyphicon-list" aria-hidden="true"></span>
                    queue-domains</a></li>
                <li><a href="${admin_prefix}/queue-renewals"
                    >
                    <span class="glyphicon glyphicon-list" aria-hidden="true"></span>
                    queue-renewals</a></li>
                <li><a href="${admin_prefix}/unique-fqdn-sets"
                       title="${request.text_library.info_UniqueFQDNs[0]}"
                    >
                    <span class="glyphicon glyphicon-list" aria-hidden="true"></span>
                    unique-fqdn-sets</a></li>
            </ul>
        </div>
        <div class="col-sm-4">
            <h3>Status</h3>
            <ul class="nav nav-pills nav-stacked">
                <li><a href="${admin_prefix}/api/nginx/status.json">
                    <span class="glyphicon glyphicon-file" aria-hidden="true"></span>
                    api : nginx/status.json</a></li>
            </ul>
            <h4>Tools</h4>
            <ul class="nav nav-pills nav-stacked">
                <li><a href="${admin_prefix}/domains/search">
                    <span class="glyphicon glyphicon-search" aria-hidden="true"></span>
                    search domains</a></li>
            </ul>
            ${admin_partials.operations_options(enable_redis=enable_redis,
                                                enable_nginx=enable_nginx,
                                                as_list=True,
                                                )}


        </div>
        <div class="col-sm-4">
            <h3>New Certificates</h3>
            <ul class="nav nav-pills nav-stacked">
                <li>
                    <a  href="${admin_prefix}/certificate-request/new-acme-automated"
                        title="${request.text_library.info_CertificateRequest_new_AcmeAutomated[0]}"
                    >
                    <span class="glyphicon glyphicon-wrench" aria-hidden="true"></span>
                    New: ACME Automated</a></li>
                % if request.registry.settings['enable_acme_flow']:
                    <li>
                        <a  href="${admin_prefix}/certificate-request/new-acme-flow"
                            title="${request.text_library.info_CertificateRequest_new_AcmeFlow[0]}"
                        >
                        <span class="glyphicon glyphicon-wrench" aria-hidden="true"></span>
                        New: ACME Flow</a></li>
                % endif
            </ul>

            <h3>Existing Certificates</h3>
            <ul class="nav nav-pills nav-stacked">
                <li>
                    <a  href="${admin_prefix}/certificate/upload"
                        title="${request.text_library.info_UploadExistingCertificate[0]}"
                    >
                    <span class="glyphicon glyphicon-upload" aria-hidden="true"></span>
                    Upload: Existing Certificate</a></li>
                <li>
                    <a  href="${admin_prefix}/private-key/upload"
                        title="${request.text_library.info_UploadPrivateKey[0]}"
                    >
                    <span class="glyphicon glyphicon-upload" aria-hidden="true"></span>
                    Upload: Private Key</a></li>
                <li>
                    <a  href="${admin_prefix}/account-key/upload"
                        title="${request.text_library.info_UploadAccountKey[0]}"
                    >
                    <span class="glyphicon glyphicon-upload" aria-hidden="true"></span>
                    Upload: Account Key</a></li>
                <li>
                    <a  href="${admin_prefix}/ca-certificate/upload"
                        title="${request.text_library.info_UploadCACertificate[0]}"
                    >
                    <span class="glyphicon glyphicon-upload" aria-hidden="true"></span>
                    Upload: CA Certificate</a></li>
            </ul>
        </div>
    </div>
</%block>
