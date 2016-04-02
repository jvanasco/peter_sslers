
<%def name="table_to_certificates(to_certificates, show_domains=False, show_domains_title='domains', show_expiring_days=False)">
    <table class="table table-striped">
        <thead>
            <tr>
                <th>id</th>
                <th>active?</th>
                <th>timestamp_signed</th>
                <th>timestamp_expires</th>
                % if show_expiring_days:
                    <th>expiring days</th>
                % endif
                % if show_domains:
                    <th>${show_domains_title}</th>
                % endif
            </tr>
        </thead>
        <tbody>
        % for to_cert in to_certificates:
            <tr>
                <td><a class="label label-info" href="/.well-known/admin/certificate/${to_cert.certificate.id}">&gt; ${to_cert.certificate.id}</a></td>
                <td>
                    <span class="label label-${'success' if to_cert.certificate.is_active else 'warning'}">
                        ${'Active' if to_cert.certificate.is_active else 'inactive'}
                    </span>
                </td>
                <td><timestamp>${to_cert.certificate.timestamp_signed}</timestamp></td>
                <td><timestamp>${to_cert.certificate.timestamp_expires or ''}</timestamp></td>
                % if show_expiring_days:
                    <td>
                        <span class="label label-${to_cert.certificate.expiring_days_label}">
                            ${to_cert.certificate.expiring_days}
                        </span>
                    </td>
                % endif
                % if show_domains:
                     <td>${to_cert.certificate.domains_as_string}</td>
                % endif
            </tr>
        % endfor
        </tbody>
    </table>
</%def>


<%def name="table_to_certificate_requests(to_certificate_requests, show_domains=False)">
    <table class="table table-striped table-condensed">
        <thead>
            <tr>
                <th>id</th>
                <th>active?</th>
                <th>type?</th>
                <th>timestamp_verified</th>
                <th>challenge_key</th>
                <th>challenge_text</th>
            </tr>
        </thead>
        <tbody>
        % for to_cr in to_certificate_requests:
            <tr>
                <td>
                    <a  class="label label-info"
                        href="/.well-known/admin/certificate_request/${to_cr.certificate_request.id}">&gt; ${to_cr.certificate_request.id}</a>
                </td>
                <td>
                    <span class="label label-${'success' if to_cr.certificate_request.is_active else 'warning'}">
                        ${'Active' if to_cr.certificate_request.is_active else 'inactive'}
                    </span>
                </td>
                <td>
                    <span class="label label-defaul">${to_cr.certificate_request.certificate_request_type}</span>
                </td>                
                <td><timestamp>${to_cr.timestamp_verified or ''}</timestamp></td>
                <td><code>${to_cr.challenge_key or ''}</code></td>
                <td><code>${to_cr.challenge_text or ''}</code></td>
            </tr>
        % endfor
        </tbody>
    </table>
</%def>


<%def name="table_certificates__list(certificates, show_domains=False, show_expiring_days=False)">
    <table class="table table-striped">
        <thead>
            <tr>
                <th>id</th>
                <th>active?</th>
                <th>timestamp_signed</th>
                <th>timestamp_expires</th>
                % if show_expiring_days:
                    <th>expiring days</th>
                % endif
                % if show_domains:
                    <th>domains</th>
                % endif
            </tr>
        </thead>
        <tbody>
        % for cert in certificates:
            <tr>
                <td><a class="label label-info" href="/.well-known/admin/certificate/${cert.id}">&gt; ${cert.id}</a></td>
                <td>
                    <span class="label label-${'success' if cert.is_active else 'warning'}">
                        ${'Active' if cert.is_active else 'inactive'}
                    </span>
                </td>
                <td><timestamp>${cert.timestamp_signed}</timestamp></td>
                <td><timestamp>${cert.timestamp_expires or ''}</timestamp></td>
                % if show_expiring_days:
                    <td>
                        <span class="label label-${cert.expiring_days_label}">
                            ${cert.expiring_days}
                        </span>
                    </td>
                % endif
                % if show_domains:
                    <td>${cert.domains_as_string}</td>
                % endif
            </tr>
        % endfor
        </tbody>
    </table>
</%def>


