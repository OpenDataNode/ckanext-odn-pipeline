'''
Created on 9.2.2015

@author: mvi
'''

from ckan.common import _, c
import ckan.logic as logic
import ckan.plugins as plugins
from ckanext.model.pipelines import Pipelines

import urllib
import logging
import pylons.config as config

from ckan.model.user import User
import json

NotFound = logic.NotFound
get_action = logic.get_action

rdf_uri_template = config.get('odn.storage.rdf.uri.template', '')
token_from_cfg = config.get("ckan.auth.internal_api.token", None)

log = logging.getLogger('ckanext')


def check_and_bust(key, dict):
    if key not in dict or not dict[key]:
        raise NotFound("Key '{0}' was not found or has no value set.".format(key))

# ============= AUTHENTIFICATION =============

class MyUser(User):
    
    @classmethod
    def by_id(cls, id):
        import ckan.model.meta as meta
        obj = meta.Session.query(User).autoflush(False)
        return obj.filter_by(id=id).first()

def change_auth_user(context, user_id):
    if not user_id:
        return
    
    context['user'] = None
    context['auth_user_obj'] = None
    c.user = None
    c.userobj = None

    user = MyUser.by_id(user_id)
    if user:
        log.debug('internal_api: Setting user to {username}'.format(username=user.name))
        context['user'] = user.name
        context['auth_user_obj'] = user
        c.user = user.name
        c.userobj = user

def internal_api_auth(context, data_dict=None):
    check_and_bust('token', data_dict)

    token = data_dict['token']
    
    if not token or token != token_from_cfg:
        return {'success': False, 'msg': _('internal api: Authentication failed.')}
    
    return {'success': True }

# ============= RESOURCE CREATE logic =============

# data_dict = {
#     'action':'resource_create',
#     'pipeline_id': 11,                     (optional)
#     'user_id': 'CKAN USER ID',             (optional)
#     'token': 'token',
#     'type': 'RDF',                         (optional)
#     'value': 'specific value for type',    (optional)
#     'data': {}                             (optional)
# }

def internal_api(context, data_dict=None):
    check_and_bust('action', data_dict)
    check_and_bust('user_id', data_dict)
    
    user_id = data_dict.get('user_id', None)
    change_auth_user(context, user_id)
    
    log.debug('internal_api: action = {0}'.format(data_dict['action']))
    log.debug('internal_api: user_id = {0}'.format(user_id))
    logic.check_access('internal_api', context, data_dict)

    action = data_dict['action'] 
    data = data_dict.get('data', {})
    
    if isinstance(data, basestring):
        # if upload data is actually a string
        data = json.loads(data)
    
    # type == 'FILE'
    
    if data_dict.has_key('upload'):
        data['upload'] = data_dict['upload']
        data['url'] = ''
    
    # any type
    
    if data_dict.has_key('pipeline_id') and data_dict['pipeline_id']:
        log.debug('internal_api: pipeline_id = {0}'.format(data_dict['pipeline_id']))
        pipeline_id = data_dict['pipeline_id']
        dataset_to_pipeline = Pipelines.by_pipeline_id(pipeline_id)
        
        if dataset_to_pipeline:
            # converting pipeline_id to 'id' or 'package_id'
            if 'resource_create' == action:
                data['package_id'] = dataset_to_pipeline.package_id
            elif action in ['package_update', 'package_show']:
                data['id'] = dataset_to_pipeline.package_id
        else:
            raise NotFound('No dataset found for pipeline_id = {0}'.format(pipeline_id))
    
    # type == 'RDF'
    if data_dict.has_key('type') and data_dict['type'] == 'RDF':
        data['url'] = get_rdf_url(data_dict)
    
    return get_action(action)(context, data)

def get_rdf_url(data_dict):
    check_and_bust('value', data_dict)
    storage_id = data_dict['value']
    
    # escaping 'wrong' characters
    url = rdf_uri_template.replace('{storage_id}', str(storage_id))
    return urllib.quote(url, safe="%/:=&?~#+!$,;'@()*[]")

# ============= PLUGIN =============

class InternalApiPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IActions)

    def get_auth_functions(self):
        return {'internal_api': internal_api_auth}
    
    def get_actions(self):
        return {'internal_api': internal_api}