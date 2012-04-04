""" This module contains utilities for creating paletted images from arbitrary rasters (arrays).  This is often used in
the datacube and pyramid models to take floating-point datasets and convert into paletted raster data.  Palettes are the
alternative to Stylesheets for raster data. Your styles dictionary in your WMSAdapter will look like this::

    def f2c(f):
    return (5.0/9.0) * (f-32)

    palettes = {
        'freezing_danger' : Palette(
            ColorBin(rgba(1,108,89,200), right_value=f2c(10)),
            ColorBin(rgba(28,144,153,200), left_value=f2c(10), right_value=f2c(28), include_right=False),
            ColorBin(rgba(103,169,207,200), left_value=f2c(28), right_value=f2c(36), include_right=False),
            ColorBin(rgba(255,255,255,0), left_value=f2c(36), include_left=False),
        ),

        'temps' : Palette(
            ColorBin(rgba(37, 52, 148), right_value=f2c(20), include_right=False),
            ColorBin(rgba(44, 127, 184), left_value=f2c(20), right_value=f2c(32), include_right=False),
            ColorBin(rgba(65, 182, 196), left_value=f2c(32), right_value=f2c(42), include_right=False),
            ColorBin(rgba(161, 218, 180), left_value=f2c(42), right_value=f2c(52), include_right=False),
            ColorBin(rgba(255, 255, 204), left_value=f2c(52), right_value=f2c(62), include_right=False),
            ColorBin(rgba(254, 217, 142), left_value=f2c(62), right_value=f2c(72), include_right=False),
            ColorBin(rgba(254, 153, 41), left_value=f2c(72), right_value=f2c(82), include_right=False),
            ColorBin(rgba(217, 95, 14), left_value=f2c(82), right_value=f2c(92), include_right=False),
            ColorBin(rgba(153, 52, 4), left_value=f2c(92), right_value=f2c(122)),
            CatchAll(rgba(255,255,255,0))
        ),

        'temps_gradient' : Palette(
            ColorBin(rgba(37, 52, 148), right_value=f2c(10), include_right=False),
            LinearGradient(rgba(37, 52, 148), rgba(44, 127, 184), left_value=f2c(10), right_value=f2c(22), include_right=False),
            LinearGradient(rgba(44, 127, 184), rgba(65, 182, 196), left_value=f2c(22), right_value=f2c(32), include_right=False),
            LinearGradient(rgba(65, 182, 196), rgba(161, 218, 180), left_value=f2c(32), right_value=f2c(42), include_right=False),
            LinearGradient(rgba(161, 218, 180), rgba(255, 255, 204), left_value=f2c(42), right_value=f2c(52), include_right=False),
            LinearGradient(rgba(255, 255, 204), rgba(254, 217, 142), left_value=f2c(52), right_value=f2c(62), include_right=False),
            LinearGradient(rgba(254, 217, 142), rgba(254, 153, 41), left_value=f2c(62), right_value=f2c(72), include_right=False),
            LinearGradient(rgba(254, 153, 41), rgba(217, 95, 14), left_value=f2c(72), right_value=f2c(82), include_right=False),
            LinearGradient(rgba(217, 95, 14), rgba(153, 52, 4), left_value=f2c(82), right_value=f2c(92), include_right=False),
            ColorBin(rgba(153, 52, 4), left_value=f2c(92), right_value=f2c(122)),
            CatchAll(rgba(255,255,255,0))
        ),
    }

This defines three palettes in a dictionary which can be passed into "styles" for the DataCube WMSAdapter or the Pyramid
WMSAdapter.  The first two palettes contain color binned palettes, which will use one color for the entire band of values
and the third palette contains a linear gradient, which will create a smooth transition between two values.  Order is
important in palettes to some extent.  If you have a CatchAll color in your palette, that must come last or else everything
will take the catch-all color.
"""

import numpy as np
import logging

log = logging.getLogger(__name__)

def rgba(r, g, b, a=1.0):
    """A function that returns a color for rgba values between 0 and 1"""
    return np.array((255*r, 255*g, 255*b, 255*a), dtype=np.uint8)

def rgba255(r, g, b, a=255):
    """A function that returns a color for rgba values between 0 and 255"""
    return np.array((r, g, b, a), dtype=np.uint8)

def rgbahex(color):
    """A function that returns a color for a hex integer"""
    return np.array((color,), dtype=np.uint32).view(dtype=np.uint8)

class Palette(object):
    """This is a dummy function in case I want to use a class later"""

    def __init__(self, *bands):
        """
        :param bands: Every band is one of the various band classes: ColorBin, CatchAll, etc defined in this module
        """
        self.bands = bands

    def __call__(self, value):
        for band in self.bands:
            if value in band:
                return band(value)
        return 0


class NullColorEntry(object):
    """A palette entry that matches the null value, None"""
     
    def __init__(self, color):
        """
        :param color: A color as returned by rgba, rgba255, or rgbahex
        """
        self.color = color

    def __contains__(self, value):
        return value is None

    def __call__(self, v):
        return self.color

class CatchAll(object):
    """A palette entry that matches the any value"""
     
    def __init__(self, color):
        """
        :param color: A color as returned by rgba, rgba255, or rgbahex
        """
        self.color = color

    def __contains__(self, value):
        return True

    def __call__(self, v):
        return self.color

