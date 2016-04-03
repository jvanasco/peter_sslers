<%inherit file="/admin/-site_template.mako"/>
<%namespace name="admin_partials" file="/admin/-partials.mako"/>


<%block name="breadcrumb">
    <ol class="breadcrumb">
        <li><a href="/.well-known/admin">Admin</a></li>
        <li><a href="/.well-known/admin/domains">Domains</a></li>
        <li><a href="/.well-known/admin/domain/${LetsencryptDomain.id}">Focus [${LetsencryptDomain.id}]</a></li>
        <li class="active">Unique FQDN Set</li>
    </ol>
</%block>


<%block name="page_header">
    <h2>Domain Focus - Unique FQDN Set</h2>
</%block>

    
<%block name="content_main">

    % if LetsencryptUniqueFQDNSets:
        ${admin_partials.nav_pagination(pager)}
        ${admin_partials.table_LetsencryptUniqueFQDNSets(LetsencryptUniqueFQDNSets)}
    % else:
        No known fqdn sets.
    % endif 

</%block>
