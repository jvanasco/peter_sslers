<%inherit file="/admin/-site_template.mako"/>
<%namespace name="admin_partials" file="/admin/-partials.mako"/>


<%block name="breadcrumb">
    <ol class="breadcrumb">
        ${request.breadcrumb_prefix|n}
        <li><a href="${admin_prefix}">Admin</a></li>
        <li><a href="${admin_prefix}/acme-orderlesss">ACME Orderless</a></li>
        <li><a href="${admin_prefix}/acme-orderlesss/${AcmeOrderless.id}" class="active">Focus - ${AcmeOrderless.id}</a></li>
    </ol>
</%block>


<%block name="page_header_col">
</%block>


<%block name="content_main">
    <div class="row">
        <div class="col-sm-12">

            <p>Workspace for
                <a  class="label label-default"
                    href="${admin_prefix}/acme-orderless/${AcmeOrderless.id}"
                >
                    <span class="glyphicon glyphicon-file" aria-hidden="true"></span>
                    AcmeOrderless-${AcmeOrderless.id}
                </a>
            </p>

            <p>
                <b>
                    This tool is a convenience wrapper for using another client to perform ACME Challenges.
                </b>
            </p>

            <p>The <code>token</code> is the name of the file letsencrypt expects at a url.
                The <code>keyauthorization</code> are the files contents.
                The <code>url</code> is the ACME url that handles the challenge, not your url.
            </p>

            <p>If letsencrypt says the url should be <code>example.com/acme-challenge/foo-bar-biz</code> , then the token is <code>foo-bar-biz</code></p>

            <p>
                note: Visiting a `test` URL will direct you to the actual verification URL with "?test=1" appended.  This string instructs the server to not log the visit.  If the "?test=1" string is missing, the server will log the visit.  This is used to track the ACME server verification visits.
            </p>
            
            <p>
                This orderless configuration is :
                % if AcmeOrderless.is_active:
                    <span class="label label-success">active</span>.
                    <form
                        action="${admin_prefix}/acme-orderless/${AcmeOrderless.id}/deactivate"
                        method="POST"
                        enctype="multipart/form-data"
                    >
                        <button type="submit" class="btn btn-danger"><span class="glyphicon glyphicon-remove"></span> Deactivate</button>
                    </form>
                
                % else:
                    <span class="label label-danger">deactivated</span>.
                % endif
            </p>
            
        </div>
    </div>
    <div class="row">
        <div class="col-sm-12">
            <h5>Challenges in this Orderless Request</h5>
            
            <form
                action="${admin_prefix}/acme-orderless/${AcmeOrderless.id}/update"
                method="POST"
                enctype="multipart/form-data"
            >
                <% form = request.pyramid_formencode_classic.get_form() %>
                ${form.html_error_main_fillable()|n}
                <%
                    cols = ('Challenge',
                            'Domain',
                            'Test',
                            'Type',
                            'Status',
                            'Token',
                            'KeyAuthorization',
                            'challenge_url',
                            'updated',
                            )
                %>

                <table class="table table-condensed table-striped">
                    <thead>
                        <tr>
                            % for col in cols:
                                <th>${col}</th>
                            % endfor
                        </tr>
                    </thead>
                    <tbody>
                        % for challenge in AcmeOrderless.acme_orderless_challenges:
                            <tr>
                                % for col in cols:
                                    <td>
                                        % if col == 'Challenge':
                                            <a class="label label-info" href="${admin_prefix}/acme-orderless/${AcmeOrderless.id}/acme-orderless-challenge/${challenge.id}">
                                                <span class="glyphicon glyphicon-file" aria-hidden="true"></span>
                                                AcmeOrderlessChallenge-${challenge.id}
                                            </a>
                                        % elif col == 'Domain':
                                            <a class="label label-info" href="${admin_prefix}/domain/${challenge.domain_id}">
                                                <span class="glyphicon glyphicon-file" aria-hidden="true"></span>
                                                ${challenge.domain_id}
                                                |
                                                ${challenge.domain_name}
                                            </a>
                                        % elif col == 'Test':
                                            % if challenge.acme_challenge_type == "http-01":
                                                % if challenge.token:
                                                    <a href="http://${challenge.domain.domain_name}/.well-known/acme-challenge/${challenge.token}?test=1"
                                                       target="_blank"
                                                       class="btn btn-${"success" if AcmeOrderless.is_active else "danger"}"
                                                    >
                                                        <span class="glyphicon glyphicon-link" aria-hidden="true"></span>
                                                    </a>
                                                % endif
                                            % endif
                                        % elif col == 'Type':
                                            <span class="label label-default">${challenge.acme_challenge_type}</span>
                                        % elif col == 'Status':
                                            <span class="label label-default">${challenge.acme_status_challenge}</span>

                                        % elif col == 'Token':
                                            <input class="form-control" type="text" name="${challenge.id}_token" value="${challenge.token or ''}"/>
                                        % elif col == 'KeyAuthorization':
                                            <input class="form-control" type="text" name="${challenge.id}_keyauthorization" value="${challenge.keyauthorization or ''}"/>
                                        % elif col == 'challenge_url':
                                            <input class="form-control" type="text" name="${challenge.id}_url" value="${challenge.challenge_url or ''}"/>
                                        % elif col == 'updated':
                                            <timestamp>${challenge.timestamp_updated if challenge.timestamp_updated else ''}</timestamp>
                                        % endif
                                    </td>
                                % endfor
                            </tr>
                        % endfor
                    </tbody>
                </table>
                <button type="submit" class="btn btn-primary"><span class="glyphicon glyphicon-upload"></span> Submit</button>
            </form>
            
            % if len(AcmeOrderless.acme_orderless_challenges) < 50:
                <hr/>
                <hr/>
                <form
                    action="${admin_prefix}/acme-orderless/${AcmeOrderless.id}/add"
                    method="POST"
                    enctype="multipart/form-data"
                >
                    <div class="form-group">
                        <label for="add_domain">Domain</label>
                        <input class="form-control" type="text" name="add_domain" value=""/>
                    </div>
                    <div class="form-group">
                        <label for="add_token">Token</label>
                        <input class="form-control" type="text" name="add_token" value=""/>
                    </div>
                    <div class="form-group">
                        <label for="add_keyauthorization">KeyAuthorization</label>
                        <input class="form-control" type="text" name="add_keyauthorization" value=""/>
                    </div>
                    <div class="form-group">
                        <label for="add_challenge_url">ChallengeURL</label>
                        <input class="form-control" type="text" name="add_challenge_url" value=""/>
                    </div>

                    <button type="submit" class="btn btn-primary"><span class="glyphicon glyphicon-upload"></span> Submit</button>
                </form>
            % else:
                Can not add items to this.
            % endif

        </div>
    </div>
</%block>
