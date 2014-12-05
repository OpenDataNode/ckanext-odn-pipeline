'''
Created on 26.11.2014

@author: mvi
'''

import schema
import ckan.logic as logic
import ckan.plugins as plugins
import ckan.new_authz as new_authz


import logging
from ckanext.model.pipelines import Pipelines 
from ckan.common import _, c
from ckan.model.user import User

NotFound = logic.NotFound
get_action = logic.get_action

log = logging.getLogger('ckanext')

# TODO from cfg
url = "http://192.168.128.23/dump"


def get(data_dict):
    if 'pipelineId' not in data_dict:
        raise NotFound('pipelineId not provided.')
    
    if 'rdf' not in data_dict:
        raise NotFound('File containing resource information not provided.')
    
    return data_dict['pipelineId'], data_dict['rdf'].file


def resources_auth(context, data_dict=None):
    """Authentication for resources function
    """

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


def resources(context, data_dict=None):
    """Resources

    :param pipelineId: id of pipeline the resource belongs to
    :type pipelineId: int
    
    :rtype: list of dictionaries describing the success / failure of updating or creating the resource

    """
    log.debug("data_dict = {0}".format(data_dict))
    pipeline_id, rdf_file = get(data_dict)
    
    resources, msg = get_resources(rdf_file)
    
    if not resources:
        if msg:
            raise NotFound("No resources information found: {0}".format(msg))
        else:
            raise NotFound("No resources information found.")
        
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
        resource.pop('uri')
        name = resource['name']
        package_resource = get_resource_by_name(name, package_resources)
        
        success = False
        type = "CREATE"
        message = None
        
        try:
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


def get_resources(rdf_file):
    from ckanext.dcat.parsers import RDFParser, RDFParserException
    parser = RDFParser()
    
    # Parsing a local RDF/XML file
    
    in_out_format = 'turtle'

    try:
        parser.parse(rdf_file.read(), _format=in_out_format)
    
        for dataset in parser.datasets():
            return dataset['resources'], None
    
    except RDFParserException, e:
        log.error('Error parsing the RDF file: {0}'.format(e))
        return None, str(e)
    except Exception, e:
        log.exception(e)
        None, str(e)


def resource_create(dataset_id, resource, context):
    log.debug("Creating resource dataset_id={id}, resource={res}"\
              .format(id=dataset_id, res=resource))
#     data_dict = {'package_id': dataset_id,
#                  'name': name,
#                  'url': url}
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