<%def name="table_certificate_requests__list(certificate_requests, show_domains=False, show_certificate=False)">
    <table class="table table-striped table-condensed">
        <thead>
            <tr>
                <th>id</th>
                <th>type</th>
                <th>active?</th>
                <th>error?</th>
                % if show_certificate:
                    <th>cert issued?</th>
                % endif
                <th>timestamp_started</th>
                <th>timestamp_finished</th>
                % if show_domains:
                    <th>domains</th>
                % endif
            </tr>
        </thead>
        <tbody>
        % for certificate_request in certificate_requests:
            <tr>
                <td>
                    <a  class="label label-info"
                        href="/.well-known/admin/certificate_request/${certificate_request.id}">&gt; ${certificate_request.id}</a>
                </td>
                <td>
                    <span class="label label-default">${certificate_request.certificate_request_type}</span>
                </td>                
                <td>
                    <span class="label label-${'success' if certificate_request.is_active else 'warning'}">
                        ${'Active' if certificate_request.is_active else 'inactive'}
                    </span>
                </td>
                <td>
                    <span class="label label-${'danger' if certificate_request.is_error else 'default'}">
                        ${'Error' if certificate_request.is_error else 'ok'}
                    </span>
                </td>
                % if show_certificate:
                    <td>
                        % if certificate_request.signed_certificate:
                            <a  class="label label-info"
                                href="/.well-known/admin/certificate/${certificate_request.signed_certificate.id}">&gt; ${certificate_request.signed_certificate.id}</a>
                        % else:
                            &nbsp;
                        % endif
                    </td>                
                % endif
                <td><timestamp>${certificate_request.timestamp_started}</timestamp></td>
                <td><timestamp>${certificate_request.timestamp_finished or ''}</timestamp></td>
                % if show_domains:
                    <td>${certificate_request.domains_as_string}</td>
                % endif
            </tr>
        % endfor
        </tbody>
    </table>
</%def>


<%def name="table_LetsencryptCertificateRequest2LetsencryptDomain(lcr2mds, request_inactive=None, active_domain_id=None, perspective=None)">
    % if perspective == 'certificate_request':
        <table class="table table-striped table-condensed">
            <thead>
                <tr>
                    <th>domain</th>
                    <th>timestamp_verified</th>
                    <th>challenge_key</th>
                    <th>challenge_text</th>
                    <th>configured?</th>
                </tr>
            </thead>
            <tbody>
                % for to_d in lcr2mds:
                    <tr>
                        <td><a href="/.well-known/admin/domain/${to_d.domain.id}" class="label label-info">&gt; ${to_d.domain.id}</a> ${to_d.domain.domain_name}</td>
                        <td><timestamp>${to_d.timestamp_verified or ''}</timestamp></td>
                        <td><code>${to_d.challenge_key or ''}</code></td>
                        <td><code>${to_d.challenge_text or ''}</code></td>
                        <td>
                            % if to_d.is_configured:
                                % if request_inactive:
                                    <span class="label label-success">configured</span>
                                % else:
                                    <a  class="label label-success"
                                        href="/.well-known/admin/certificate_request/${LetsencryptCertificateRequest.id}/process/domain/${to_d.domain.id}"
                                        >&gt; configured</a>
                                % endif
                            % else:
                                % if request_inactive:
                                    <span class="label label-warning">not configured</span>
                                % else:
                                    <a  class="label label-warning"
                                        href="/.well-known/admin/certificate_request/${LetsencryptCertificateRequest.id}/process/domain/${to_d.domain.id}"
                                        >&gt; configure!</a>
                                % endif
                            % endif
                        </td>
                    </tr>
                % endfor
            </tbody>
        </table>
    % elif perspective == 'certificate_request_sidebar':
        <table class="table table-striped table-condensed">
            <thead>
                <tr>
                    <th>active?</th>
                    <th>domain</th>
                    <th>configured?</th>
                    <th>verified?</th>
                    <th>test</th>
                </tr>
            </thead>
            <tbody>
            % for to_d in LetsencryptCertificateRequest.certificate_request_to_domains:
                <tr>
                    <td>
                        % if active_domain_id == to_d.letsencrypt_domain_id:
                            <span class="label label-success">active</span>
                        % endif
                    </td>
                    <td>
                        <span class="label label-default"
                        >
                            ${to_d.domain.domain_name}
                        </span>
                    </td>
                    <td>
                        % if active_domain_id == to_d.letsencrypt_domain_id:
                            % if to_d.is_configured:
                                <span 
                                    class="label label-success">configured</span>
                            % else:
                                <span
                                    class="label label-warning">not configured</span>
                            % endif
                        % else:
                            % if to_d.is_configured:
                                <a 
                                    href="/.well-known/admin/certificate_request/${LetsencryptCertificateRequest.id}/process/domain/${to_d.letsencrypt_domain_id}"
                                    class="label label-success">&gt; configured</a>
                            % else:
                                <a href="/.well-known/admin/certificate_request/${LetsencryptCertificateRequest.id}/process/domain/${to_d.letsencrypt_domain_id}"
                                    class="label label-warning">
                                    % if request_inactive:
                                        &gt; not configured
                                    % else:
                                        &gt; configure
                                    % endif
                                    </a>
                            % endif
                        % endif
                    </td>
                    <td>
                        % if to_d.timestamp_verified:
                            <span class="label label-success">verified</span>                            
                        % else:
                            &nbsp;
                        % endif
                    </td>
                    <td>
                        % if to_d.is_configured:
                            <a  class="label label-info"
                                target="_blank"
                                href="http://${to_d.domain.domain_name}/.well-known/acme-challenge/${to_d.challenge_key}?test=1"
                            >
                                &gt; test
                            </a>
                        % endif
                    </td>
                </tr>
            % endfor
            </tbody>
        </table>

    % else:
        <!-- table_LetsencryptCertificateRequest2LetsencryptDomain missing perspective -->
    % endif
