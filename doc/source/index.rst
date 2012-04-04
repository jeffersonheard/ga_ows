.. ga_ows documentation master file, created by
   sphinx-quickstart on Tue Apr  3 18:25:57 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

ga_ows : OWS services for Geoanalytics
======================================
Core to `Geoanalytics`_ are the `Open Geographic Consortium's`_ Open Web
Services.  ``ga_ows`` is a reusable GeoDjango_ webapp that provides you the
ability to expose GeoDjango models and Python objects as geographic
webservices.

A geographic webservice allows you to access data in your GeoDjango models by
bounding box and other filters; these data can then be imported into other
geographic databases, or perhaps more importantly as layers on a map.  For
layering WFS and WMS services, see `the OpenLayers project`_ .

.. _the OpenLayers project: http://www.openlayers.org
.. _Geoanalytics: http://geoanalytics.renci.org
.. _Open Geographic Consortium's: http://opengeospatial.org
.. _GeoDjango: http://djangoproject.com

How does it work?   OWS is based on Django's class-based generic views. The
following in your ``urls.py`` will create a WFS_ service for a the models in
your app::

    from ga_ows.views.wfs import WFS
    from myapp import models as m

    urlpatterns = patterns('',

    # ...

        url(r'^wfs/?', WFS.as_view(
            models=[m.MyModel1, m.MyModel2], # everything but this is optional.
            title='My app\'s WFS',
            keywords=['some','keywords'],
            fees='one dollar',
            provider_name='RENCI',
            addr_street='100 Europa Dr. ste 529',
            addr_city='Chapel Hill',
            addr_admin_area='NC',
            addr_postcode='27515',
            addr_country='USA',
            addr_email='jeff@renci.org'
        )),

    # ...

    )

.. _WFS: http://www.opengeospatial.org/standards/wfs

This will create a WFS endpoint at ``$django_server/$myapp_root/wfs`` that
serves up features in GML and any of the formats that support the creation of
single-file dataset in OGR_ (note that for now this means shapefiles are not
supported for output since they require multiple files, although they will be
in the near future).

WMS works similarly.  It is a bit more complicated to setup because for most
applications you need a stylesheet to actually render model data into a map,
but the principles are similar.  You also have a number of choices in WMS 
that are explained further in the module documentation.

.. _WMS:http://www.opengeospatial.org/standards/wms
.. _OGR::http://www.gdal.org

Implemented features
====================

Currently implemented in WFS are the following operations, as urlencoded HTTP
GET and HTTP POST.  XML and SOAP are not supported yet and not high on my
priority list at the moment:

    * GetCapabilities
    * DescribeFeatureType [1]_
    * GetFeature
    * ListStoredQueries
    * DescribeStoredQueries

Yet to be implemented features include:

    * Transaction
    * GetFeatureWithLock
    * LockFeature
    * GetPropertyValue
    * CreateStoredQuery
    * DropStoredQuery

If you require transactional features, right now `django-tastypie`_ may well
cover your needs nicely.  It creates RESTful APIs for models instead of using
the standard WFS transaction support.

.. [1] DescribeFeatureType requires that you have your models' schema exposed through django-model-schemas_
.. _django-tastypie:http://django-tastypie.readthedocs.org/en/latest/index.html
.. _django-model-schemas:http://bitbucket.org/eegg/django-model-schemas/wiki/Home

Querying the data
=================

The standard query language is **not** implemented.  Instead, the `Django QuerySet query language`_ 
is supported, including `geographic extensions through GeoDjango`_.  In the
``query`` parameter, you pass a JSON document containing the query as sets of
parameters and JSON serializable values (geometry should be WKT_ strings in the
same SRS_ as the service's native SRS.).  Thus the following filter is valid::

    {
        "geom__crosses" : "LINESTRING(0 0, 10 10, 20 30)",
        "entry__gt" : "10/10/2010",
        "speed__gt" : 10
    }

Not all Django model queries are supported yet.  In particular, referencing model fields and queries that requiree Q()
are not yet supported.  These will be supported in future versions of ``ga_ows``.

.. _Django QuerySet query language: http://docs.djangoproject.com/en/dev/topics/db/queries/#field-lookups-intro
.. _geographic extensions through GeoDjango: http://docs.djangoproject.com/en/dev/ref/contrib/gis/geoquerysets/#spatial-lookups
.. _SRS: http://spatialreference.org
.. _WKT: http://en.wikipedia.org/wiki/Well-known_text

Common return formats
=====================

Although nothing is guaranteed, most implementations of OGR contain at least the GeoJSON and GML formats as well as a
number of others, often including CSV.  For a complete list of formats, check the GetCapabilities document.

Requirements
============

Because OWS does a lot of heavy lifting, there are a few requirements above and beyond basic GeoDjango:

WFS
----

    * GDAL
    * lxml
    * psycopg2 [2]_
    * PostGIS or Spatialite backends (MySQL and Oracle are currently unsupported)
    * django-tastypie *(if you want to support transactions)*
    * django-model-schemas *(for DescribeFeatureType)*

WMS
----

    * as above, but also...
    * pycairo
    * shapely
    * numpy
    * scipy - *(yes, really)*

.. [2] note that Postgres 9.1 users will want to get the `patch for psycopg2 described here`_

.. _patch for psycopg2 described here:http://code.djangoproject.com/ticket/16778

Support
=======

Please post issues at `github's`_ repository for `ga_ows` for support.

.. _github's: http://www.github.com/JeffHeard


Contents:

.. toctree::
   :maxdepth: 2

   modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

