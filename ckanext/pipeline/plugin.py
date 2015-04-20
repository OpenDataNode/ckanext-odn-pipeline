'''
Created on 5.11.2014

@author: mvi
'''

import socket

import pylons.config as config

import routes.mapper
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h
import logging

from ckan.common import _, c
from ckanext.pipeline.uv_helper import UVRestAPIWrapper
from ckanext.model.pipelines import Pipelines
import urllib2
from dateutil.parser import parse

GET = dict(method=['GET'])
POST = dict(method=['POST'])
log = logging.getLogger('ckanext')


STATUSES = {
    # Next execution
    "QUEUED": "Queued",
    "RUNNING": "Running",
    "CANCELLING": "Running",
    # Last execution
    "CANCELLED": "Cancelled",
    "FAILED": "Failed",
    "FINISHED_SUCCESS": "OK",
    "FINISHED_WARNING": "Warning",
    # empty
    None: None,
    "": None
}

def get_url_without_slash_at_the_end(url):
    if url and url.endswith("/"):
        return url[:-1]
    else:
        return url

uv_url = get_url_without_slash_at_the_end(config.get('odn.uv.url', None))
uv_api_url = get_url_without_slash_at_the_end(config.get('odn.uv.api.url', None))
uv_api_auth = '{0}:{1}'.format(config.get('odn.uv.api.auth.username', ''), config.get('odn.uv.api.auth.password', '')) 
pipeline_allow_create = toolkit.asbool(config.get('odn.uv.pipeline.allow.create', True))


def allows_create_pipe():
    return pipeline_allow_create

# Our custom template helper function.
def get_all_pipelines():
    assert uv_api_url
    try:
        if c.pkg.owner_org:
            org_id = c.pkg.owner_org
        else:
            # raise error
            err_msg = _('Error: Organization is not set for dataset {dataset_name}').format(dataset_name=c.pkg.name)
            log.error(err_msg)
            h.flash_error(err_msg)
            return []            
        
        uv_api = UVRestAPIWrapper(uv_api_url, uv_api_auth)
        pipes = uv_api.get_pipelines(org=org_id)
        return pipes
    except Exception, e:
        h.flash_error(_("Couldn't get pipelines, probably UnifiedViews is not responding."))
        log.exception(e)
        return None
    except socket.timeout, e:
        h.flash_error(_("Connecting to UnifiedViews timed out."))
        log.exception(e)
        return None

def get_pipeline(pipe_id):
    assert uv_api_url
    try:
        uv_api = UVRestAPIWrapper(uv_api_url, uv_api_auth)
        pipe = uv_api.get_pipeline_by_id(pipe_id)
        return pipe, None
    except urllib2.HTTPError, e:
        error_msg =_("Couldn't get pipeline with id = {pipe_id}: {error}").format(pipe_id=pipe_id, error=e)
        return None, error_msg
    except socket.timeout, e:
        error_msg = _("Connecting to UnifiedViews timed out.")
        return None, error_msg
 
def get_pipelines_not_assigned():
    pipes = get_all_pipelines()
    
    if not pipes:
        return []
    
    pipelines_assigned = Pipelines.get_all()
    
    # remove already assigned pipelines
    pipes_assigned = []
    for pipe in pipelines_assigned:
        pipes_assigned.append(pipe.pipeline_id)
        
    unassigned = []
    for pipe in pipes:
        if not pipe['id'] in pipes_assigned:
            unassigned.append(pipe)
    
    return unassigned


def synchonize_name(actual_pipe, pipes):
    """Updates name in the pipelines table
    according to the name it get from uv rest api call
    """
    old_name = pipes.name
    pipes.name = actual_pipe['name']
    pipes.add() # updates
    pipes.commit()
    log.info('Synchronized pipeline name: {old_name} -> {new_name}'\
             .format(old_name=old_name, new_name=pipes.name))


def get_dataset_pipelines(package_id):
    assert package_id
    dataset_pipes = Pipelines.by_dataset_id(package_id)
    
    val = []
    try:
        # UV connection is OK, we can get pipe info from UV
        for pipes in dataset_pipes:
            pipe, err_msg = get_pipeline(pipes.pipeline_id)
            
            # name synchronization
            if pipe and pipes.name != pipe['name']:
                synchonize_name(pipe, pipes)
                
            if pipe:
                add_last_exec_info(pipes.pipeline_id, pipe)                    
                add_next_exec_info(pipes.pipeline_id, pipe)
            
            if pipe:
                val.append(pipe)
            else:
                val.append({u'id': pipes.pipeline_id, u'name':pipes.name, u'error': err_msg})
    except urllib2.URLError:
        h.flash_error(_("Couldn't connect to UnifiedViews server."))
        
        # get info only from DB
        for pipes in dataset_pipes:
            pipe = {u'id': pipes.pipeline_id, u'name':pipes.name}
            val.append(pipe) 
        
    return val
        

