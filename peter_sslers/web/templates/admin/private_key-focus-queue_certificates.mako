<%inherit file="/admin/-site_template.mako"/>
<%namespace name="admin_partials" file="/admin/-partials.mako"/>


<%block name="breadcrumb">
    <ol class="breadcrumb">
        ${request.breadcrumb_prefix|n}
        <li><a href="${admin_prefix}">Admin</a></li>
        <li><a href="${admin_prefix}/private-keys">Private Keys</a></li>
        <li><a href="${admin_prefix}/private-key/${PrivateKey.id}">Focus [${PrivateKey.id}]</a></li>
        <li class="active">QueueCertificates</li>
    </ol>
</%block>


<%block name="page_header_col">
    <h2>Private Key - Focus | QueueCertificates</h2>
</%block>


<%block name="content_main">
    <div class="row">
        <div class="col-sm-12">
            % if QueueCertificates:
                ${admin_partials.nav_pagination(pager)}
                ${admin_partials.table_QueueCertificates(QueueCertificates, perspective="PrivateKey")}
            % else:
                No known QueueCertificates.
            % endif
        </div>
    </div>
</%block>
