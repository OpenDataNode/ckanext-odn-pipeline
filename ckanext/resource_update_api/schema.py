'''
Created on 27.11.2014

@author: mvi
'''

import ckan.lib.navl.dictization_functions as df

# from ckan.logic import ValidationError

_validate = df.validate

from ckan.lib.navl.validators import (not_empty,
                                      not_missing,
                                     )
from ckan.logic.validators import (package_id_or_name_exists,
                                   url_validator,
                                   )

logic_vals = [package_id_or_name_exists, url_validator]


def default_resource_update_schema():

    schema = {
        'pipelineId': [not_missing, not_empty, unicode],
        'rdf': [not_missing, not_empty]
    }

    return schema

def validate(data_dict):
    schema = default_resource_update_schema()
    _validate(data_dict, schema)