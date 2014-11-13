'''
Created on 11.11.2014

@author: mvi
'''

from ckan.lib.cli import CkanCommand
import sys

import logging
from ckanext.model.pipelines import pipelines_table
log = logging.getLogger('ckanext')

class PipelineCmd(CkanCommand):
    """Database initialization command
    
    Usage:
        
        internal-catalog-cmd initdb
        - initializes required db tables
    """
    
    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 3
    min_args = 0
    
    def __init__(self, name):
        super(PipelineCmd, self).__init__(name)
        
    
    def command(self):
        self._load_config()
        
        if len(self.args) == 0:
            self.parser.print_usage()
            sys.exit(1)
        cmd = self.args[0]
        
        if cmd == 'initdb':
            log.info('Starting db initialization')
            if not pipelines_table.exists():
                log.info("creating pipelines table")
                pipelines_table.create()
                log.info("pipelines table created successfully")
            else:
                log.info("pipelines table already exists")
            log.info('End of db initialization')
            
        if cmd == 'uninstall':
            log.info('Starting uninstall command')
            if pipelines_table.exists():
                log.info("dropping pipelines table")
                pipelines_table.drop()
                log.info("dropped pipelines table successfully")
            else:
                log.info("Table pipelines doesn't exist")
            log.info('End of uninstall command')