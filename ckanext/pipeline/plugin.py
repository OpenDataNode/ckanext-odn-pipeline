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

from ckan.common import _
from ckanext.pipeline.uv_helper import UVRestAPIWrapper
from ckanext.model.pipelines import Pipelines
import urllib2
from dateutil.parser import parse

GET = dict(method=['GET'])
POST = dict(method=['POST'])

uv_url = config.get('odn.uv.url', None)
uv_api_url = config.get('odn.uv.api.url', None)


# Our custom template helper function.
def get_all_pipelines():
    assert uv_api_url
    try:
        uv_api = UVRestAPIWrapper(uv_api_url)
        pipes = uv_api.get_pipelines()
        return pipes
    except Exception, e:
        h.flash_error(_("Couldn't get pipelines, probably UnifiedViews is not responding: {error}").format(error=e))
        return None
    except socket.timeout, e:
        h.flash_error(_("Connecting to UnifiedViews timed out."))
        return None

def get_pipeline(pipe_id):
    assert uv_api_url
    try:
        uv_api = UVRestAPIWrapper(uv_api_url)
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

def get_dataset_pipelines(id):
    assert id
    dataset_pipes = Pipelines.by_dataset_id(id)
    
    val = []
    try:
        # try contact UV server
        pipe, err_msg = get_pipeline(-1)
    except urllib2.URLError, e:
        h.flash_error(_("Couldn't connect to UnifiedViews server."))
        
        # get info only from DB
        for pipes in dataset_pipes:
            pipe = {u'id': pipes.pipeline_id, u'name':pipes.name}
            val.append(pipe) 
    else:
        # UV connection is OK, we can get pipe info from UV
        for pipes in dataset_pipes:
            pipe, err_msg = get_pipeline(pipes.pipeline_id)
            
            # name synchronization
            if pipes.name != pipe['name']:
                old_name = pipes.name
                pipes.name = pipe['name']
                pipes.add() # updates
                pipes.commit()
                h.flash_notice(_('Synchronized pipeline name: {old_name} -> {new_name}')\
                               .format(old_name=old_name, new_name=pipes.name))
            
            last_exec, err_msg_exec = get_last_exec_info(pipes.pipeline_id)
            
            if last_exec:
                pipe['last_exec'] = format_date(last_exec['start'])
                pipe['last_exec_status'] = last_exec['status']
                pipe['last_exec_link'] = uv_url +'/#!ExecutionList/exec={id}'\
                                        .format(id=last_exec['id'])
            
            if err_msg_exec:
                h.flash_error(err_msg_exec)
            
            if pipe:
                val.append(pipe)
            else:
                h.flash_error(err_msg)
        
    return val
        

def get_last_exec_info(pipe_id):
    assert uv_api_url
    assert pipe_id
    try:
        uv_api = UVRestAPIWrapper(uv_api_url)
        last_exec = uv_api.get_last_pipe_execution(pipe_id)
        return last_exec, None
    except urllib2.HTTPError, e:
        error_msg =_("Couldn't get pipeline execution information for pipeline id = {pipe_id}: {error}")\
                    .format(pipe_id=pipe_id, error=e)
        return None, error_msg
    except socket.timeout, e:
        error_msg = _("Connecting to UnifiedViews timed out.")
        return None, error_msg
    


def get_pipes_options():
    pipes = get_pipelines_not_assigned()
    options = []
    descriptions = []
    if pipes:
        for pipe in pipes:
            options.append({'value': pipe['id'], 'text':pipe['name']})
            descriptions.append({'id':pipe['id'], 'description':pipe[u'description']})
    return options, descriptions


def format_date(datetime_str):
    """
    Formats datetime str to:
    24. Jul 2012, 23:14
    """
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
                'get_pipes_options': get_pipes_options,
                'get_dataset_pipelines': get_dataset_pipelines}
    
    
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
            
        return route_map
    
    def after_map(self, route_map):
        # see IRoutes plugin interface
        return route_map
    

        