def add_last_exec_info(pipe_id, pipe):
    assert uv_url
    assert uv_api_url
    assert pipe_id
    assert pipe
    
    error_msg = None
    try:
        uv_api = UVRestAPIWrapper(uv_api_url, uv_api_auth)
        last_exec = uv_api.get_last_finished_execution(pipe_id)
        
        if not last_exec:
            return
        
        # adding it to pipe
        pipe['last_exec'] = format_date(last_exec['start'])
        pipe['last_exec_status'] = STATUSES[last_exec['status']]
        pipe['last_exec_link'] = '{0}/#!ExecutionList/exec={1}'\
            .format(uv_url, last_exec['id'])
    except urllib2.HTTPError, e:
        error_msg =_("Couldn't get pipeline last execution information for pipeline id = {pipe_id}: {error}")\
                    .format(pipe_id=pipe_id, error=e)
    except socket.timeout, e:
        error_msg = _("Connecting to UnifiedViews timed out.")
    
    if error_msg:
        h.flash_error(error_msg)


def add_next_exec_info(pipe_id, pipe):
    assert uv_url
    assert uv_api_url
    assert pipe_id
    assert pipe
    
    error_msg = None
    try:
        uv_api = UVRestAPIWrapper(uv_api_url, uv_api_auth)
        schedule_id, next_exec, next_exec_status = uv_api.get_next_execution_info(pipe_id)
        
        pipe['next_exec'] = format_date(next_exec)
        pipe['next_exec_status'] = STATUSES[next_exec_status]
        pipe['next_exec_sched_url'] = '{0}/#!Scheduler'.format(uv_url) # TODO link to schedule
        return
    except urllib2.HTTPError, e:
        error_msg =_("Couldn't get pipeline next execution information for pipeline id = {pipe_id}: {error}")\
                    .format(pipe_id=pipe_id, error=e)
    except socket.timeout, e:
        error_msg = _("Connecting to UnifiedViews timed out.")

    if error_msg:
        h.flash_error(error_msg)


def get_available_pipes_options():
    pipes = get_pipelines_not_assigned()
    return get_options_discriptions_for(pipes)


def get_all_pipes_options():
    pipes = get_all_pipelines()
    return get_options_discriptions_for(pipes)

    
def get_options_discriptions_for(pipes):
    options = []
    descriptions = []
    if pipes:
        for pipe in pipes:
            options.append({'value': pipe['id'], 'text':pipe['name']})
            descriptions.append({'id':pipe['id'], 'description':pipe[u'description']})
    return options, descriptions


def format_date(datetime_str):
    """
    Formats datetime string:
    2012-07-24T23:14:23.516Z -> 24. Jul 2012, 23:14
    """
    if not datetime_str:
        return None
    # TODO timezone
    date = parse(datetime_str)
    return date.strftime("%d. %b %Y, %H:%M")


class PipelinePlugin(plugins.SingletonPlugin):
    
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IRoutes)
    
    def update_config(self, config):
        # see IConfigurer plugin interface
        
        # Tells CKAN to use the template and
        # snippet files
        toolkit.add_template_directory(config, 'templates')
        
        # Tells CKAN where to find JS and CSS files
        toolkit.add_resource('fanstatic', 'ic_theme')
        
            
    # Tell CKAN what custom template helper functions this plugin provides,
    # see the ITemplateHelpers plugin interface.
    def get_helpers(self):
        return {'get_pipeline_available': get_pipelines_not_assigned,
                'get_dataset_pipelines': get_dataset_pipelines,
                'allows_create_pipe': allows_create_pipe
                }
    
    
    def before_map(self, route_map):
        # see IRoutes plugin interface
        with routes.mapper.SubMapper(route_map,
                controller='ckanext.controllers.pipeline:ICController') as m:
            
            m.connect('dataset_pipelines', '/dataset/{id}/pipelines', action='show', conditions=GET)
            m.connect('/dataset/{id}/pipelines/choose_pipeline', action='choose_pipeline')
            m.connect('pipe_assign', '/dataset/{id}/pipelines', action='assign', conditions=POST)
            m.connect('/dataset/{id}/pipelines/remove_pipeline/{pipeline_id}', action='remove_pipe')
            m.connect('/dataset/{id}/pipelines/choose_action', action='choose_action')
            m.connect('/dataset/{id}/pipelines/create_new', action='create_pipe_manually', conditions=POST)
            m.connect('/dataset/{id}/pipelines/execute/{pipeline_id}', action='execute_now')
            m.connect('pipe_to_copy', '/dataset/{id}/pipelines/choose_pipe_to_copy',
                       action='choose_pipe_to_copy', conditions=POST)
            m.connect('name_and_descr', '/dataset/{id}/pipelines/name_and_descr',
                       action='set_name_descr', conditions=POST)
            m.connect('/dataset/{id}/pipelines/response', action='create_copy')
            
        return route_map
    
    def after_map(self, route_map):
        # see IRoutes plugin interface
        return route_map
    

        
