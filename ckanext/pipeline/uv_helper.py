'''
Created on 6.11.2014

@author: mvi
'''

import logging

import json
import requests
import urllib2
import pylons.config as config
import base64

# doc https://team.eea.sk/wiki/pages/viewpage.action?pageId=108660564
# TODO POST /pipelines/<pipeline_id>/schedules
# TODO GET /pipelines/<pipeline_id>/schedules/<id>
# TODO GET /pipelines/<pipeline_id>/executions
# TODO /pipelines/<pipeline_id>/executions/<execution_id>
# TODO /pipelines/<pipeline_id>/executions
# TODO /pipelines/<pipeline_id>/executions/<execution_id>/events

# TODO this class to ckancommons

TIMEOUT =  int(config.get(u'odn.uv.timeout', 5))
AUTH_HEADER_FIELD_NAME = u'Authorization'
USER_EXT_ID = u'userExternalId'
USER_ACTOR_EXT_ID = u'userActorExternalId'

log = logging.getLogger('ckanext')


class UVRestAPIWrapper():
    
    def __init__(self, uv_url, auth=None):
        assert uv_url
        self.url = uv_url
        self.auth = None
        if auth:
            self.auth = base64.b64encode(auth)
        

    def _send_request(self, uv_url):
        """Sends GET request
        """
        assert uv_url
        log.debug("uv_helper sending request to: {0}".format(uv_url))
        request = urllib2.Request(uv_url)
        if self.auth:
            request.add_header(AUTH_HEADER_FIELD_NAME, self.auth)
        # Make the HTTP request.
        response = urllib2.urlopen(request, timeout=TIMEOUT)
        assert response.code == 200
        # Use the json module to load CKAN's response into a dictionary.
        response_dict = json.loads(response.read())
        return response_dict


    def _send_request_with_data(self, uv_url, data_string, is_put=False):
        """Sends POST request with JSON data
        """
        assert uv_url
        headers = {'content-type': 'application/json'}
        if self.auth:
            headers[AUTH_HEADER_FIELD_NAME] = self.auth

        if is_put:
            response = requests.put(uv_url, data=data_string, headers=headers)
        else:
            response = requests.post(uv_url, data=data_string, headers=headers)
        if response.status_code != 200:
            raise Exception("Error sending request to {0}: {1}".format(uv_url, response.text))
        response_dict = response.json()
        return response_dict
    
    
    def get_pipelines(self, user_id=None):
        uv_url = '{0}/pipelines'.format(self.url)
        if user_id:
            uv_url = '{0}?{1}={2}'.format(uv_url, USER_EXT_ID, user_id)
        return self._send_request(uv_url)
    
    
    def get_pipeline_by_id(self, pipe_id):
        assert pipe_id
        uv_url = '{0}/pipelines/{1}'.format(self.url, pipe_id)
        return self._send_request(uv_url)


    def create_pipeline(self, name, description, user_id, user_actor_id):
        uv_url = '{0}/pipelines'.format(self.url)
        data = {
                'name':name,
                'description': description,
                USER_EXT_ID: user_id,
                USER_ACTOR_EXT_ID: user_actor_id
        }
        return self._send_request_with_data(uv_url, json.dumps(data))
    
    
    def create_copy_pipeline(self, pipe_to_copy, name, description, user_id, user_actor_id):
        assert pipe_to_copy
        uv_url = '{0}/pipelines/{1}/clones'.format(self.url, pipe_to_copy)
        data = {
                'name':name,
                'description': description,
                USER_EXT_ID: user_id,
                USER_ACTOR_EXT_ID: user_actor_id
        }
        return self._send_request_with_data(uv_url, json.dumps(data))


    def get_last_finished_execution(self, pipe_id):
        assert pipe_id
        uv_url = '{0}/pipelines/{1}/executions/last'.format(self.url, pipe_id)
        try:
            execution = self._send_request(uv_url)
            return execution
        except urllib2.HTTPError, err:
            if err.code == 404:
                return None
            else:
                raise err


    def get_next_execution_info(self, pipe_id):
        """ Return information about next execution
        (schedule_id, next_execution_time, execution_status)
        """
        assert pipe_id
        # find pending execution
        uv_url = '{0}/pipelines/{1}/executions/pending'.format(self.url, pipe_id)
        executions = self._send_request(uv_url)
        if executions and len(executions) > 0:
            execution = executions.pop(0)
            return execution['schedule'], execution['lastChange'], execution['status']
        
        # if there is no pending execution, get next execution from schedules
        uv_url = "{0}/pipelines/{1}/schedules/~all/scheduledexecutions".format(self.url, pipe_id)
        schedules = self._send_request(uv_url)
        if schedules and len(schedules) > 0:
            schedule = schedules.pop(0)
            return schedule['schedule'], schedule['start'], None
        
        return None, None, None 
    

    def execute_now(self, pipe_id, is_debugging=False, user_id=None, user_actor_id=None):
        assert pipe_id
        uv_url = '{0}/pipelines/{1}/executions/'.format(self.url, pipe_id)
        data = {
                'debugging':is_debugging,
                USER_EXT_ID: user_id,
                USER_ACTOR_EXT_ID: user_actor_id
        }
        return self._send_request_with_data(uv_url, json.dumps(data))


    def get_all_schedules(self, pipe_id):
        """ Gets all schedules for selected pipeline
        
        :param pipe_id: pipeline id
        :type pipe_id: interger
        
        :return: list of dictionaries
        """
        assert pipe_id
        uv_url = '{0}/pipelines/{1}/schedules'.format(self.url, pipe_id)
        return self._send_request(uv_url)
    

    def edit_pipe_schedule(self, pipe_id, schedule):
        assert schedule
        schedule_id = schedule['id']
        uv_url = '{0}/pipelines/{1}/schedules/{2}' \
                    .format(self.url, pipe_id, schedule_id)
        return self._send_request_with_data(uv_url, json.dumps(schedule), is_put=True)
