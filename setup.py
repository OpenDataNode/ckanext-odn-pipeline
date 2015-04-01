from setuptools import setup, find_packages

version = '0.3.3-SNAPSHOT'

setup(
    name='ckanext-odn-pipeline',
    version=version,
    description="""
    Extension for administration of pipelines
    """,
    long_description="""
    Extension for administration of UnifiedViews pipelines
    """,
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Martin Virag',
    author_email='martin.virag@eea.sk',
    uv_url='',
    license='',
    packages=find_packages(exclude=['examples', 'tests']),
    namespace_packages=['ckanext',
                        'ckanext.pipeline',
                        'ckanext.model',
                        'ckanext.commands',
                        'ckanext.controllers',
                        'ckanext.internal_api',
                        'ckanext.resource_update_api'],
    package_data={'': [
                       'i18n/*/LC_MESSAGES/*.po',
                       'fanstatic/*.css',\
                       'fanstatic/*.js',\
                       'templates/*.html',\
                       'templates/package/*.html',\
                       'templates/pipeline/*.html',\
                       'templates/pipeline/snippets/*.html']},
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.html', 'ckan', None),
        ]
    }, # for babel.extract_messages, says which are source files for translating
    entry_points=\
    """
    [ckan.plugins]
    odn_pipeline=ckanext.pipeline.plugin:PipelinePlugin
    odn_resource_update_api=ckanext.resource_update_api.plugin:ResourceUpdateAPIPlugin
    internal_api=ckanext.internal_api.plugin:InternalApiPlugin
    [paste.paster_command]
    pipeline-cmd = ckanext.commands.pipeline_cmd:PipelineCmd
    """,
)