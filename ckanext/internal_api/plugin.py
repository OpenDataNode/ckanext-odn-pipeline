'''
Created on 9.2.2015

@author: mvi
'''

from ckan.common import _
import ckan.logic as logic
import ckan.plugins as plugins
from ckanext.model.pipelines import Pipelines

import urllib
import logging
import pylons.config as config

from ckan.model.user import User
import ast

NotFound = logic.NotFound
get_action = logic.get_action

rdf_uri_template = config.get('odn.storage.rdf.uri.template', '')

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
    context['user'] = ''
    context['auth_user_obj'] = ''
    if not user_id:
        return
    
    # TODO
#     user = User.by_name(user_id)
    user = MyUser.by_id(user_id)
    if user:
        log.debug('internal_api: Setting user to {username}'.format(username=user.name))
        context['user'] = user.name
        context['auth_user_obj'] = user


# TODO remove annotation
@plugins.toolkit.auth_allow_anonymous_access
def internal_api_auth(context, data_dict=None):
    check_and_bust('token', data_dict)

    token = data_dict['token']
    token_from_cfg = config.get("ckan.auth.internal_api.token", None)
     
    if not token or token != token_from_cfg:
        return {'success': False, 'msg': _('internal api: Authentication failed.')}
    
    return {'success': True }

# ============= RESOURCE CREATE logic =============

def get_package_editor_or_admin(package_id, context):
    '''
    :return: user id with either editor or admin role on package
    '''
    resp = get_action('roles_show')(context, {'domain_object':package_id})
    admin_id = None
    for role in resp['roles']:
        role_name = role['role']
        user_id = role['user_id']
        if role_name == 'editor':
            return user_id
        elif role_name == 'admin':
            admin_id = user_id
    return admin_id

# data_dict = {
#     'action':'resource_create',
#     'pipeline_id': 11,
#     'user_id': 'idcko',
#     'token': 'token',
#     'type': 'RDF otherwise optional',
#     'value': 'storageId if value == RDF otherwise optional',
#     'data': {}
# }

def internal_api(context, data_dict=None):
    check_and_bust('user_id', data_dict)
    user_id = data_dict['user_id']
    # TODO set user for auth
    # change_auth_user(context, user_id)
    
    log.debug('internal_api: data_dict = {0}'.format(data_dict))
    logic.check_access('internal_api', context, data_dict)
    
    change_auth_user(context, None)

    check_and_bust('action', data_dict)
    check_and_bust('data', data_dict)
    action = data_dict['action'] 
    data = data_dict['data']
    
    if isinstance(data, basestring):
        # if upload data is actually a string
        data = ast.literal_eval(data)
    
    # type == 'FILE'
    
    if data_dict.has_key('upload'):
        data['upload'] = data_dict['upload']
    
    # any type
    
    if data_dict.has_key('pipeline_id') and data_dict['pipeline_id']:
        pipeline_id = data_dict['pipeline_id']
        dataset_to_pipeline = Pipelines.by_pipeline_id(pipeline_id)
        
        if dataset_to_pipeline:
            # user with permission to edit or admin rights on dataset
            editor_id = get_package_editor_or_admin(dataset_to_pipeline.package_id, context)
            change_auth_user(context, editor_id)
        
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