from django.http import HttpResponse
from django.contrib.gis.db.models.proxy import GeometryProxy
from django.shortcuts import render_to_response
from django.core import serializers
import json
import datetime
import shapely.geometry as g
from django.contrib.gis.geos import GEOSGeometry
import scipy
import cairo

from osgeo import gdal, osr
import tempfile
from ga_ows.views.common import GetCapabilitiesMixin

from ga_ows.views.wmsconfig import config_from_document
from ga_ows.rendering.cairo_geodjango_renderer import RenderingContext
from ga_ows import utils
from ga_ows.models.wms import Cache
from ga_ows.views import common
from ga_ows.utils import create_spatialref

class WMSAdapterBase(object):
    def __init__(self, application, cls, styles, **config):
        self.cls = cls
        self.styles = styles
        self.config = config
        self.application = application

        if 'requires_time' not in self.config:
            self.requires_time = False
        else:
            self.requires_time = self.config['requires_time']

        if 'requires_elevation' not in self.config:
            self.requires_elevation = False
        else:
            self.requires_elevation = self.config['requires_elevation']

    def get_wmsconfig(self):
        addresses = []
        if 'addresses' in self.config: 
            addresses = self.config['addresses']
        cache = True
        if 'cache' in self.config:
            cache = self.config['cache']
        expires = lambda x: None
        if 'expires' in self.config and callable(self.config['expires']):
            expires = self.config['expires']

        return config_from_document(
            ns={ 'name' : self.application },
            serviceurl= self.config['url'],
            addresses=addresses,
            styles=self.styles,
            layers=self.layerlist(), 
            cache=cache,
            expires=expires)

    def get_cache_key(self, **kwargs):
        return None

    def get_valid_elevations(self):
        return None

    def get_valid_times(self):
        return None

    def get_valid_versions(self):
        return None

    def layerlist(self):
        raise NotImplementedError("Must implement layerlist to avoid being abstract")

    def get_2d_dataset(self, **kwargs):
        raise NotImplementedError("Must implement get_2d_dataset to avoid being abstract")

    def nativesrs(self, layer):
        raise NotImplementedError("Must implement nativesrs to avoid being abstract")

    def nativebbox(self):
        raise NotImplementedError("Must implement nativebbox to avoid being abstract")

    def styles(self):
        return self.styles.keys()

