'''
Created on 11.11.2014

@author: mvi
'''


from sqlalchemy.sql.expression import or_
from sqlalchemy import types, Column, Table, ForeignKey
import vdm.sqlalchemy

import types as _types
from ckan.model import domain_object
from ckan.model.meta import metadata, Session, mapper
from sqlalchemy.orm import relationship, backref
from ckan.model.package import Package


pipelines_table = Table('pipelines', metadata,
            Column('package_id', ForeignKey('package.id'), primary_key=True, nullable=False, unique=False, autoincrement=False),
            Column('pipeline_id', types.BIGINT, primary_key=True, nullable=False, unique=True, autoincrement=False),
            Column('name', types.UnicodeText, nullable=True, unique=False)
            )


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
        assert dataset_id
        return Session.query(cls)\
            .filter_by(package_id = dataset_id).all()
            
    @classmethod
    def by_pipeline_id(cls, pipeline_id):
        assert pipeline_id
        return Session.query(cls)\
            .filter_by(pipeline_id = pipeline_id).first()
            
    def get(self):
        return Session.query(Pipelines)\
            .filter_by(package_id = self.package_id, pipeline_id = self.pipeline_id).first()
            

mapper(Pipelines, pipelines_table, properties={
    "pipelines": relationship(Package, single_parent=True, backref=backref('pipelines', cascade="all, delete, delete-orphan"))
})