</%def>


<%def name="table_LetsencryptOperationsEvents(LetsencryptOperationsEvents, show_event=None)">
    <%
        event_id = None
        if show_event is not None:
            event_id = request.params.get('event.id')
    %>
    <table class="table table-striped table-condensed">
        <thead>
            <tr>
                <th>id</th>
                <th>child of</th>
                <th>event_type</th>
                <th>event timestamp</th>
            </tr>
        </thead>
        <tbody>
            % for event in LetsencryptOperationsEvents:
                <tr class="${'success' if event_id == str(event.id) else ''}">
                    <td><span class="label label-default">${event.id}</span></td>
                    <td>
                        % if event.letsencrypt_sync_event_id_child_of:
                            <span class="label label-default">${event.letsencrypt_sync_event_id_child_of}</span>
                        % endif
                    </td>
                    <td><span class="label label-default">${event.event_type_text}</span></td>
                    <td><timestamp>${event.timestamp_operation}</timestamp></td>
                </tr>
            % endfor
        </tbody>
    </table>
</%def>


<%def name="info_AccountKey()">
    <h3>Need a Private Key?</h3>
        <p>Use an Existing LetsEncrypt key from their client.  This is the easiest way to register with LetsEncrypt.</p>
        <p>
            You have to convert the key from <code>jwk</code> to <code>pem</code> format.  
            The easiest way is outlined on this github page: <a href="https://github.com/diafygi/acme-tiny">https://github.com/diafygi/acme-tiny</a>
        </p>
</%def>


<%def name="info_PrivateKey()">
    <h3>Need a Private Key?</h3>
        <p>NOTE: you can not use your account private key as your private key for signing domains!</p>
        <p>
            <code>openssl genrsa 4096 > domain.key</code>
        </p>
</%def>


<%def name="info_CACertificate()">
    <h3>What are CA Certificates?</h3>
    <p>
        These are the trusted(?) certs that CertificateAuthorities use to sign your certs.  They are used for building fullchains.
        Often these are called 'chain.pem'.
    </p>
</%def>


<%def name="formgroup__account_key_file(show_text=False)">
    <div class="form-group clearfix">
        <label for="f1-account_key_file">Account Private Key</label>
        <input class="form-control" type="file" id="f1-account_key_file" name="account_key_file" />
        <p class="help-block">
            Enter your LetsEncrypted registered PRIVATE AccountKey above in PEM format; this will be used to sign your request.
            This is saved ot the DB and is used to track requests and handle reiussues.
        </p>
        % if show_text:
            <label for="f1-account_key">Account Private Key [text]</label>
            <textarea class="form-control" rows="4" name="account_key" id="f1-account_key"></textarea>
            <p class="help-block">
                Alternately, provide text inline.
            </p>
        % endif
    </div>
</%def>


<%def name="formgroup__private_key_file(show_text=False)">
    <div class="form-group clearfix">
        <label for="f1-private_key_file">Private Key</label>
        <input class="form-control" type="file" id="f1-private_key_file" name="private_key_file" />
        <p class="help-block">
            Enter your PRIVATE key used to sign CSRs above in PEM format; this will be used to create a CSR used for configuring servers/chains and matched against existing issued certs.
            This WILL be saved.
        </p>
        % if show_text:
            <label for="f1-private_key">Private Key [text]</label>
            <textarea class="form-control" rows="4" name="private_key" id="f1-private_key"></textarea>
            <p class="help-block">
                Alternately, provide text inline.
            </p>
        % endif
    </div>
</%def>


<%def name="formgroup__certificate_file(show_text=False)">
    <div class="form-group clearfix">
        <label for="f1-certificate_file">Signed Certificate</label>
        <input class="form-control" type="file" id="f1-certificate_file" name="certificate_file" />
        <p class="help-block">
            Enter a Signed Certificate above in PEM format.
            This is something that has been signed by a CA.
        </p>
        % if show_text:
            <label for="f1-certificate">Signed Certificate [text]</label>
            <textarea class="form-control" rows="4" name="certificate" id="f1-certificate"></textarea>
            <p class="help-block">
                Alternately, provide text inline.
            </p>
        % endif
    </div>
</%def>