class ColorBin(object):
    """A palette entry that presents a uniform color entry for any value between bounds"""

    def __init__(self, color, left_value=float('-Inf'), right_value=float("Inf"), include_left=True, include_right=True):
        """
        :param color: A color as returned by rgba, rgba255, or rgbahex
        :param left_value: The lower value for the bin.
        :param right_value: The upper value for the bin.
        :param include_left: Whether or not to include the exact left value in the bin
        :param include_right: Whether or not to include the exact right value in the bin.
        """
        self.l = left_value
        self.r = right_value
        self.color = color.view(np.int32)[0]
        if include_right:
            self.rcmp = 0
        else:
            self.rcmp = -1

        if include_left:
            self.lcmp = 0
        else:
            self.lcmp = 1

    def __contains__(self, value):
        return cmp(value, self.l) <= self.lcmp and cmp(value, self.r) >= self.rcmp

    def __call__(self, v):
        return self.color

class LinearGradient(object):
    """A gradient palette entry between two floating point numbers.  Calculates gradient colors using HSL to provide
    a smooth gradient without an intermediate gray between compilments."""

    def _hsl(self, c):
        r,g,b,a = c / 255.0
        mx = max(r,g,b)
        mn = min(r,g,b)
        h = 0
        s = 0
        l = (mx+mn)/2
        if mx != mn:
            if l < 0.5:
                s = (mx-mn) / (mx+mn)
            else:
                x = (mx-mn) / (2.0-mx-mn)
        if r==mx:
            h = (g-b) / (mx-mn)
        elif g==mx:
            h = 2.0+(b-r) / (mx-mn)
        else:
            h = 4.0+(r-g) / (mx-mn)
        h *= 60
        if h < 0:
            h += 360
        return np.array((h,s,l,a), dtype=np.float32)

    def _rgb(self, quad):
        h,s,l,a = quad
        c = 1 - abs(2*l - 1) * s
        h /- 60
        x = c*(1 - abs(h % 2-1))
        rgba = None
        
        if h < 1:
            rgba = np.array(c,x,0,a, dtype=np.float32)
        elif h < 2:
            rgba = np.array(x,c,0,a, dtype=np.float32)
        elif h < 3:
            rgba = np.array(c,x,0,a, dtype=np.float32)
        elif h < 4:
            rgba = np.array(0,c,x,a, dtype=np.float32)
        elif h < 5:
            rgba = np.array(0,x,c,a, dtype=np.float32)
        elif h < 6:
            rgba = np.array(x,0,c,a, dtype=np.float32)
        else:
            rgba = np.array(c,0,x,a, dtype=np.float32)
        rgba += l - 0.5*c
        return np.rint(rgba*255, out=np.zeros((4,), np.uint8))


    def __init__(self, left_color, right_color, left_value, right_value, include_left=True, include_right=True):
        """
        :param left_color: A color as returned by rgba, rgba255, or rgbahex
        :param right_color: A color as returned by rgba, rgba255, or rgbahex
        :param left_value: The lower value for the bin.
        :param right_value: The upper value for the bin.
        :param include_left: Whether or not to include the exact left value in the bin
        :param include_right: Whether or not to include the exact right value in the bin.
        """
        self.l = left_value
        self.r = right_value
        self.lc = self._hsl(left_color)
        self.rc = self._hsl(right_color)
        if include_right:
            self.rcmp = 0
        else:
            self.rcmp = -1

        if include_left:
            self.lcmp = 0
        else:
            self.lcmp = 1

    def __contains__(self, value):
        return cmp(value, self.l) <= self.lcmp and cmp(value, self.r) >= self.rcmp

    def interp(self,v):
        return (v-self.l) / (self.r-self.l)

    def __call__(self, v):
        iv = self.interp(v)
        return self._rgb((iv*self.rc) + ((1-iv)*self.lc))

class Choices(object):
    """A stepped gradient among logical choices, with the possibility of an "out of band" choice"""

    def __init__(self, choices, colors, null_color=None):
        """
        :param choices: Any of these values will produce the a color
        :param colors: The respective colors for each choice
        :param null_color: The color to use for None entries (NullColorEntry works just as well)
        :return:
        """
        self.choices = dict(zip(choices,colors))
        self.null_color = null_color

    def __contains__(self, value):
        return value in self.choices

    def __call__(self, value):
        return self.choices(value)

class Lambda(object):
    """An imputed gradient that maps from a function of keyword args to a null, 0.0 - 1.0 value"""

    def __init__(self, fn, left_color, right_color, null_color=None):
        """
        :param fn: A function that takes data and returns something in the interval [0.0,1.0] or None
        :param left_color: the color associated with 0.0
        :param right_color: the color associated with 1.0
        :param null_color: if None, then lambdas will be calcualted twice - once for "contains" and once for the value

        """
        self.fn = fn
        self.left_color = left_color
        self.right_color = right_color
        self.null_color = null_color

    def __contains__(self, value):
        return self.null_color is None and self.fn(value) is None

    def __call__(self, value):
        a = self.fn(value)
        if a is not None:
            return (a*self.right_color) + ((1-a)*self.left_color)
        else:
            return self.null_color

class ArrayColorTransfer(object):
    """A ColorTransfer is what's used in Geoanalytics to color a raster dataset into a tricolor
    or four-color image.  This is mostly used internally.  You should be fine just using Palette."""

    def __init__(self, palette, colors=4):
        self.palette = np.vectorize(palette, otypes=[np.uint32])
        self.colors = colors

    def __call__(self, value):
        return self.palette(value).view(dtype=np.uint8).reshape(value.shape[0], value.shape[1], 4)
            
