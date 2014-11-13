'''
Created on 11.11.2014

@author: mvi
'''


from sqlalchemy.sql.expression import or_
from sqlalchemy import types, Column, Table
import vdm.sqlalchemy

import types as _types
from ckan.model import domain_object
from ckan.model.meta import metadata, Session, mapper


pipelines_table = Table('pipelines', metadata,
            Column('package_id', types.UnicodeText, primary_key=True, nullable=False, unique=False, autoincrement=False),
            Column('pipeline_id', types.BIGINT, primary_key=True, nullable=False, unique=True, autoincrement=False),
            Column('name', types.UnicodeText, nullable=True, unique=False)
            )


vdm.sqlalchemy.make_table_stateful(pipelines_table)


class Pipelines(domain_object.DomainObject):
    
    def __init__(self, package_id, pipeline_id, name=None):
        assert package_id
        assert pipeline_id
        self.package_id = package_id
        self.pipeline_id = pipeline_id
        self.name = name
    
    @classmethod
    def get_all(cls):
        return Session.query(cls).all()
    
    @classmethod
    def by_dataset_id(cls, dataset_id):
        return Session.query(cls)\
            .filter_by(package_id = dataset_id).all()
            
    def get(self):
        return Session.query(Pipelines)\
            .filter_by(package_id = self.package_id, pipeline_id = self.pipeline_id).first()
            

mapper(Pipelines, pipelines_table)