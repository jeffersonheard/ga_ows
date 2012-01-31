import numpy as np

def _parseHexColor(self, value):
    red = 0.0
    green = 0.0
    blue = 0.0
    alpha = 1.0
    if len(value) == 3:
        red = green = blue = int(value[1:3], 16) / 255.0
    elif len(value) >= 7:
        red = int(value[1:3],16) / 255.0
        green = int(value[3:5], 16) / 255.0
        blue = int(value[5:7], 16) / 255.0
    if len(value) == 9:
        alpha = int(value[7:9], 16) / 255.0

    return np.array((red,green,blue,alpha), dtype=np.float32)


class Stylesheet(object):
    """A symbolizer for features.
    
    In general, methods can be sent a "val" parameter, a "fun" parameter, or both.
    If the method has a val parameter, then this value is passed directly to the rasterizer.
    If the method has a fun parameter, then the function is called with the record (a dict 
    object) and the result is passed to the rasterizer.  If both are passed, then a value 
    lookup is performed on the data record and the result of the lookup is passed to the
    function as the first argument, and the result of that is passed to the rasterizer.

    If a function is specified, the second argument will always be the scale denominator,
    for the purpose of rendering features different sizes by scale.  

    The following properties are defined:

        * stroke_width * stroke_color * stroke_dash * stroke_cap
        * stroke_join * fill_color * fill_pattern * label
        * font_family * font_weight * font_slant * font_size
        * font_options * label_halo_size * label_halo_color * point_size
        * point_shape * point_icon * compositing_operator
        * lod * label_color

        Also, stylesheets can inherit by passing a 'parent' or 'parents' parameter' to the constructor with other stylesheet instanecs

    """

    FeatureProperties = frozenset([
        'stroke_width', 'stroke_color', 'stroke_dash', 'stroke_cap', 'stroke_join',
        'fill_color','fill_pattern',
        'point_size','point_shape','point_icon',
        'compositing_operator', 'lod'
    ])

    LabelProperties = frozenset([
        'label','label_color','font_face','font_weight','font_slant','font_size','font_options','font_align',
        'label_halo_size','label_halo_color','label_align', 'label_offsets'
    ])

    def _condprop(self, p, data, pxlsz, callback=None):
        ret = None
        if p in self._props:
            if 'fun' in  self._props[p] and self._props[p]['fun'] is not None:
                if 'val' in self._props[p] and self._props[p]['val'] is not None:
                    ret = self._props[p]['fun'](data[ self._props[p]['val'] ], pxlsz)
                else:
                    ret = self._props[p]['fun'](data, pxlsz)
            else:
                ret = self._props[p]['val']

        if ret and callback:
            return callback(ret)
        else:
            return ret

    @classmethod
    def from_module(cls, modname):
        """allow a python module to be used as a stylesheet. scans the module
        for useful properties and adds them to the sheet
        
        """
        m = __import__(modname)
        d = dict(filter(lambda x: not x[0].startswith('__'), m.__dict__.items()))
        ss = cls(**d)
        return ss


    def __init__(self, **options):
        """Create a new stylesheet.  Any of the properties available in the stylesheet can 
        be set by passing its name as a keyword parameter along with a dictionary 
        { 'val' : val, 'fun' : fun } pair, which may be missing either val or fun, but 
        not both."""

        self._props = {
            'stroke_width' : { 'val' : 1.0 },
            'stroke_color' : { 'val' : (0.0,0.0,0.0,1.0) },
            'fill_color' : { 'val' : (1.0,1.0,0.0,0.5) },
            'compositing_operator' : { 'val' : 'over' },
        }

        if 'parent' in options:
            for key, item in options['parent']._props:
                self._props[key] = item

        if 'parents' in options:
            for parent in options['parents']:
                for key, item in parent._props:
                    self._props[key] = item


        for option, value in options.items():
            if type(value) is dict:
                self._props[option] = value
            elif callable(value):
                self._props[option] = { 'fun' : value }
            else:
                self._props[option] = { 'val' : value }

    ### Styling methods

    def styles(self, data, pxlsz):
        return frozenset([(p, self._condprop(p, data, pxlsz)) for p in Stylesheet.FeatureProperties])

    def label(self, data, pxlsz):
        if 'label' in self._props:
            if 'fun' in self._props['label']:
                if 'val' in self._props['label']:
                    return (self._props['label']['fun'](data[self.label['val']]), frozenset([(p, self._condprop(p, data, pxlsz)) for p in Stylesheet.LabelProperties]))
                else:
                    return (self._props['label']['fun'](data, pxlsz), frozenset([(p, self._condprop(p, data, pxlsz)) for p in Stylesheet.LabelProperties]))
            elif 'val' in self._props['label']:
                if self._props['label']['val'] in data:
                    return (data['val'], frozenset([(p, self._condprop(p, data, pxlsz)) for p in Stylesheet.LabelProperties]))
                else:
                    return None, None
            else:
                return None, None
        else:
            return None, None

    def s(self, prop, value=None, fun=None):
        self._props[prop] = { 'val' : value, 'fun' : fun }
            
