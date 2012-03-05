from collections import namedtuple
import datetime
from django.core.exceptions import ValidationError
from django.forms import MultipleChoiceField, TypedMultipleChoiceField, Field
from django.utils.datastructures import MultiValueDict
from django.utils.formats import sanitize_separators
from osgeo import osr

def parsetime(t):
    timeformats = [
        '%Y.%m.%d-%H:%M:%S.%f',
        '%Y.%m.%d-%H:%M:%S',
        '%Y.%m.%d-%H:%M',
        '%Y.%m.%d',
        '%Y%m%d%H%M%S%f',
        '%Y%m%d%H%M%S',
        '%Y%m%d%H%M',
        '%Y%m%d'
    ]

    if not t:
        return None

    ret = None
    for tf in timeformats:
        try:
            ret = datetime.datetime.strptime(t, tf)
        except:
            pass
    if ret:
        return ret
    else:
        raise ValueError('time data does not match any valid format: ' + t)

def create_spatialref(srs, srs_format='srid'):
    """
    Create an :py:class:osgeo.osr.SpatialReference from an srid, wkt,
    projection, or epsg code.  srs_format should be one of: srid, wkt, proj,
    epsg to represent a format in numerical srid form, well-known text, proj4,
    or epsg formats.
    """
    spatialref = osr.SpatialReference()
    if srs_format:
        if srs_format == 'srid':
            spatialref.ImportFromEPSG(srs)
        elif srs_format == 'wkt':
            spatialref.ImportFromWkt(srs)
        elif srs_format == 'proj':
            spatialref.ImportFromProj4(srs)
    else:
        spatialref.ImportFromEPSG(int(srs.split(':')[1]))
    return spatialref

mimetypes = namedtuple("MimeTypes", (
    'json', 'jsonp')
)(
    json='application/json',
    jsonp='text/plain'
)


class CaseInsensitiveDict(dict):
    """
    A subclass of :py:class:django.utils.datastructures.MultiValueDict that treats all keys as lower-case strings
    """

    def __init__(self, key_to_list_mapping=()):
        def fix(pair):
            key, value = pair
            return key.lower(),value
        super(CaseInsensitiveDict, self).__init__([fix(kv) for kv in key_to_list_mapping])

    def __getitem__(self, key):
        return super(CaseInsensitiveDict, self).__getitem__(key.lower())

    def __setitem__(self, key, value):
        return super(CaseInsensitiveDict, self).__setitem__(key.lower(), value)

    def get(self, key, default=None):
        if key not in self:
            return default
        else:
            return self[key]

    def getlist(self, key):
        if key not in self:
            return []
        elif isinstance(self[key], list):
            return self[key]
        elif isinstance(self[key], tuple):
            return list(self[key])
        else:
            return [self[key]]


class MultipleValueField(MultipleChoiceField):
    """A field for pulling in arbitrary lists of strings instead of constraining them by choice"""
    def validate(self, value):
        if self.required and not value:
            raise ValidationError(self.error_messages['required'])

class BBoxField(Field):
    def to_python(self, value):
        value = super(BBoxField, self).to_python(value)
        if not value:
            return -180.0,-90.0,180.0,90.0

        try:
            lx, ly, ux, uy = value.split(',')
            if self.localize:
                lx = float(sanitize_separators(lx))
                ly = float(sanitize_separators(ly))
                ux = float(sanitize_separators(ux))
                uy = float(sanitize_separators(uy))

                if uy < ly or ux < lx:
                    raise ValidationError("BBoxes must be in lower-left(x,y), upper-right(x,y) order")
        except (ValueError, TypeError):
            raise ValidationError("BBoxes must be four floating point values separated by commas")

        lx = float(sanitize_separators(lx))
        ly = float(sanitize_separators(ly))
        ux = float(sanitize_separators(ux))
        uy = float(sanitize_separators(uy))
        return lx, ly, ux, uy
