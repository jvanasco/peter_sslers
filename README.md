peter_sslers README
================================

Peter SSLers *or how i stopped worrying and learned to love the ssl certificate*.

`peter_sslers` is a package designed to help *experienced* admins and devops people manage SSL Certificates and deploy them on larger systems.

What's in the box ?

* SSL Certificate Manager
* ACME v2 client for LetsEncrypt Certificate Authority
* OpenResty Lua module for Dynamic SSL Certificate Handling on the Nginx webserver

THIS CONTAINS EVERYTHING YOU NEED TO SSL-ERATE AN INIFINITELY SCALEABLE MULTI-SERVER OR MULTI-DOMAIN SETUP!!!

AMAZING, RIGHT?

This package is *not* aimed at casual or single-site users.  This package is *not* aimed at novice users.

Peter offers lightweight tools to centrally manage SSL Certificate data in a SQL database of your choice.

Peter combines an ACME v2 client designed to operate against the LetsEncrypt service, alongside tools designed to manage & deploy certificates.

The client supported ACME v1 until version `0.4.0`. Only ACME v2 is currently supported.

Peter's core tool is a lightweight database-backed `Pyramid` application that can:

* act as a client for the entire "LetsEncrypt" issuance process, operating behind a proxied webserver
* import existing ssl certificates
* ease provisioning certificates onto various servers
* browse certificate data and easily see what needs to be renewed
* communicate with a properly configured `OpenResty` enabled `Nginx` web server (see next section)
* translate certificates into different formats

Peter ships alongside a `Lua` `opm` module for the `OpenResty` framework on the `Nginx` server which will:

* dynamically request certificates from a primed Redis cache
* store data in shared `Nginx` worker memory and
* expose routes to flush the worker shared memory or expire select keys. 

The module is available in a separate project, https://github.com/aptise/peter_sslers-lua-resty and can be installed into your OpenResty/Nginx server via the `opm` package installer

The `Pyramid` based application can function as a daemon or a commandline script.  Most pages offer `.json` endpoints, so you can easily issue commands via `curl` and have human-readable data in a terminal window. Don't want to do things manually? Ok - everything was built to be readable on commandline browsers... yes, this is actually developed-for and tested-with lynx.

Do you like book-keeping?  Peter's `Pryamid` component logs everything into sql.  

Do you like cross-referencing?  Your certs are broken down into fields that are cross-referenced or searchable within Peter as well.

