About
-------

CKAN extension implementing ODN pipeline association to dataset functionality 

Until now added features:
* Adds 'pipelines' table to DB, columns: package_id, pipeline_id, name
* Adds tab 'Pipelines' to dataset management
* Associates existing pipeline with CKAN dataset
* Associates manually created pipeline with CKAN dataset
* Shows information about last and next execution
* Links to UV functionality
* Uses ODN/UV rest API
* Adds rest API for creating / updating resources from UnifiedViews (L-Catalog dpu)

TODO
-------


Installation
-------

(Optional): activate ckan virtualenv ``` . /usr/lib/ckan/default/bin/activate ```

From the extension folder start the installation: ``` python setup.py install ```

Add extension to ckan config: /etc/ckan/default/production.ini

```
ckan.plugins = odn_pipeline resource-update-api
```

to section [app:main] add:
```ApacheConf
# pipeline
odn.uv.url = http://HOST/unifiedviews
odn.uv.api.url = http://127.0.0.1:8080/master/api/1
odn.uv.timeout = 5

# resource update api (L-Catalog <-> IC), the URL are quoted in code
odn.storage.rdf.uri.template = http://host/sparql?query=select {?s ?p ?o} from {storage_id}
odn.storage.file.uri.template = http://host/dump/{storage_id}
```

DB init
-------

After installing plugin and restarting apache server start db initialization:

```
paster --plugin=ckanext-odn-pipeline pipeline-cmd initdb --config=/etc/ckan/default/production.ini
```

There should be output like this:
```
Starting db initialization
creating pipelines table				/ Or if it was already intialized:
pipelines table created successfully	/ pipelines table already exists
End of db initialization
```

Uninstall
-------

Before removing extension start:

```
paster --plugin=ckanext-odn-pipeline pipeline-cmd uninstall --config=/etc/ckan/default/production.ini
```

This will drop tables created in DB init script.

Now you can remove plugin string from: ``` /etc/ckan/default/production.ini ```

Restart apache server: ``` sudo service apache2 restart ```

And remove from python installed extension egg.

Resource update API for L-Catalog
-------

This describes communication between UnifiedViews L-Catalog DPU and CKAN. This request
is sent by L-Catalog to create / update resources according the pipeline id. More than
one resource can be send.
```JSON
POST <host>/api/3/action/resources
Accept: application/json

{
	"pipelineId": 8,
	"resources": [
		{
			"storageId": {
				"type": "RDF",
				"value": "storageID"
			},
			"resource": {
				"name": "resource name",
				"description": "description of resource",
				"last_modified" : "2014-12-05 08:38:44.019000",
			}
		}
	]
}
```
All keys in this request are mandatory. The only exception to this is the resource part,
where only 'name' key is mandatory. The name key is used as resource identification. It
is used to determine if the resource should be created or updated. The resource value
corresponds to standard CKAN resource_update / resource_create api call.

storageId type: RDF / FILE

Response:
```JSON
HTTP 200 OK
Content-Type: application/json

{
	"help": "...",
	"result": [
		{
			"message": null,
            "name": "resource name",
			"success": true,
			"type": "UPDATE"
		},
		{
			"message": "Error message explaining failure just for THIS resource.",
            "name": "resource name 2",
			"success": false,
			"type": "CREATE"
		}
	],
	"success": true
}
```

Error response:
```JSON
HTTP 404 Not found
Content-Type: application/json

{
	"help": "...",
	"success": false,
	"error": {
		"message": "Not found: No dataset found with pipeline 15 assigned to it.",
		"__type": "Not Found Error"
	}
}
```

Licenses
-------

[GNU Affero General Public License, Version 3.0](http://www.gnu.org/licenses/agpl-3.0.html) is used for licensing of the code (see LICENSE)