<%def name="formgroup__chain_file(show_text=False)">
    <div class="form-group clearfix">
        <label for="f1-chain_file">Chain File</label>
        <input class="form-control" type="file" id="f1-chain_file" name="chain_file" />
        <p class="help-block">
            This should be the public cert of the upstream signer.
        </p>
        % if show_text:
            <label for="f1-chain">Chain File [text]</label>
            <textarea class="form-control" rows="4" name="chain" id="f1-chain"></textarea>
            <p class="help-block">
                Alternately, provide text inline.
            </p>
        % endif
    </div>
</%def>



<%def name="formgroup__chain_bundle_file()">
    <div class="form-group clearfix">
        <label for="f1-isrgrootx1_file">ISRG Root X1</label>
        <input class="form-control" type="file" id="f1-isrgrootx1_file" name="isrgrootx1_file" />
        <p class="help-block">
            As linked to from https://letsencrypt.org/certificates/
        </p>
    </div>
    <hr/>

    <div class="form-group clearfix">
        <label for="f1-le_x1_auth_file">Let’s Encrypt Authority X1</label>
        <input class="form-control" type="file" id="f1-le_x1_auth_file" name="le_x1_auth_file" />
        <p class="help-block">
            As linked to from https://letsencrypt.org/certificates/
        </p>
    </div>
    <hr/>

    <div class="form-group clearfix">
        <label for="f1-le_x1_cross_signed_file">Let’s Encrypt Authority X1 (IdenTrust cross-signed)</label>
        <input class="form-control" type="file" id="f1-le_x1_cross_signed_file" name="le_x1_cross_signed_file" />
        <p class="help-block">
            As linked to from https://letsencrypt.org/certificates/
        </p>
    </div>
    <hr/>

    <div class="form-group clearfix">
        <label for="f1-le_x2_auth_file">Let’s Encrypt Authority X2</label>
        <input class="form-control" type="file" id="f1-le_x2_auth_file" name="le_x2_auth_file" />
        <p class="help-block">
            As linked to from https://letsencrypt.org/certificates/
        </p>
    </div>
    <hr/>

    <div class="form-group clearfix">
        <label for="f1-le_x2_cross_signed_file">Let’s Encrypt Authority X2 (IdenTrust cross-signed)</label>
        <input class="form-control" type="file" id="f1-le_x2_cross_signed_file" name="le_x2_cross_signed_file" />
        <p class="help-block">
            As linked to from https://letsencrypt.org/certificates/
        </p>
    </div>
    <hr/>

</%def>


<%def name="formgroup__domain_names()">
    <div class="form-group clearfix">
        <label for="f1-domain_names">Domain Names</label>
        <textarea class="form-control" rows="4" name="domain_names" id="f1-domain_names"></textarea>
        <p class="help-block">
            A comma(,) separated list of domain names.
        </p>
    </div>
</%def>


<%def name="nav_pagination(pager)">
    <% if not pager: return '' %>
    <center>
        <nav>
            <ul class="pagination">
                % if pager.start > 1:
                    <li>
                        <a href="${pager.template.format(max(pager.current-pager.range_num, 1))}" aria-label="Previous">
                            <span aria-hidden="true">&laquo;</span>
                        </a>
                    </li>
                % endif
                % for p in pager.pages:
                    <li ${'class="active"' if pager.current == p else ''|n}><a href="${pager.template.format(p)}">${p}</a></li>
                % endfor
                % if pager.end < pager.page_num:
                    <li>
                        <a href="${pager.template.format(min(pager.start+pager.range_num, pager.page_num-pager.range_num))}" aria-label="Next">
                            <span aria-hidden="true">&raquo;</span>
                        </a>
                    </li>
                % endif
            </ul>
        </nav>
    </center>
</%def>


<%def name="nav_pager(see_all_url, see_all_text='See All')">
    <nav>
      <ul class="pager">
        <li>
            <a 
                href="${see_all_url}"
            >${see_all_text}</a>
        </li>
      </ul>
    </nav>
</%def>


<%def name="operations_options(enable_redis=False, enable_nginx=False)">
    % if enable_redis:
        <p>
            <a  href="/.well-known/admin/operations/redis"
                class="btn btn-info"
            >Redis Operations</a><br/>
        </p>
    % endif
    % if enable_nginx:
        <p>
            <a  href="/.well-known/admin/operations/nginx"
                class="btn btn-info"
            >nginx Operations</a><br/>
        </p>
    % endif
    <p>
        <a  href="/.well-known/admin/operations/ca_certificate_probes"
            class="btn btn-info"
        >CA Certificate Probes</a><br/>
        <em>${request.text_library.info_CACertificateProbes[0]}</em>
    </p>
    <p>
        <a  href="/.well-known/admin/operations/deactivate_expired"
            class="btn btn-primary"
        >Deactivate Expired Certificates</a><br/>
    </p>
    <p>
        <a  href="/.well-known/admin/operations/update_recents"
            class="btn btn-primary"
        >Update Recents</a><br/>
    </p>
</%def>