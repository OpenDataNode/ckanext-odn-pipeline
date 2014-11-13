'''
Created on 12.11.2014

@author: mvi
'''

import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.plugins
import ckan.logic as logic
import ckan.model as model

from ckan.common import _, request, c
from ckanext.model.pipelines import Pipelines
from ckanext.internal_catalog.plugin import get_pipeline

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized

render = base.render
abort = base.abort
lookup_package_plugin = ckan.lib.plugins.lookup_package_plugin
check_access = logic.check_access
get_action = logic.get_action


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
            abort(401, _('User %r not authorized to edit %s') % (c.user, id))
        # check if package exists
        try:
            c.pkg_dict = get_action('package_show')(context, data_dict)
            c.pkg = context['package']
        except NotFound:
            abort(404, _('Dataset not found'))
        except NotAuthorized:
            abort(401, _('Unauthorized to read package %s') % id)
        
        lookup_package_plugin(package_type).setup_template_variables(context, {'id': id})
    
    def edit(self, id):
        self._load(id)
        return render('package/pipelines.html')
    
    
    def choose_action(self, id):
        data = request.POST
        if u'action' in data:
            action = data[u'action']
            if action == 'existing':
                self._load(id)
                return render('pipeline/assign_pipeline.html')
            else:
                abort(404, _('Not implemented yet'))
        else:
            abort(404, _('Action was not choosed!'))
            
    
    
    def assign_pipeline(self, id):
        self._load(id) 
        return render('pipeline/choose_assign_action.html')
    
    
    def assign(self, id):
        self._load(id)

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
            h.flash_notice("No pipeline selected.")
            return render('package/pipelines.html')

        try:
            check_access('package_update', context, data_dict)
            package = get_action('package_show')(context, data_dict)
            # TODO add pipe
            package_pipe = Pipelines(package['id'], pipe['id'], name=pipe['name'])
            package_pipe.save() # this adds and commits too
        except Exception, e:
            h.flash_error(str(e))
#         except NotFound:
#             abort(404, _('Dataset not found'))
#         except NotAuthorized, e:
#             abort(401, _('User %r not authorized to edit %s') % (c.user, id))
        

        return render('package/pipelines.html')
    
    def remove_pipe(self, package_id, pipeline_id):
        assert package_id
        assert pipeline_id
        
        try:
            pipe = Pipelines(package_id, pipeline_id).get()
            
            if not pipe:
                h.flash_error("Couldn't remove pipeline, because\
                there is no such pipeline assigned to this dataset.")
                return self.edit(package_id)
            
            pipe.delete()
            pipe.commit()
            h.flash_success('Pipeline removed from dataset successfully')
        except Exception, e:
            h.flash_error('Failed to remove pipeline from dataset: %s'\
                           % (str(e),))
        
        return self.edit(package_id)