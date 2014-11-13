'''
Created on 5.11.2014

@author: mvi
'''

import pylons.config as config

import routes.mapper
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h


# from ckan.common import OrderedDict, _, json, request, c, g, response
from ckanext.pipeline.uv_helper import UVRestAPIWrapper
from ckanext.model.pipelines import Pipelines
import urllib2


GET = dict(method=['GET'])
POST = dict(method=['POST'])


uv_url = config.get('internal.catalog.uv.url', None)

# Our custom template helper function.
def get_all_pipelines():
    assert uv_url
    try:
        uv_api = UVRestAPIWrapper(uv_url)
        pipes = uv_api.get_pipelines()
        return pipes
    except Exception, e:
        h.flash_error("Couldn't get pipelines, probably UV is not responding: %s"\
                       % (str(e),))
        return None

def get_pipeline(pipe_id):
    assert uv_url
    try:
        uv_api = UVRestAPIWrapper(uv_url)
        pipe = uv_api.get_pipeline_by_id(pipe_id)
        return pipe, None
    except urllib2.HTTPError, e:
        error_msg ="Couldn't get pipeline with id = %s: %s" % (pipe_id, str(e),)
        return None, error_msg
 
def get_pipelines_not_assigned():
    pipes = get_all_pipelines()
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
        h.flash_error("Couldn't connect to UV server.")
        
        for pipes in dataset_pipes:
            pipe = {u'id': pipes.pipeline_id, u'name':pipes.name}
            val.append(pipe) 
    else:
        for pipes in dataset_pipes:
            pipe, err_msg = get_pipeline(pipes.pipeline_id)
            
            # name synchronization
            if pipes.name != pipe['name']:
                old_name = pipes.name
                pipes.name = pipe['name']
                pipes.add() # updates
                pipes.commit()
                h.flash_notice('Synchronized pipeline name: %s -> %s' % (old_name, pipes.name, ))
            
            if pipe:
                val.append(pipe)
            else:
                h.flash_error(err_msg)
        
    return val 
        
    

def get_pipes_options():
    pipes = get_pipelines_not_assigned()
    options = []
    descriptions = []
    if pipes:
        for pipe in pipes:
            options.append({'value': pipe['id'], 'text':pipe['name']})
            descriptions.append({'id':pipe['id'], 'description':pipe[u'description']})
    return options, descriptions


class PipelinePlugin(plugins.SingletonPlugin):
    
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IRoutes)
    
    def update_config(self, config):
        # see IConfigurer plugin interface
        # Tell CKAN to use the template files in
        # ckanext/internal_catalog/templates.
        toolkit.add_template_directory(config, 'templates')
        
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
            
            m.connect('dataset_pipelines', '/dataset/pipelines/{id}', action='edit')
            m.connect('/dataset/pipelines/{id}/assign_pipeline',\
                       action='assign_pipeline')
            m.connect('/dataset/pipelines/{id}/assign', action='assign')
            m.connect('/dataset/pipelines/{package_id}/remove_pipeline/{pipeline_id}',\
                       action='remove_pipe')
            m.connect('/dataset/pipelines/{id}/choose_action', action='choose_action')
        return route_map
    
    def after_map(self, route_map):
        # see IRoutes plugin interface
        return route_map
    

        
