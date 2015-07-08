'''
Created on 12.11.2014

@author: mvi
'''

import logging
import socket

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.plugins
import ckan.logic as logic
import ckan.model as model

from ckan.common import _, request, c
from ckanext.model.pipelines import Pipelines
from ckanext.pipeline.plugin import get_pipeline, get_available_pipes_options,\
    get_all_pipes_options
from ckanext.pipeline.uv_helper import UVRestAPIWrapper

import pylons.config as config
from pylons import session

uv_api_auth = '{0}:{1}'.format(config.get('odn.uv.api.auth.username', ''), config.get('odn.uv.api.auth.password', ''))

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized

render = base.render
abort = base.abort
lookup_package_plugin = ckan.lib.plugins.lookup_package_plugin
check_access = logic.check_access
get_action = logic.get_action

log = logging.getLogger('ckanext')


def get_url_without_slash_at_the_end(url):
    if url and url.endswith("/"):
        return url[:-1]
    else:
        return url

uv_url = get_url_without_slash_at_the_end(config.get('odn.uv.url', None))
uv_api_url = get_url_without_slash_at_the_end(config.get('odn.uv.api.url', None))

def disable_schedules_for_pipe(pipe_id):
    try:
        uv_api = UVRestAPIWrapper(uv_api_url, uv_api_auth)
        schedules = uv_api.get_all_schedules(pipe_id)
        for schedule in schedules:
            if not schedule.get('enabled', True):
                continue # already disabled
            schedule['enabled'] = False
            uv_api.edit_pipe_schedule(pipe_id, schedule)
    except Exception, e:
        log.error('Failed to disable schedules for pipeline id {0}: {1}'.format(pipe_id, e.msg))
    except socket.timeout, e:
        log.error('Timeout: Failed to disable schedules for pipeline id {0}: {1}'.format(pipe_id, e))


