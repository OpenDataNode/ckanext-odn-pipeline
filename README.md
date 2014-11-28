About
-------

CKAN extension implementing ODN pipeline association to dataset functionality 

Until now added features:
* Adds 'pipelines' table to DB, columns: package_id, pipeline_id, name
* Adds tab 'Pipelines' to dataset management
* Associates pipline with CKAN dataset
* Uses ODN/UV rest API

TODO
-------


Installation
-------

(Optional): activate ckan virtualenv

Requires installation of:
* ckancommons:
cd ckanext-odn-ic/ckancommons
python setup.py install

* pipeline extenstion:
cd ckanext-odn-ic/ckanext-odn-pipeline
python setup.py install

Add extension to ckan config: /etc/ckan/default/production.ini
ckan.plugins = pipeline

to [app:main] add:
odn.uv.url = http://host/unifiedviews
odn.uv.api.url = http://127.0.0.1:8080/master/api/1
odn.uv.timeout = 5

DB init
-------

After installing plugin and restarting apache server start db initialization:
paster --plugin=ckanext-odn-pipeline pipeline-cmd initdb --config=/etc/ckan/default/production.ini

There should be output like this:
Starting db initialization
creating pipelines table				/ Or if it was already intialized:
pipelines table created successfully	/ pipelines table already exists
End of db initialization

Uninstall
-------

Before removing extension start:
paster --plugin=ckanext-odn-pipeline pipeline-cmd uninstall --config=/etc/ckan/default/production.ini

This will drop tables created in DB init script.
Now you can remove plugin string from: /etc/ckan/default/production.ini
And remove from python installed extension egg.

Licenses
-------

[GNU Affero General Public License, Version 3.0](http://www.gnu.org/licenses/agpl-3.0.html) is used for licensing of the code (see LICENSE)

