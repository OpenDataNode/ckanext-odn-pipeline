About
-------

CKAN extension implementing ODN pipeline association to dataset functionality 

Until now added features:
* Adds 'pipelines' table to DB, columns: package_id, pipeline_id, name
* Adds tab 'Pipelines' to dataset management
* Associates existing pipeline with CKAN dataset
* Associates manually created pipeline with CKAN dataset
* Associates modified copy of existing pipeline with CKAN dataset
* Shows information about last and next execution
* Links to UV functionality
* Uses ODN/UV rest API
* Adds API calls for creating / updating resources from UnifiedViews (L-Catalog DPU)
* Adds API call internal_api for proxy-ing API calls

TODO
-------

Installation
-------

(Optional): activate ckan virtualenv ``` . /usr/lib/ckan/default/bin/activate ```

From the extension folder start the installation: ``` python setup.py install ```

Add extension to ckan config: /etc/ckan/default/production.ini

```
ckan.plugins = odn_pipeline odn_resource_update_api internal_api
```

* odn_pipeline - plugin for association pipeline to dataset from CKAN GUI 
* odn_resource_update_api - plugin needed for L-Catalog DPU
* internal_api - plugin to proxy API calls, needed by DPUs: L-FilesToCkan, L-RdfToCkan, L-RelationalToCkan, L-RelationalDiffToCkan

to section [app:main] add:
```ApacheConf
# pipeline
odn.uv.url = http://HOST/unifiedviews
odn.uv.api.url = http://127.0.0.1:8080/master/api/1
odn.uv.timeout = 5
# uv rest api authorization
odn.uv.api.auth.username = username
odn.uv.api.auth.password = password

# allow create pipelines from CKAN gui, default True (optional)
odn.uv.pipeline.allow.create = False

# resource update api (L-Catalog <-> IC), the URL are quoted in code
odn.storage.rdf.uri.template = http://host/sparql?query=select {?s ?p ?o} from {storage_id}
odn.storage.file.uri.template = http://host/dump/{storage_id}

# internal_api
ckan.auth.internal_api.token = my secret token
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

internal_api
-------
Functions as proxy to other CKAN API calls. Requires following properties set up in CKAN configuration file:
* ckan.auth.internal_api.token
* odn.storage.rdf.uri.template
 
Request:

* POST <host>/api/3/action/internal_api
* multipart/form-data
* parameters:
	* action - name of API call, e.g. 'resource_create'
	* pipeline_id - pipeline id used to identify the dataset the change should be applied to (optional)
	* user_id - user used for authentication (CKAN user id)
	* token - authentication token set up in CKAN conf file (ckan.auth.internal_api.token)
	* data - actual JSON data of the proxied API call (optional)
	* type - 'RDF' otherwise optional
	* value - storage id if type == 'RDF', otherwise optional

For 'package_update', 'package_show', 'resource_create' actions the pipeline_id is converted to appropriate package id. So for these
actions its not necessary to add the ids to the data parameter and will be overwritten if both are given.


Internationalization (i18n)
-------
CKAN supports internationalization through babel (```pip install babel```). This tool extracts the messages from source code and html files
and creates .pot file. Next using commands (step 2 or 3) it creates or updates .po files. The actual translation are in these .po files.

1. To extract new .pot file from sources
	```
	python setup.py extract_messages
	```
	
	This need to be done if there is no .pot file or there were some changes to messages in source code files or html files.

2. To generate .po for new localization (this example uses 'sk' localization)
	```
	python setup.py init_catalog --locale sk
	```

3. If only updating existing .po file (e.g. new messages were extracted through step 1)
	```
	python setup.py update_catalog --locale sk
	```

Licenses
-------

[GNU Affero General Public License, Version 3.0](http://www.gnu.org/licenses/agpl-3.0.html) is used for licensing of the code (see LICENSE)