class GeoDjangoWMSAdapter(WMSAdapterBase):
    def __init__(self, application, cls, styles, time_property=None, elevation_property=None, version_property=None, **kwargs):
        super(GeoDjangoWMSAdapter, self).__init__(application, cls, styles, **kwargs)
        self.time_property = time_property
        self.elevation_property = elevation_property
        self.version_property = version_property 

    def get_feature_info(self, wherex, wherey, srs, query_layers, info_format, feature_count, exceptions, *args, **kwargs):
        if type(srs) is int:
            kind='srid'
        elif srs.upper().startswith('EPSG'):
            kind=None
        elif srs.startswith('-') or srs.startswith('+'):
            kind='proj'
        else:
            kind='wkt'

        s_srs = create_spatialref(srs, srs_format=kind)
        t_srs = self.cls.srs
        crx = osr.CoordinateTransformation(s_srs, t_srs)
        wherex, wherey, _0 = crx.TransformPoint(wherex, wherey, 0)

        if info_format == 'application/json':
            return HttpResponse(serializers.serialize('json', [self.cls.objects.filter({ layer + "__contains" : g.Point(wherex, wherey) }).limit(feature_count) for layer in query_layers]),  mimetype='application/json')
        elif info_format == 'application/jsonp':
            return HttpResponse(kwargs['callback'] + '(' + serializers.serialize('json', [self.cls.objects.filter({ layer + "__contains" : g.Point(wherex, wherey) }).limit(feature_count) for layer in query_layers]) + ')',  mimetype='application/jsonp')

    def get_2d_dataset(self, bbox, width, height, query_layers, styles=None, **args):
        minx,miny,maxx,maxy = bbox
        if self.requires_time and 'time' not in args:
            raise Exception("this service requires a time parameter")
        if self.requires_elevation and 'elevation' not in args:
            raise Exception('this service requires an elevation')

        ss = None
        if type(self.styles) is dict:
            if not styles and 'default' in self.styles:
                ss = self.styles['default']
            elif styles:
                ss = self.styles[styles]
       
        ctx = RenderingContext(ss, minx, miny, maxx, maxy, width, height)
       
        default_srid=srid=self.cls.__dict__[query_layers[0]]._field.srid
        if 'srs' in args:
            if args['srs'].upper().startswith('EPSG'):
                srid = int(args['srs'][5:])
            else:
                srid = int(args['srs'])

        geom = GEOSGeometry('SRID={srid};POLYGON(({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, {minx} {maxy}, {minx} {miny}))'.format(srid=srid,minx=minx,miny=miny,maxx=maxx,maxy=maxy))

        flt = dict([(query_layer + "__bboverlaps" , geom) for query_layer in query_layers])
        for k,v in args.items():
            if k[0] == '_':
                flt[k[1:]] = v
            if k == 'time':
                flt[self.time_property] = v
            if k == 'elevation':
                flt[self.elevation_property] = v

        for layer in query_layers:
            if default_srid != srid:
                ctx.render(self.cls.objects.transform(srid).filter(**flt), lambda k: k.__getattribute__(layer))
            else:
                ctx.render(self.cls.objects.filter(**flt), lambda k: k.__getattribute__(layer))

        return ctx.surface

    def layerlist(self):
        for k,v in self.cls.__dict__.items():
            if type(v) is GeometryProxy:
                yield k

    def nativesrs(self, layer):
        return self.cls.__dict__[layer]._field.srs

    def nativebbox(self):
        return self.cls.objects.extent()

    def get_valid_times(self, **kwargs):
        if self.time_property:
            return [t.__getattribute__(self.time_property).strftime('%Y.%m.%d-%H:%M:%S.%f') for t in self.cls.objects.all()]

    def get_valid_versions(self, **kwargs):
        if self.version_property:
            return [t.__getattribute__(self.version_property).strfversion('%Y.%m.%d-%H:%M:%S.%f') for t in self.cls.objects.all()]

    def get_valid_elevations(self, **kwargs):
        if self.elevation_property:
            return [t.__getattribute__(self.elevation_property).strfversion('%Y.%m.%d-%H:%M:%S.%f') for t in self.cls.objects.all()]