class ICController(base.BaseController):

    
    def _get_package_type(self, id):
        """
        Given the id of a package it determines the plugin to load
        based on the package's type name (type). The plugin found
        will be returned, or None if there is no plugin associated with
        the type.
        """
        pkg = model.Package.get(id)
        if pkg:
            return pkg.type or 'dataset'
        return None


    def _load(self, id):
        package_type = self._get_package_type(id.split('@')[0])
        data_dict = {'id': id}
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author, 'for_view': True,
                   'auth_user_obj': c.userobj}
        
        try:
            check_access('package_update', context, data_dict)
        except NotAuthorized, e:
            abort(401, _(u'User {user} not authorized to edit {id}').format(user=c.user, id=id))
        # check if package exists
        try:
            c.pkg_dict = get_action('package_show')(context, data_dict)
            c.pkg = context['package']
        except NotFound:
            abort(404, _(u'Dataset not found'))
        except NotAuthorized:
            abort(401, _(u'Unauthorized to read package {id}').format(id=id))
        
        lookup_package_plugin(package_type).setup_template_variables(context, {'id': id})
    
    
    def show(self, id):
        assert uv_url
        
        self._load(id)
        vars = {'uv_edit_url': uv_url + '/#!PipelineEdit/{pipe_id}',
                'uv_scheduler_url': uv_url + '/#!Scheduler'}
        return render('package/pipelines.html', extra_vars = vars)
    
    
    def choose_pipeline(self, id):
        data = request.POST
        if u'action' in data:
            action = data[u'action']
            if action == 'existing':
                self._load(id)
                options, descriptions = get_available_pipes_options()
                vars = {'options': options,
                        'descriptions': descriptions,
                        'form_action': 'assign' 
                        }
                return render('pipeline/assign_pipeline.html', extra_vars = vars)
            elif action == 'created-manually':
                self._load(id)
                vars = {'form_action': 'create_pipe_manually'}
                return render('pipeline/create_pipeline.html', extra_vars = vars)
            elif action == 'choose-pipe-to-copy':
                self._load(id)
                options, descriptions = get_all_pipes_options()
                vars = {'options': options,
                        'descriptions': descriptions,
                        'form_action': 'set_name_descr',
                        'submit_label': _(u'Next step')
                        }
                return render('pipeline/choose_pipeline.html', extra_vars = vars)
            else:
                abort(404, _(u'Not implemented yet'))
        else:
            abort(404, _(u'Action was not choosen!'))
    
    def set_name_descr(self, id):
        # just to forwards choosed pipe id to copy to setting name and descr
        data = request.POST
        pipe_to_copy = None
        if u'pipeline' in data:
            pipe_to_copy = data[u'pipeline']
            
        if not pipe_to_copy:
            self._load(id)
            options, descriptions = get_all_pipes_options()
            vars = {'options': options,
                    'descriptions': descriptions,
                    'form_action': 'set_name_descr'  
            }
            h.flash_error(_(u"Choose pipeline to copy."))
            return render('pipeline/choose_pipeline.html', extra_vars = vars)
        
        self._load(id)
        vars = {'pipeline': pipe_to_copy,
               'form_action': 'create_copy'
               }
        return render('pipeline/create_pipeline.html', extra_vars = vars)


    def create_copy(self, id):
        assert uv_url
        
        data = request.POST
        name = ''
        description = ''
        pipe_to_copy = None
        if u'name' in data:
            name = data[u'name']
        if u'description' in data:
            description = data[u'description']
        if u'pipeline' in data:
            pipe_to_copy = data[u'pipeline']
            
        if not name.strip():
            h.flash_error(_(u"Pipeline name is required."))
            self._load(id)
            return render('pipeline/create_pipeline.html',
                           extra_vars={'descr': description, 
                                       'form_action': 'create_copy',
                                       'pipeline':pipe_to_copy})
            
        data_dict = {'id': id}
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'auth_user_obj': c.userobj}
        
        assert uv_api_url
        open_on_load = None
        msg = None
        err_msg = None
        try:
            check_access('package_update', context, data_dict)
            package = get_action('package_show')(context, data_dict)

            # creating new Pipe in UV
            uv_api = UVRestAPIWrapper(uv_api_url, uv_api_auth)
            
            actor_id = session.get('ckanext-cas-actorid', None)
            user_id = None
            if c.userobj:
                user_id = c.userobj.id 
            
            new_pipe = uv_api.create_copy_pipeline(pipe_to_copy, name, description, user_id, actor_id)
            
            # associate it with dataset
            if not new_pipe:
                err_msg = _(u"Pipeline wasn't created.")
            elif Pipelines.by_pipeline_id(new_pipe['id']): # checks if already exists
                err_msg = _(u'Pipeline is already associated to some dataset.')
            else:
                # adds pipe association
                package_pipe = Pipelines(package['id'], new_pipe['id'], name=new_pipe['name'])
                package_pipe.save() # this adds and commits too
                msg = _(u"Pipeline {name} assigned successfully.").format(name=new_pipe['name'])
                open_on_load = uv_url + '/#!PipelineEdit/{pipe_id}'.format(pipe_id=new_pipe['id'])
        except NotFound:
            abort(404, _(u'Dataset not found'))
        except NotAuthorized:
            abort(401, _(u'User {user} not authorized to edit {id}').format(user=c.user, id=id))
        except Exception, e:
            log.exception(e)
            err_msg = _(u"Couldn't create/associate pipeline: {error}").format(error=e.msg)
            self._load(id)
            vars = {
                'form_action': 'create_copy',
                'name': name,
                'descr': description,
                'pipeline':pipe_to_copy,
                'err_msg': err_msg
            }
            return render('pipeline/create_pipeline.html', extra_vars = vars)
        except socket.timeout, e:
            err_msg = _(u"Connecting to UnifiedViews timed out.")
        
        self._load(id)
        vars = {'uv_url': open_on_load,
                'link_show': h.url_for('dataset_pipelines', id=id, qualified=True),
                'msg': msg,
                'err_msg': err_msg}
        return render('pipeline/create_pipeline_response.html', extra_vars=vars)
    
    def choose_action(self, id):
        self._load(id) 
        return render('pipeline/choose_assign_action.html')
    
    
    def assign(self, id):
        pipe = None
        data = request.POST
        if u'pipeline' in data:
            pipe_id = data[u'pipeline']
            pipe, err_msg = get_pipeline(pipe_id)

        data_dict = {'id': id}
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'auth_user_obj': c.userobj}

        if not pipe:
            h.flash_notice(_(u"No pipeline selected."))
            base.redirect(h.url_for('dataset_pipelines', id=id))
            return

        try:
            check_access('package_update', context, data_dict)
            package = get_action('package_show')(context, data_dict)
            
            # checks if already exists
            if Pipelines.by_pipeline_id(pipe['id']):
                h.flash_error(_(u'Pipeline is already associated to some dataset.'))
                base.redirect(h.url_for('pipe_assign', id=id))
            else:
                # adds pipe association
                package_pipe = Pipelines(package['id'], pipe['id'], name=pipe['name'])
                package_pipe.save() # this adds and commits too
                h.flash_success(_(u"Pipeline assigned successfully."))
        except NotFound:
            abort(404, _(u'Dataset not found'))
        except NotAuthorized:
            abort(401, _(u'User {user} not authorized to edit {id}').format(user=c.user, id=id))
        
        base.redirect(h.url_for('pipe_assign', id=id))


    def remove_pipe(self, id, pipeline_id):
        assert id
        assert pipeline_id
        
        try:
            data_dict = {'id': id}
            context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'auth_user_obj': c.userobj}
            check_access('package_update', context, data_dict)
            package = get_action('package_show')(context, data_dict)
            # id is most probably is package.name so we have to get actual id
            pipe = Pipelines(package['id'], pipeline_id).get()
            
            if not pipe:
                h.flash_error(_(u"Couldn't remove pipeline, because there is no such pipeline assigned to this dataset."))
                base.redirect(h.url_for('pipe_assign', id=id))
            else:
                pipe_id = pipe.pipeline_id
                pipe.delete()
                pipe.commit()
                h.flash_success(_(u'Pipeline removed from dataset successfully'))
                
                disable_schedules_for_pipe(pipe_id)
        except NotFound:
            abort(404, _(u'Dataset not found'))
        except NotAuthorized:
            abort(401, _(u'User {user} not authorized to edit {id}').format(user=c.user, id=id))
        
        base.redirect(h.url_for('pipe_assign', id=id))
        
    
    def create_pipe_manually(self, id):
        assert uv_url
        
        data = request.POST
        name = ''
        description = ''
        if u'name' in data:
            name = data[u'name']
        if u'description' in data:
            description = data[u'description']
            
        if not name.strip():
            h.flash_error(_(u"Pipeline name is required."))
            self._load(id)
            return render('pipeline/create_pipeline.html',
                           extra_vars={'descr': description, 
                                       'form_action': 'create_pipe_manually'})
            
        data_dict = {'id': id}
        context = {'model': model, 'session': model.Session,
                   'user': c.user or c.author,
                   'auth_user_obj': c.userobj}
        
        assert uv_api_url
        open_on_load = None
        msg = None
        err_msg = None
        try:
            check_access('package_update', context, data_dict)
            package = get_action('package_show')(context, data_dict)

            # creating new Pipe in UV
            uv_api = UVRestAPIWrapper(uv_api_url, uv_api_auth)
            
            actor_id = session.get('ckanext-cas-actorid', None)
            user_id = None
            if c.userobj:
                user_id = c.userobj.id 
            
            new_pipe = uv_api.create_pipeline(name, description, user_id, actor_id)
            
            # associate it with dataset
            if not new_pipe:
                err_msg = _(u"Pipeline wasn't created.")
            elif Pipelines.by_pipeline_id(new_pipe['id']): # checks if already exists
                err_msg = _(u'Pipeline is already associated to some dataset.')
            else:
                # adds pipe association
                package_pipe = Pipelines(package['id'], new_pipe['id'], name=new_pipe['name'])
                package_pipe.save() # this adds and commits too
                msg = _(u"Pipeline {name} assigned successfully.").format(name=new_pipe['name'])
                open_on_load = uv_url + '/#!PipelineEdit/{pipe_id}'.format(pipe_id=new_pipe['id'])
        except NotFound:
            abort(404, _(u'Dataset not found'))
        except NotAuthorized:
            abort(401, _(u'User {user} not authorized to edit {id}').format(user=c.user, id=id))
        except Exception, e:
            log.exception(e)
            err_msg = _(u"Couldn't create/associate pipeline: {error}").format(error=e.msg)
            self._load(id)
            vars = {
                'form_action': 'create_pipe_manually',
                'name': name,
                'descr': description,
                'err_msg': err_msg
            }
            return render('pipeline/create_pipeline.html', extra_vars = vars)
        except socket.timeout, e:
            err_msg = _(u"Connecting to UnifiedViews timed out.")
        
        self._load(id)
        vars = {'uv_url': open_on_load,
                'link_show': h.url_for('dataset_pipelines', id=id, qualified=True),
                'msg': msg,
                'err_msg': err_msg}
        return render('pipeline/create_pipeline_response.html', extra_vars=vars)


    def execute_now(self, id, pipeline_id):
        
        err_msg = None
        try:
            uv_api = UVRestAPIWrapper(uv_api_url, uv_api_auth)
            
            # get dataset org id
            self._load(id)
            actor_id = session.get('ckanext-cas-actorid', None)
            
            # get id of logged user
            user_id = None
            if c.userobj:
                user_id = c.userobj.id 
            
            execution = uv_api.execute_now(pipeline_id, user_id=user_id, user_actor_id=actor_id)
            log.debug("started execution: {0}".format(execution))
        except Exception, e:
            err_msg = _(u"Couldn't execute pipeline: {error}").format(error=e.msg)
            log.exception(e)
        except socket.timeout, e:
            err_msg = _(u"Connecting to UnifiedViews timed out.")
        
        if err_msg:
            h.flash_error(err_msg)        
        
        base.redirect(h.url_for('dataset_pipelines', id=id))
