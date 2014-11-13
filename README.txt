About
=====
CKAN extension implementing ODN Internal catalog funkcionality 

Until now added features:
* Adds tab 'Pipelines' to dataset management
* Uses ODN/UV rest api

Installation
============

pip install -e git+https://github.com/OpenDataNode/InternalCatalog.git

(Optional): activate ckan virtualenv

Requires installation of:
* ckancommons:
cd InternalCatalog/ckancommons
python setup.py install

* internal catalog extenstion:
cd InternalCatalog/ckanext-internal-catalog
python setup.py install

Add extension to ckan config: /etc/ckan/default/production.ini
ckan.plugins = internalcatalog

to [app:main] add:
internal.catalog.uv.url = http://url_to_uv.com:8080

DB init
=======
After installing plugin and restarting apache server start db initialization:
paster --plugin=ckanext-internal-catalog internal-catalog-cmd initdb --config=/etc/ckan/default/production.ini

There should be output like this:
Starting db initialization
creating pipelines table				/ Or if it was already intialized:
pipelines table created successfully	/ pipelines table already exists
End of db initialization

Uninstall
=========
Before removing extension start:
paster --plugin=ckanext-internal-catalog internal-catalog-cmd uninstall --config=/etc/ckan/default/production.ini

This will drop tables created in DB init script.
Now you can remove plugin string from: /etc/ckan/default/production.ini
And remove from python installed extension egg.
