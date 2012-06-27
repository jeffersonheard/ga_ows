# Appropriated with license from https://github.com/newsapps/django-boundaryservice/blob/master/boundaryservice/tastyhacks.py

# The MIT License
#
#Copyright (c) 2011 Chicago Tribune, Christopher Groskopf, Ryan Nagle
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

from django.contrib.gis.db.models import GeometryField
from django.utils import simplejson

from tastypie.bundle import Bundle
from tastypie.fields import ApiField, CharField
from tastypie.resources import ModelResource


class GeometryApiField(ApiField):
    """
    Custom ApiField for dealing with data from GeometryFields (by serializing them as GeoJSON).
    """
    dehydrated_type = 'geometry'
    help_text = 'Geometry data.'

    def hydrate(self, bundle):
        value = super(GeometryApiField, self).hydrate(bundle)
        if value is None:
            return value
        return simplejson.dumps(value)

    def dehydrate(self, obj):
        return self.convert(super(GeometryApiField, self).dehydrate(obj))

    def convert(self, value):
        if value is None:
            return None

        if isinstance(value, dict):
            return value

        # Get ready-made geojson serialization and then convert it _back_ to a Python object
        # so that Tastypie can serialize it as part of the bundle
        return simplejson.loads(value.geojson)


class GeoResource(ModelResource):
    """
    ModelResource subclass that handles geometry fields as GeoJSON.
    """

    @classmethod
    def api_field_from_django_field(cls, f, default=CharField):
        """
        Overrides default field handling to support custom GeometryApiField.
        """
        if isinstance(f, GeometryField):
            return GeometryApiField

        return super(GeoResource, cls).api_field_from_django_field(f, default)