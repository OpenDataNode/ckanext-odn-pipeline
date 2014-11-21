'''
Created on 6.11.2014

@author: mvi
'''

import json
import socket
import urllib2
import pylons.config as config

# doc https://team.eea.sk/wiki/pages/viewpage.action?pageId=108660564
# TODO /pipelines/<pipeline_id>/schedules/
# TODO /pipelines/<pipeline_id>/schedules/<id>
# TODO /pipelines/<pipeline_id>/schedules/<schedule_id>
# TODO /pipelines/<pipeline_id>/executions
# TODO /pipelines/<pipeline_id>/executions/<execution_id>
# TODO /pipelines/<pipeline_id>/executions
# TODO /pipelines/<pipeline_id>/executions/<execution_id>/events

# TODO this class to ckancommons

TIMEOUT =  int(config.get('odn.uv.timeout', 5))

class UVRestAPIWrapper():
    
    def __init__(self, uv_url):
        assert uv_url
        self.url = uv_url
        

    def _send_request(self, uv_url):
        assert uv_url
        request = urllib2.Request(uv_url)
        # Creating a dataset requires an authorization header.
    #     request.add_header('Authorization', self.api_key)
        # Make the HTTP request.
        response = urllib2.urlopen(request, timeout=TIMEOUT)
        assert response.code == 200
        # Use the json module to load CKAN's response into a dictionary.
        response_dict = json.loads(response.read())
        return response_dict
    
    
    def get_pipelines(self):
        uv_url = '{0}/pipelines'.format(self.url)
        return self._send_request(uv_url)
    
    
    def get_pipeline_by_id(self, id):
        assert id
        uv_url = '{0}/pipelines/{1}'.format(self.url, id)
        return self._send_request(uv_url)

    def get_last_pipe_execution(self, pipe_id):
        assert pipe_id
        uv_url = '{0}/pipelines/{1}/executions/'.format(self.url, pipe_id)
        executions = self._send_request(uv_url)
        if executions and len(executions) > 0:
            last_exec = executions.pop(0)
            for execution in executions:
                print execution['start']
                if execution['start'] > last_exec['start']:
                    last_exec = execution
            return last_exec
        return None