class WMS(common.OWSView, GetCapabilitiesMixin):
    """
    A Django generic view for handling a WMS service.  The basic WMS service
    contains methods for GetCapabilities, GetMap, and GetFeatureInfo, as well
    as extensions for GetValidTimes and GetValidElevations.

    The key roles of this class are to expose views and parse and validate
    requests.  The actual work behind the views is largely done elsewhere.
    Much of the default WMS view class depends on an adapter class for support.
    The adapter must define several key methods to make a model available for
    serving up as a WMS service.  Adapters should define:

        * requires_time : Boolean.  Whether or not time is a required parameter of the service
        * requires_elevation : Boolean. Whether or not elevation is a required parameter of the service.
        * get_feature_info(version, wherex, wherey, srs, query_layers, info_format, feature_count, exceptions, **kwargs) : HttpResponse. Some kind of feature info response for a given x/y
        * get_wmsconfig() : WMSConfig. For creating the WMSFeatureInfo.  Since the WMSConfig is a fairly heavy object, I recommend only calculating this lazily.
        * get_valid_times(**kwargs) : Get valid times to use in the time field.  Should be a JSON object expressing a list of { value : TIME } and { range : [TIME, TIME] } objects.
        * get_valid_elevations(**kwargs) : Get valid elevations to use in the elevation request field.  Should be a JSON object expressing elevations like this: { units : 'm', 'elevations' : [e1, [e21,e22], e3, e4, ...]
        * nativebbox() : Get the native bounding box of the data.
        * nativesrs(layer) : Get the native SRS of the a layer
        * layerlist() : Get a list of all layers.
        * styles() : Get a list of abilable stylesheets
        * get_2d_dataset(bbox, width, height, query_layers, styles = None, **args): GDAL dataset or Cairo surface.  Return a rendered image of the data.  

    """
    adapter = None
    expires = lambda x: None

    def get_capabilities_response(self, request):
        render_to_response('ga_ows/WMS_Capabilities.template.xml', self.adapter.get_wmsconfig())

    def GetFeatureInfo(self, r, bbox, width, height, i, j, *args, **kwargs):
        x = int(i)
        y = int(j)
        bbox = [float(a) for a in bbox.split(',')]
        width = float(width)
        height = float(height)

        wherex = bbox[0] + x/width*(bbox[2]-bbox[0])
        wherey = bbox[1] + y/height*(bbox[3]-bbox[1])
        return self.adapter.get_feature_info(wherex, wherey, **kwargs)

    def GetValidTimes(self, r, **kwargs):
        """Vendor extension that returns valid timestamps in json format"""
        if 'callback' in kwargs:
                return HttpResponse("{callback}({js})".format(
                    callback=kwargs['callback'], 
                    js=json.dumps([t.strftime('%Y.%m.%d-%H:%M:%S.%f') for t in self.adapter.get_valid_times(**kwargs)]), mimetype='test/jsonp'
                ))
        else:
            return HttpResponse(json.dumps([t.strftime('%Y.%m.%d-%H:%M:%S.%f') for t in self.adapter.get_valid_times(**kwargs)]), mimetype='application/json')

    def GetValidElevations(self, r, **kwargs):
        """Vendor extension that returns valid elevation bands in json format"""
        if 'callback' in kwargs:
                return HttpResponse("{callback}({js})".format(
                    callback=kwargs['callback'], 
                    js=json.dumps(self.adapter.get_valid_elevations(**kwargs)), mimetype='test/jsonp'
                ))
        else:
            return HttpResponse(json.dumps(self.adapter.get_valid_elevations(**kwargs)), mimetype='application/json')

    def GetValidVersions(self, r, **kwargs):
        """Vendor extension that returns valid version bands in json format"""
        if 'callback' in kwargs:
                return HttpResponse("{callback}({js})".format(
                    callback=kwargs['callback'], 
                    js=json.dumps(self.adapter.get_valid_versions(**kwargs)), mimetype='test/jsonp'
                ))
        else:
            return HttpResponse(json.dumps(self.adapter.get_valid_versions(**kwargs)), mimetype='application/json')

    def GetMap(self,  
        r,
        layers=None, 
        srs=None,
        bbox=None,
        width=None, 
        height=None, 
        styles=None, 
        format='image/png', 
        bgcolor=None,
        transparent=True,
        exceptions='application/vnd.ogc.se_xml',
        times=None,
        elevations=None,
        **kwargs
    ):

        if not width:
            raise common.MissingParameterValue.at('width')
        if not height:
            raise common.MissingParameterValue.at('height')
        if not layers:
            raise common.MissingParameterValue.at('layers')
        if self.adapter.requires_time and not times:
            raise common.MissingParameterValue.at('times')
        if self.adapter.requires_elevation and not elevations:
            raise common.MissingParameterValue.at('elevations')

        d = {
            'layers' : layers, 'srs' : srs, 'bbox' : bbox, 'width' : width, 'height' : height, 
            'styles' : styles, 'format' : format, 'bgcolor' : bgcolor, 'transparent' : transparent, 
            'exceptions' : exceptions, 'times' : times, 'elevations' : elevations
        }
        for k,v in kwargs.items():
            d[k] = v

        cache_key = self.adapter.get_cache_key(**d)
        if cache_key:
            r = Cache.retrieve(self.adapter.application, cache_key)
            if r:
                return HttpResponse(r, mimetype=format)

        layers = layers.split(',')
        width = int(width)
        height = int(height)

        bbox = [float(x) for x in bbox.split(',')]
        
        if times:
            times = [utils.parsetime(t) for t in times.split(',')]

        if elevations:
            elevations = [float(e) for e in elevations.split(',')]

        if format.startswith('image/'):
            format = format[len('image/'):]

        ds = self.adapter.get_2d_dataset(
            query_layers=layers, 
            srs=srs, 
            bbox=bbox, 
            width=width, 
            height=height, 
            styles=styles, 
            bgcolor=bgcolor, 
            transparent=transparent, 
            times=times, 
            elevations=elevations,
            **kwargs
        )
 
        tmp = None
        if type(ds) is not gdal.Dataset: # then it == a Cairo imagesurface or numpy array, or at least... it'd BETTER be
            if ds.__class__.__base__ is cairo.Surface:
                tmp = tempfile.NamedTemporaryFile(suffix='.png')
                ds.write_to_png(tmp.name)
                ds = gdal.Open(tmp.name)
                # TODO add all the appropriate metadata from the request into the dataset if this == being returned as a GeoTIFF
            else:
                tmp = tempfile.NamedTemporaryFile(suffix='.tif')
                scipy.misc.imsave(tmp.name, ds)
                ds = gdal.Open(tmp.name)
                # TODO add all the appropriate metadata from the request into the dataset if this == being returned as a GeoTIFF

        if format == 'tiff' or format == 'geotiff':
            tmp = tempfile.NamedTemporaryFile(suffix='.tif')
            ds2 = gdal.GetDriverByName('GTiff').CreateCopy(tmp.name, ds)
            del ds2
            tmp.seek(0)
            ret = HttpResponse(tmp.read(), mimetype='image/' + format)
        elif format == 'png':
            tmp = tempfile.NamedTemporaryFile(suffix='.png')
            ds2 = gdal.GetDriverByName('png').CreateCopy(tmp.name, ds)
            del ds2
            tmp.seek(0)
            ret = HttpResponse(tmp.read(), mimetype='image/' + format)
        elif format == 'jpg' or format == 'jpeg':
            tmp = tempfile.NamedTemporaryFile(suffix='.jpg')
            ds2 = gdal.GetDriverByName('jpeg').CreateCopy(tmp.name, ds)
            del ds2
            tmp.seek(0)
            ret = HttpResponse(tmp.read(), mimetype='image/' + format)
        elif format == 'jp2k' or format == 'jpeg2000':
            tmp = tempfile.NamedTemporaryFile(suffix='.jp2')
            ds2 = gdal.GetDriverByName('jpeg2000').CreateCopy(tmp.name, ds)
            del ds2
            tmp.seek(0)
            ret = HttpResponse(tmp.read(), mimetype='image/' + format)
        elif format == 'gif':
            tmp = tempfile.NamedTemporaryFile(suffix='.gif')
            ds2 = gdal.GetDriverByName('gif').CreateCopy(tmp.name, ds)
            del ds2
            tmp.seek(0)
            ret = HttpResponse(tmp.read(), mimetype='image/' + format)
        else:
            try:
                tmp = tempfile.NamedTemporaryFile(suffix='.' + format)
                ds2 = gdal.GetDriverByName(format.encode('ascii')).CreateCopy(tmp.name, ds)
                del ds2
                tmp.seek(0)
                ret = HttpResponse(tmp.read(), mimetype='image/' + format)
            except Exception as ex:
                del tmp
                raise common.NoApplicableCode(str(ex))

        if cache_key and tmp:
            expiration = self.expires(datetime.datetime.now())
            tmp.seek(0)
            Cache.add(self.adapter.application, tmp.read(), cache_key, expires=expiration)
        return ret