Peter has absolutely no security measures and should only be used by people who understand that (that should be a self-selecting group, because many people won't want this tool).  Peter is a honeybadger, he don't care.  He just takes what he wants.

Peter offers several commandline tools -- so spinning up a tool "webserver" mode may not be necessary at all -- or might only be needed for brief periods of time.

SqlAlchemy is the backing database library, so virtually any database can be used (SQLite, PostgreSQL, MySQL, Oracle, mssql, etc). `SQLite` is the default, but the package has been tested against PostgreSQL.  SQLite is actually kind of great, because a single `.sqlite` file can be sftp'd on-to and off-of different machines for distribution and local viewings.

Peter leverages the system's OpenSSL instead of using Python's modules. The reason is to minimize the amount of downloads/packages.

Although Python2 is no longer supported by Python, Python2 and Python3 are targeted platforms for this library.


## Why?

Most of us hate having to spend time on DevOps tasks.  Personally, I would rather spend time working on the core product or consumer products.  This tool was designed as a swiss-army-knife to streamline some tasks and troubleshoot a handful of issues with https hosting.  This is pre-release and still being worked on as it fixes new issues on a production system.  PRs are absolutely welcome, even if just fixes or additions to the test-suite.


## Status

This largely works for certificate management, manual/queued renewal and for transitions.

The endpoint related to "requesting" domains and handling dynamic queues of new certificates do not work yet.


# An important WARNING:

* This package DOES NOT USE/KNOW/CARE ABOUT SECURITY.
* This package manages PRIVATE SSL KEYS and makes them readable.
* If you do not know / are not really awesome with basic network security PLEASE DO NOT USE THIS.


# The Components

## "Peter SSLers" - a Pyramid Application

"Peter SSLers" is the core toolkit.  It is a `Pyramid` application that can be spun up as a webserver or used via a commandline interface.  Peter is your friend and handles all of the Certificate Management and translation functions for you.  He's a bit eccentric, but basically a good guy.

## "SSL Minnow" - The Datastore

By default, the "SSL Minnow" is a SQLite database `ssl_minnow.sqlite`.  It is the backing datastore for SSL Certificates and the operations log.  Your data is ONLY saved to the SSL Minnow - not to the filesystem like other LE clients - so you should be careful with it.  If the Minnow would be lost, it can not be recovered.  Be a good skipper, or your three hour tour could end up taking many years and might involve the Harlem Globetrotters.

## "Tools"

The "/tools" directory contains scripts useful for certificate operations.  Currently this includes:

* an `invoke` script for some miscellaneous tasks
* a sample `fake_server.py` that will spin up a server with routes that you can test against.  this will allow you to setup your integration without running peter_sslers
* a sample `fake_boulder.py` that will spin up a fake boulder server that can be used as a certificate authority when testing

## The OpenResty package

Available via the opm package manager:

	opm get peter_sslers-lua-resty

The source and docs are available on github https://github.com/aptise/peter_sslers-lua-resty


# General Management Concepts

## Certificates and Certificate Requests

This handles several types of certificate requests

1. Upload an existing Certificate Request and Certificate for tracking
2. Have the built-in ACME-v2 client generate a Certificate Request and handle the challeges (Acme-Automated)
3. Use an external tool to generate the certificate request, use PeterSSLers via HTML/API to manage the challenges (Acme-Flow)

## Input

1. An admin dashboard allows you to upload certificates (in a triplet of Cert, Signing Key, CA-Chain)
2. An admin dashboard allows you to initiate LetsEncrypt certificate signing. Upload a list of domains, your LetsEncrypt account key, and private key used for signing/serving, and the system will generate the CSR and perform all the verifications.
3. A public interface allows you to proxypass the acme-challenges that LetsEncrypt issues for manual verification. (ie, run this behind Nginx)
4. You can run the 'webserver' on a private IP, and `curl` data into it via the commandline or miscellaneous scripts

## Output

1. All the keys & certs are viewable in a wonderfully connected RDMBS browser.
2. Any keys/certs/chains can be queried in PEM & DER formats.
3. All the certificates are checked to track their validity dates, so you can search and re-issue
4. This can "prime" a Redis cache with SSL Cert info in several formats.  A Lua script for OpenResty is included that enables dynamic SSL certs.

## Management

* Everything is in the RDBMS and de-duped.
* chains are built on-the-fly.
* a growing API powers most functionality
* public and admin routes can be isolated in the app & firewall, so you can just turn this on/off as needed
* you can easily see when certificates and/or domains expire and need to be renewed
* if SQLite is your backend, you can just run this for signing and deployment; then handle everything else offline.
* "Admin" and "Public" functions are isolated from each other. By changing the config, you can run a public-only "validation" interface or enable the admin tools that broadcast certificate information.
* the Pyramid server can query Nginx locations to clear out the shared cache 


# Installation

This is pretty much ready to go for development use.  Python should install everything for you.  If it doesn't, someone screwed up.

You should create a virtualenv for this project. In this example, we will create the following directory structure:

* `certificate_admin` - core page
* `certificate_admin/peter_sslers-venv` - dedicated virtualenv
* `certificate_admin/peter_sslers` - git checkout

Here we go...

	mkdir certificate_admin
	cd certificate_admin

	virtualenv peter_sslers-venv
	source peter_sslers-venv/bin/activate

	git clone https://github.com/aptise/peter_sslers.git
	cd peter_sslers
	python setup.py develop
	initialize_peter_sslers_db example_development.ini	
	prequest example_development.ini /.well-known/admin/api/ca-certificate-probes/probe.json
	pserve --reload example_development.ini
	
Then you can visit `http://127.0.0.1:7201`

Editing the `example_development.ini` file will let you specify how the package runs.  some fields are necessary for it to work correctly, they are noted below...

`Pyramid` applications are based on `.ini` configuration files.  You can use multiple files to deploy the server differently on the same machine, or on different environments.

You can run this on SQLite or switch to Posgtresql by adjusting the sqlalchemy url

If you run via sqlalchemy, you'll need to setup the database BEFORE running `initialize_peter_sslers_db`

roughly, that entails...

	$ psql -Upostgres
	psql> create user ssl_minnow with password '{PASSWORD}';
	psql> create database ssl_minnow with owner ssl_minnow ;

Some tools are provided to automatically import existing certificates and chains (see below).

It is recommended to open up a new terminal and do the following commands

	cd certificate_admin
	source peter_sslers-venv/bin/activate
	cd peter_sslers
	prequest example_development.ini /.well-known/admin/api/ca-certificate-probes/probe.json
	cd tools
	invoke import_letsencrypt_certs_archive --archive-path='/etc/letsencrypt/archive' --server-url-root='http://127.0.0.1:7201/.well-known/admin'
	invoke import_letsencrypt_accounts_all --accounts-all-path='/etc/letsencrypt/accounts' --server-url-root='http://127.0.0.1:7201/.well-known/admin'

The `prequest` command above will import the current LetsEncrypt certificates to get you started.
The first `invoke` command will import existing LetsEncrypt issued certificates
The second `invoke` command will import existing LetsEncrypt accounts


# Implementation Details

The webserver exposes the following routes/directories:

* `/.well-known/acme-challenge` - directory
* `/.well-known/public/whoami` - URL prints host
* `/.well-known/admin` - admin tool IMPORTANT - THIS EXPOSES PRIVATE KEYS ON PURPOSE


# Just a friendly reminder:

THE ADMIN TOOL SHOULD NEVER BE PUBLICLY ACCESSIBLE.
YOU SHOULD ONLY RUN IT ON A PRIVATE NETWORK

By default, the `example_production.ini` file won't even run the admin tools.  that is how serious we are about telling you to be careful!


# why/how?

Again, the purpose of this package is to enable certificate management in systems where one or more of the following apply:

* you have a lot of domains
* you have a lot of machines
* your domains resolve to more than one IP address

Imagine you want to issue a certificate for 100 domains, which could be served from any one of 5 machines (load balancers or round-robin dns) and the certificates need to be deployable to all 5 machines.

To solve this you can:

* proxy external ` /.well-known/acme-challenge/` to one or more machines running this tool (they just need to share a common datastore)
* make ` /.well-known/admin` only usable within your LAN or NEVER USABLE
* on a machine within your LAN, you can query for the latest certs for domain(s) using simple `curl` commands

In a more advanced implementation (such as what this was originally designed to manage) the certificates need to be loaded into a `Redis` server for use by an `OpenResty`/`Nginx` webserver/gateway that will dynamically handle ssl certificates.

In a simple example, OpenResty/Nginx will query `/.well-known/admin/domain/example.com/config.json` to pull the active certificate information for a domain.  In advanced versions, that certificate information will be cached into multiple levels of OpenResty/Nginx and Redis using different optimization strategies.

This package does all the annoying openssl work in terms of building chains and converting formats *You just tell it what domains you need certificates for and in which format and THERE YOU GO.*


# Deployment Concepts

![Network Map: Simple](https://raw.github.com/aptise/peter_sslers/master/docs/assets/network_map-01.png)

PeterSSlers can run as a standalone service OR proxied behind Nginx/Apache/etc

The SSLMinnow datastore is entirely separate and standalone.  It is portable.

![Network Map: Configure](https://raw.github.com/aptise/peter_sslers/master/docs/assets/network_map-02.png)

In order to make network configuration more simple, the package includes a "fake server" that includes routes for the major public and admin endpoints. This should support most integration tests. 

![Network Map: Advanced](https://raw.github.com/aptise/peter_sslers/master/docs/assets/network_map-03.png)

In an advanced setting, multiple servers proxy to multiple peter-sslers "public" instances.

The instances share a single SSLMinnow data store.

The "Admin" tool runs on the private intranet.


# Notes

## Certificate/Key Translations

Certificates and Keys are stored in the PEM format, but can be downloaded in the DER format if needed.

There are several ways to download each file. Different file suffix will change the format and headers.

Peter shows you buttons for available formats on each page.

### CA Certificate

	could be `cert` or `chain`

	cert.pem 		PEM		application/x-pem-file
	cert.pem.txt	PEM		text/plain
	cert.cer 		DER		application/pkix-cert
	cert.der 		DER		application/x-x509-ca-cert
	cert.crt 		DER		application/x-x509-ca-cert

### Signed Certificate

	cert.pem 		PEM		application/x-pem-file
	cert.pem.txt	PEM		text/plain
	cert.crt 		DER		application/x-x509-server-cert

### Certificate Request

	csr.pem 		PEM		application/x-pem-file
	csr.pem.txt		PEM		text/plain
	csr.csr 		PEM		application/pkcs10

### Account/Domain Keys

	key.pem 		PEM		application/x-pem-file
	key.pem.txt		PEM		text/plain
	key.key 		DER		application/pkcs8

### Account/Domain Keys

	key.pem 		PEM		application/x-pem-file
	key.pem.txt		PEM		text/plain
	key.key 		DER		application/pkcs8


# Configuration options

Your `environment.ini` exposes a few configuration options.

These are documented at-length on the in-app settings page.

* `openssl_path` - the full path to your openssl binary (default `openssl`)
* `openssl_path_conf` - the full path to your openssl binary (default `/etc/ssl/openssl.cnf`)

* `certificate_authority` - the LetsEncrypt certificate authority. by default we use their staging URL. you will have to manually put in the real URL as defined on their docs.  you can also use the string "pebble" or "custom" to enable local testing.
* `certificate_authority_agreement` - the LetsEncrypt agreement URL used when creating new accounts.  Everything will probably fail if you don't include this argument.
* `certificate_authority_endpoint` - acmev1; if `certificate_authority=custom` or `certificate_authority=pebble`, you must supply a url for the endpoint
* `certificate_authority_directory` - acmev2; if `certificate_authority=custom` or `certificate_authority=pebble`, you must supply a url for the directory endpoint

* `enable_views_public` - boolean, should we enable the public views?
* `enable_views_admin` - boolean, should we enable the admin views?
* `enable_acme_flow` - boolean, should we enable the acme-flow tool?

* `redis.url` - URL of Redis (includes port)
* `redis.prime_style` - MUST be "1" or "2"; see Redis Prime section below.
* `redis.timeout.cacert` - INT seconds (default None)
* `redis.timeout.cert` - INT seconds (default None)
* `redis.timeout.pkey` - INT seconds (default None)
* `redis.timeout.domain` - INT seconds (default None)

* `nginx.servers_pool` - comma(,) separated list of servers with an expiry route; see Redis Prime section below
* `nginx.userpass` - http authhentication (username:password) which will be provided to each server in `nginx.servers_pool`
* `nginx.reset_path` - defaults to `/.peter_sslers/nginx/shared_cache/expire`
* `nginx.status_path` - defaults to `/.peter_sslers/nginx/shared_cache/status`
* `requests.disable_ssl_warning` - will disable the ssl warnings from the requests library

* `admin_server` (optional) defaults to `HTTP_HOST`
* `admin_prefix` (optional) prefix for the admin tool.  defaults to `/.well-known/admin`
* `admin_url` (optional) used for display in instructions. if omitted, scheme+server+prefix will be used

If you have a custom openssl install, you probably want these settings

	openssl_path = /opt/openssl/bin/openssl
	openssl_path_conf = /usr/local/ssl/openssl.cnf

These options are used by the server AND by the test suite.

# Tools

## `invoke` Script

there is an `invoke` script in the `tools` directory that can be used to automate certain tasks.

right now the invoke script offers:

* `import_letsencrypt_certs_archive` given a directory of your local LetsEncrypt archive (which has versioned certs), it will import them all into a server of your choice.
* `import_letsencrypt_certs_live` given a directory of your local LetsEncrypt install, it will import the active onesinto a server of your choice.
* `import_letsencrypt_cert_version` given a specific directory of your LetsEncrypt archive, it will import specific items
* `import_letsencrypt_cert_plain` given a directory of an unversioned cert (like a particular directory within the "live" certs), will import it.

* `import_letsencrypt_account` import a specific letsencrypt account
* `import_letsencrypt_accounts_server` import all accounts for a letsencrypt server (i.e. v1, v1-staging)
* `import_letsencrypt_accounts_all` import all accounts for all letsencrypt servers


## Commandline Interface

You can interact with this project via a commandline interface in several ways.

* run a webserver instance and query JSON urls or use a browser like lynx
* run explicit routes via `prequest`. this allows you to do admin tasks without spinnig up a server


## OpenResty/Nginx Lua integration

The OpenResty/Nginx implementation was migrated to it's own project, handled by `opm` distribution

https://github.com/aptise/peter_sslers-lua-resty

	opm get peter_sslers-lua-resty


## prequest

You can use Pyramid's `prequest` syntax to spin up a URL and get or post data

`$VENV/bin/prequest example_development.ini /.well-known/admin/api/ca-certificate-probes/probe.json`
`$VENV/bin/prequest example_development.ini /.well-known/admin/api/redis/prime.json`


## Routes Designed for JSON Automation


### `/.well-known/admin/api/ca-certificate-probes/probe.json`

Probes known URLs of LetsEncrypt keys and saves them with the correct role information.

If the keys were previously discovered during a signing process, it will decorate the existing records with the role data.

### `/.well-known/admin/api/deactivate-expired.json`

Deactivates expired certs

### `/.well-known/admin/api/redis/prime.json`

Primes a Redis cache with domain data.

### `/.well-known/admin/api/update-recents.json`

Updates domain records to list the most recent certificate for the domain


## Routes with JSON support

several routes have support for JSON requests via a `.json` suffix.

these are usually documented on the html version

### `/.well-known/admin/certificate/upload.json`

This can be used used to directly import certs issued by LetsEncrypt

	curl --form "private_key_file=@privkey1.pem" --form "certificate_file=@cert1.pem" --form "chain_file=@chain1.pem" http://127.0.0.1:7201/.well-known/admin/certificate/upload.json

	curl --form "private_key_file=@privkey2.pem" --form "certificate_file=@cert2.pem" --form "chain_file=@chain2.pem" http://127.0.0.1:7201/.well-known/admin/certificate/upload.json
	
Note that the url is not `/upload` like the html form but `/upload.json`

Both URLS accept the same form data, but `/upload.json` returns json data that is probably more readable from the commandline

Errors will appear in JSON if encountered.

if data is not POSTed to the form, instructions are returned in the json.

There is even an `invoke` script to automate these imports:

	invoke import_letsencrypt_certs_archive --archive-path='/path/to/archive' --server-url-root='http://127.0.0.1:7201/.well-known/admin'
	
    invoke import_letsencrypt_cert_version --domain-certs-path="/path/to/ssl/archive/example.com" --certificate-version=3 --server-url-root="http://127.0.0.1:7201/.well-known/admin"

	invoke import_letsencrypt_certs_live --live-path='/etc/letsencrypt/live' --server-url-root='http://127.0.0.1:7201/.well-known/admin'

	invoke import_letsencrypt_cert_plain --cert-path='/etc/letsencrypt/live/example.com' --server-url-root='http://127.0.0.1:7201/.well-known/admin'


### `/.well-known/admin/ca-certificate/upload.json`

Upload a new LetsEncrypt certificate.

`uplaod_bundle` is preferred as it provides better tracking.


### `/.well-known/admin/ca-certificate/upload-bundle.json`

Upload a new LetsEncrypt certificate with a known role.


### `/.well-known/admin/domain/{DOMAIN|ID}/config.json` Domain Data

`{DOMAIN|ID}` can be the internal numeric id or the domain name.

will return a JSON document:

    {"domain": {"id": "1",
                "domain_name": "a",
                },
     "server_certificate__latest_single": null,
     "server_certificate__latest_multi": {"id": "1",
                                  "private_key": {"id": "1",
                                                  "pem": "a",
                                                  },
                                  "certificate": {"id": "1",
                                                  "pem": "a",
                                                  },
                                  "chain": {"id": "1",
                                            "pem": "a",
                                            },
                                  "fullchain": {"id": "1",
                                                "pem": "a",
                                                },
                                  }
     }

If you pass in the querystring '?idonly=1', the PEMs will not be returned.

Notice that the numeric ids are returned as strings. This is by design.

If you pass in the querystring '?openresty=1' to identify the request as coming from OpenResty (as an api request), this will function as a write-through cache for Redis and load the domain's info into Redis (if Redis is configured).

This is the route use by the OpenResty Lua script to query domain data.


### `/.well-known/admin/certificate/{ID}/config.json` Certificate Data

The certificate JSON payload is what is nested in the DOMAIN payload

    {"id": "1",
     "private_key": {"id": "1",
                     "pem": "a",
                     },
     "certificate": {"id": "1",
                     "pem": "a",
                     },
     "chain": {"id": "1",
               "pem": "a",
               },
     "fullchain": {"id": "1",
                   "pem": "a",
                   },
     }

notice that the numeric ids are returned as strings. this is by design.

Need to get the cert data directly? NO SWEAT. Peter transforms this for you on the server, and sends it to you with the appropriate headers.

* /.well-known/admin/certificate/{ID}/cert.crt
* /.well-known/admin/certificate/{ID}/cert.pem
* /.well-known/admin/certificate/{ID}/cert.pem.txt
* /.well-known/admin/certificate/{ID}/chain.cer
* /.well-known/admin/certificate/{ID}/chain.crt
* /.well-known/admin/certificate/{ID}/chain.der
* /.well-known/admin/certificate/{ID}/chain.pem
* /.well-known/admin/certificate/{ID}/chain.pem.txt
* /.well-known/admin/certificate/{ID}/fullchain.pem
* /.well-known/admin/certificate/{ID}/fullchain.pem.txt
* /.well-known/admin/certificate/{ID}/privkey.key
* /.well-known/admin/certificate/{ID}/privkey.pem
* /.well-known/admin/certificate/{ID}/privkey.pem.txt


# Workflow Concepts

## Object Attributes

### Domain

#### `is_active`

If a domain is "active", then it is actively managed and should be included in certificate renewals or generating Nginx configuration.

### Certificate

#### `is_auto_renew`

Set to `True` by default.  If `True`, this certificate will be auto-renewed by the renewal queue.  If `False`, renewals must be manual.

#### `is_active`

If a certificate is "active" (`True` by default) then it is actively managed and should be included in generating Nginx configuration.

#### `is_deactivated` and `is_revoked`

If a certificate is not "active", only one of these will be `True`.  If an inactive certificate was deactivated, then it can be activated and this flag will reverse.  If the certificate was revoked, it is permanent and should not be re-activated.

## Domain Queue

The domain queue, `/admin/queue-domains`, is designed to allow for domains to be "queued in" for later batch processing.

If a domain is added to the queue, the following logic takes place:

* if the domain is already managed, but is not `active`, activate it.
* if the domain is not managed and not in the queue, add it to the queue.
* in all other cases, ignore the request.  the domain is either actively managed or queued to be so.


## Renewal Queue

* `update` will calculate which certificates need to be renewed
* `process` will do the actual renewal

Certificates end up in the renewal queue through the `update` command or being individually queued.

Certificates can also have a "custom renewal".

To process the queue:

To deal with timeouts and various issues, queue processing only works on one queue item at a time.

There are simple ways to process the entire queue though:

* Visit the renewal page and choose HTML processing. An item will be popped off the queue.  Refresh tags are used to continue processing until finished.
* Use the API endpoint. Inspect results and continue processing as needed


# FAQ

## Does this reformat certs?

Yes. PEM certs are reformatted to have a single trailing newline (via stripping then padding the input). This seems to be one of the more common standards people have for saving certs. Otherwise certs are left as-is.


## Is there a fast way to import existing certs?

Yes. Use `curl` on the commandline. see the TOOLS section for an `invoke` script that can automate many certificates from the Letsencrypt Store.


## What happens if multiple certs are available for a domain ?

Multiple Domains on a cert make this part of management epically & especially annoying.

The current solution:

* there is a an API endpoint to cache the most-recent "multi" and "single" cert for every domain onto the domain's record (update-recents)
* certificates *will not* be deactivated if they are the most-recent "multi" or "single" cert for any one domain.

This means that a cert will stay active so long as any one domain has not yet-replaced it.

When querying for a domain's cert, the system will currently send the most recent cert. a future feature might allow for this to be customized, and show the most widely usable cert.


## How does this handle LetsEncrypt accounts keys?

Account keys from the letsencrypt client are reformatted into PEM-encoded RSA keys. The data from the various json files are archived into the database for use later.  The account data is searched for the actual environment it is registered with, and that becomes part of the account record.


## Why use openssl directly? / does this work on windows?

It was much easier to peg this to `openssl` in a linux environment for now; which rules out windows.

In the future this could all be done with Python's crypto library. However openssl is fast and this was primarily designed for dealing with linux environments. sorry.

If someone wants to make a PR to make this fully Python based... ok!


## Where does the various data come from?

When imported, certificates are read into "text" form and parsed for data.

When generated via the acme protocol, certificate data is provided in the headers.

Useful fields are duplicated from the certificate into SQL to allow for better searching. Certificates are not changed in any way (aside from whitespace cleanup).


# Misc tips

So far this has been tested behind a couple of load balancers that use round-robin dns. They were both in the same physical network.

* Nginx is on port 80. everything in the `/.well-known directory` is proxied to an internal machine *which is not guaranteed to be up*
* this service is only spun up when certificate management is needed
* `/.well-known/admin` is not on the public internet

For testing certificates, these 2 commands can be useful:

reprime Redis cache

	$ prequest example_development.ini /.well-known/admin/api/redis/prime.json

clear out Nginx cache

    curl -k -f https://127.0.0.1/.peter_sslers/nginx/shared_cache/expire/all

the `-k` will keep the cert from verifying, the `-f` wont blow up from errors

# Redis support

There are several `.ini` config options for Redis support, they are listed above.

## Redis priming style

currently only `redis.prime_style = 1` and `redis.prime_style = 2` are supported.

### prime_style = 1

This prime style will store data into Redis in the following format:

* `d:{DOMAIN_NAME}` a 3 element hash for ServerCertificate (c), PrivateKey (p), CACertificate (i). note it has a leading colon.
* `c{ID}` the ServerCertificate in PEM format; (c)ert
* `p{ID}` the PrivateKey in PEM format; (p)rivate
* `i{ID}` the CACertificate in PEM format; (i)ntermediate cert

The Redis datastore might look something like this:

	r['d:foo.example.com'] = {'c': '1', 'p': '1', 'i' :'99'}  # certid, pkeyid, chainid
	r['d:foo2.example.com'] = {'c': '2', 'p': '1', 'i' :'99'}  # certid, pkeyid, chainid
	r['c1'] = CERT.PEM  # (c)ert
	r['c2'] = CERT.PEM
	r['p2'] = PKEY.PEM  # (p)rivate
	r['i99'] = CACERT.PEM  # (i)ntermediate cert
	
to assemble the data for `foo.example.com`:

* (c, p, i) = r.hmget('d:foo.example.com', 'c', 'p', 'i')
** returns {'c': '1', 'p': '1', 'i': '99'}
* cert = r.get('c1')
* pkey = r.get('p1')
* chain = r.get('i99')
* fullchain = cert + "\n" + chain

### prime_style = 2

This prime style will store data into Redis in the following format:

* `{DOMAIN_NAME}` a 2 element hash for FullChain [ServerCertificate+CACertificate] (f), PrivateKey (p)

The Redis datastore might look something like this:

	r['foo.example.com'] = {'f': 'FullChain', 'p': 'PrivateKey'}
	r['foo2.example.com'] = {'f': 'FullChain', 'p': 'PrivateKey'}


# Tests

To keep things simple, tests are run using unittest.

    python setup.py test

There are a few environment variables you can set:

	# run tests that hit Nginx for cache clearing
	export SSL_RUN_NGINX_TESTS=True

	# run tests that hit Redis for cache priming
	export SSL_RUN_REDIS_TESTS=True

	# run tests that hit the LetsEncryptAPI
	export SSL_RUN_LETSENCRYPT_API_TESTS=True

	# Set TRUE if you expect the LE API verificaiton to fail
	# this is desired right now, because it's rather complicated to set up a -
	# - test suite that responds to public requests
	export SSL_LETSENCRYPT_API_VALIDATES=True

Tests are done on a SQLite database as specified in `test.ini` AND WILL REQUIRE CUSTOMIZATION FOR YOUR OPENSSL location

The `test.ini` should also reflect the openssl for your distribution. YOU PROBABLY HAVE TO EDIT THIS.

`test_data/` contains the keys and certificates used for testing

You can overwrite the testdb; beware that it CAN NOT run as a memory db.  it must be a disk file due to how the tests are structured.

If running tests against the LetsEncrypt test API, there are some extra configurations to note:

* `SSL_TEST_DOMAINS` should reflect one or more domains that point to the IP address the server runs on.  this will be used for verification challenges
* `SSL_TEST_PORT` lets you specify which port the test server should bind to
* `/tools/nginx_conf/testing.conf` is an Nginx configuration file that can be used for testing.  it includes a flag check so you can just touch/remove a file to alter how Nginx proxies.


Gotchas
-------

1. This requires a relatively new version of openssl to handle multiple-domain certificates.
2. When using SQLite, two databases/database files are required. one is dedicated to handling the logging.  This is because of how SQLite locks the database file during certain operations.  A future version of this library will not use the pyramid_tm transaction manager and avoid this scenario.




ToDo
----

See `TODO.txt`


Getting Started
---------------

- cd <directory containing this file>

- $VENV/bin/python setup.py develop

- $VENV/bin/initialize_peter_sslers_db example_development.ini

- vi example_development.ini

- $VENV/bin/pserve example_development.ini


Import Letsencrypt Data?
-------------------------

after running the server, in another window...

- $VENV/bin/pip install invoke

- cd tools

- $VENV/bin/invoke import_letsencrypt_certs_archive --archive-path='/etc/letsencrypt/archive' --server-url-root='http://127.0.0.1:7201/.well-known/admin'


There is also a button under "operations" to probe LetsEncrypt's public website and update your certs with data.


How to check if it's working?
-----------------------------

The Lua script for SSL certificate handling makes a handful of DEBUG and NOTICE calls during certain actions. Nginx typically ignores DEBUG unless you build enable it at configuration/build time.

After querying the server, you can check the Redis server directly to see if keys are being set.  Assuming Redis is configured to use 127.0.0.1:6379:9

	workstation username$ redis-cli
	127.0.0.1:6379> select 9
	OK
	127.0.0.1:6379[9]> keys *
	
This should then show a bunch of keys.  If not, you have a problem.

You can also query nginx directly for status. Please note, the status route is configurable:

	https://example.com/.peter_sslers/nginx/shared_cache/status

The payload might look like:

	{
		"servers_status": {
			"errors": [],
			"success": [
				"http://127.0.0.1"
			],
			"servers": {
				"http://127.0.0.1": {
					"note": "This is a max(1024) listening of keys in the ngx.shared.DICT `cert_cache`. This does not show the worker's own LRU cache, or Redis.",
					"keys": {
						"valid": [
							"example.com"
						],
						"invalid": [
							"127.0.0.1"
						]
					},
					"config": {
						"expiries": {
							"resty.lrucache": 15,
							"ngx.shared.cert_cache": 45
						},
						"maxitems": {
							"resty.lrucache": 200
						}
					},
					"result": "success"
				}
			}
		},
		"result": "success"
	}

If you start to see valid/invalid keys disappear it is often because the `expiries` or `maxitems` have removed them from the cache.


What does it look like?
-----------------------

PeterSSLers was designed to be used on terminals, so it looks great on Lynx...

![Admin Index - Lynx](https://raw.github.com/aptise/peter_sslers/master/docs/images/lynx_01-admin_index.png)
![Admin Index - Lynx](https://raw.github.com/aptise/peter_sslers/master/docs/images/lynx_02-api_docs.png)

And most endpoints over JSON versions, so you can process everything that way

But... This project uses bootstrap, so it looks fine on browsers!

![Admin Index](https://raw.github.com/aptise/peter_sslers/master/docs/images/01-admin_index.png)
![CSR: Automate 'manual': Enter Domains](https://raw.github.com/aptise/peter_sslers/master/docs/images/02-enter_domains.png)
![CSR: Automate 'manual': Enter Challenges](https://raw.github.com/aptise/peter_sslers/master/docs/images/03-enter_challenge.png)
![CSR: Check Verification Status](https://raw.github.com/aptise/peter_sslers/master/docs/images/04-view_status.png)
![CSR: New FULL](https://raw.github.com/aptise/peter_sslers/master/docs/images/09-new_csr.png)
![Operations Log](https://raw.github.com/aptise/peter_sslers/master/docs/images/05-operations_log.png)
![List: Authority Certificates](https://raw.github.com/aptise/peter_sslers/master/docs/images/06-ca_certificates.png)
![Focus: Authority Certificate](https://raw.github.com/aptise/peter_sslers/master/docs/images/07-ca_certificates_focus.png)
![Upload Existing Certificates](https://raw.github.com/aptise/peter_sslers/master/docs/images/10-upload_cert.png)
![List Certificates](https://raw.github.com/aptise/peter_sslers/master/docs/images/11-certificates_list.png)
![List Domains](https://raw.github.com/aptise/peter_sslers/master/docs/images/12-domains_list.png)
