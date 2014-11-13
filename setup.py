from setuptools import setup, find_packages

version = '0.1.0-SNAPSHOT'

setup(
    name='ckanext-internal-catalog',
    version=version,
    description="""
    Adding dataset_purge api action for sysadmins only
    """,
    long_description="""
    Adding dataset_purge api action for sysadmins only
    """,
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Martin Virag',
    author_email='martin.virag@eea.sk',
    uv_url='',
    license='',
    packages=find_packages(exclude=['examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.internal_catalog', 'ckanext.model',\
                        'ckanext.commands', 'ckanext.controllers'],
    package_data={'': [
                       'fanstatic/*.css',\
                       'fanstatic/*.js',\
                       'templates/*.html',\
                       'templates/package/*.html',\
                       'templates/pipeline/*.html',\
                       'templates/pipeline/snippets/*.html']},
    include_package_data=True,
    zip_safe=False,
    install_requires=['ckancommons>=0.1.0-SNAPSHOT'],
    entry_points=\
    """
    [ckan.plugins]
    internal-catalog=ckanext.internal_catalog.plugin:InternalCatalog
    [paste.paster_command]
    internal-catalog-cmd = ckanext.commands.internal_catalog_cmd:InternalCatalogCmd
    """,
)