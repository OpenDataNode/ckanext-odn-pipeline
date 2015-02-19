'''
Created on 26.11.2014

@author: mvi
'''

import ckan.logic as logic
import ckan.plugins as plugins
# import ckan.new_authz as new_authz
import logging
import ckan.lib.helpers as h
import pylons.config as config
import urllib
import json

from dateutil.parser import parse

from ckanext.model.pipelines import Pipelines 
from ckan.common import _, c
from ckan.model.user import User
from ckan.logic import ValidationError

NotFound = logic.NotFound
get_action = logic.get_action

log = logging.getLogger('ckanext')

rdf_uri_template = config.get("odn.storage.rdf.uri.template", None)
file_uri_template = config.get("odn.storage.file.uri.template", None)


def get(data_dict):
    check_and_bust('pipelineId', data_dict)
   
    check_and_bust('resources', data_dict)
    
    return data_dict['pipelineId'], data_dict['resources']


def resources_auth(context, data_dict=None):
    """Authentication for resources function
    """
#     model = context['model']
#     user = context['user']
#     authorized = new_authz.is_sysadmin(user)
#     
#     return {'success' : authorized}

    return {'success' : True}


# TODO !!! REMOVE !!!
class MyUser(User):
    
    @classmethod
    def by_id(cls, id):
        import ckan.model.meta as meta
        obj = meta.Session.query(User).autoflush(False)
        return obj.filter_by(id=id).first()

# TODO !!! REMOVE !!!
def set_user(context, user_id):
    user = MyUser.by_id(user_id)
    if user:
        context['user'] = user.name


# @plugins.toolkit.side_effect_free
def resources(context, data_dict=None):
    """Resources

    :param pipelineId: id of pipeline the resource belongs to
    :type pipelineId: int
    :param resources: resources to create or update
    :type resources: list of dictionaries
    
    :rtype: list of dictionaries describing the success / failure of updating or creating the resource

    """
    
    if not rdf_uri_template or not file_uri_template:
        raise NotFound('Config properties not set. Please contact the administrator.')
    
    log.debug("data_dict = {0}".format(data_dict))
    pipeline_id, resources = get(data_dict)
    
    model = context['model']
    dataset_to_pipeline = Pipelines.by_pipeline_id(pipeline_id)
    
    if not dataset_to_pipeline:
        raise NotFound("No dataset found with pipeline {id} assigned to it.".format(id=pipeline_id))
    
    package = model.Package.get(dataset_to_pipeline.package_id)

    # TODO !!!!!!!!!!!!!!!!!! remove !!!!!!!!!!!!!!!!!!!!
    # TODO !!!!!!!!!!!!!!!!!! remove !!!!!!!!!!!!!!!!!!!!
    # TODO !!!!!!!!!!!!!!!!!! remove !!!!!!!!!!!!!!!!!!!!
    set_user(context, package.creator_user_id)
     
    if not package:
        raise NotFound("No dataset with id {0} found.".format(dataset_to_pipeline.package_id))

    log.debug("Found dataset {0}".format(package.name))
     
    package_resources = package.resources
    
    responses = []
    for resource in resources:
        success = False
        type = "CREATE"
        message = None
        name = None
        
        try:
            check_and_bust('storageId', resource)
            check_and_bust('resource', resource)
            
            storage_id = resource['storageId']
            resource = resource['resource']
            
            check_and_bust('name', resource)
            name = resource['name']
            
            package_resource = get_resource_by_name(name, package_resources)
            url = get_url(storage_id)
            
            resource['url'] = url
            if package_resource:
                # resource with the name exists -> just UPDATE
                type = "UPDATE"
                resp = resource_update(package_resource.id, resource, context)
                success = True
            else:
                # resource with the name doesn't exists -> CREATE new
                resp = resource_create(package.id, resource, context)
                success = True
        except Exception, e:
            log.exception(e)
            message = str(e)
        
        responses.append({
            u'success': success,
            u'name': name,
            u'type': type,
            u'message': message
        })
    
    return responses


def check_and_bust(key, dict):
    if key not in dict or not dict[key]:
        json_str = json.dumps(dict) # we don't want to quote
        raise NotFound("Key '{0}' was not found in: {1}".format(key, json_str))


def get_url(resource):
    check_and_bust('type', resource)
    check_and_bust('value', resource)
    
    type = resource['type']
    value = resource['value']
    
    url = ""
    if type == "RDF":
        url = h.url_for('/', locale='default', qualified=True) + rdf_uri_template

    elif type == "FILE":
        url = h.url_for('/', locale='default', qualified=True) + file_uri_template
    else:
        msg = "Wrong storageId type given '{type}', only RDF or FILE supported."
        raise ValidationError(msg.format(type=type))
    
    # escaping 'wrong' characters
    url = url.replace('{storage_id}', str(value))
    return urllib.quote(url, safe="%/:=&?~#+!$,;'@()*[]")
        

def to_timestamp_naive(datetime_str):
    datetime = parse(datetime_str)
    naive = datetime.replace(tzinfo=None) - datetime.utcoffset()
    return naive.isoformat(' ')


def resource_create(dataset_id, resource, context):
    log.debug("Creating resource dataset_id={id}, resource={res}"\
              .format(id=dataset_id, res=resource))
    resource['package_id'] = dataset_id
    return get_action('resource_create')(context, resource)


def resource_update(resource_id, res, context):
    log.debug("Updating resource id={id}, resource={res}".format(id=resource_id, res=res))
    data_dict = {'id': resource_id}
    resource = get_action('resource_show')(context, data_dict)
    resource.update(res)
    return get_action('resource_update')(context, resource)


def get_resource_by_name(name, package_resources):
    for res in package_resources:
        if res.name == name:
            return res
    return None


class ResourceUpdateAPIPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IActions)

    def get_auth_functions(self):
        return {'resources': resources_auth}
    
    def get_actions(self):
        return {'resources': resources}
