import numpy as np
import scipy as sp
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
        self.bands = bands

    def __call__(self, value):
        for band in self.bands:
            if value in band:
                return band(value)
        return 0


class NullColorEntry(object):
    """A palette entry that matches the null value"""
     
    def __init__(self, color):
        self.color = color

    def __contains__(self, value):
        return value is None

    def __call__(self, v):
        return self.color

class CatchAll(object):
    """A palette entry that matches the null value"""
     
    def __init__(self, color):
        self.color = color

    def __contains__(self, value):
        return True

    def __call__(self, v):
        return self.color

class ColorBin(object):
    """A palette entry that presents a uniform color entry for any value between bounds"""

    def __init__(self, color, left_value=float('-Inf'), right_value=float("Inf"), include_left=True, include_right=True):
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
    """A gradient palette entry between two floating point numbers"""

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
        self.choices = dict(zip(choices,colors))
        self.null_color = null_color

    def __contains__(self, value):
        return value in self.choices

    def __call__(self, value):
        return self.choices(value)

class Lambda(object):
    """An imputed gradient that maps from a function of keyword args to a null, 0.0 - 1.0 value"""

    def __init__(self, fn, left_color, right_color, null_color=None):
        self.fn = fn
        self.left_color = left_color
        self.right_color = right_color
        self.null_color = null_color

    def __call__(self, value):
        a = self.fn(value)
        return (a*self.right_color) + ((1-a)*self.left_color)

class ArrayColorTransfer(object):
    """A ColorTransfer is what's used in Geoanalytics to color a raster dataset into a tricolor
    or four-color image"""

    def __init__(self, palette, colors=4):
        """A behaviour that takes a single array and a palette and transfers to a colored array"""
        self.palette = np.vectorize(palette, otypes=[np.uint32])
        self.colors = colors

    def __call__(self, value):
        return self.palette(value).view(dtype=np.uint8).reshape(value.shape[0], value.shape[1], 4)
            
class ArrayDictColorTransfer(object):
    def __init__(self, palette):
        """A behaviour that takes a dictionary of arrays and a lambda palette"""

class LayeredColorTransfer(object):
    ADD = 0
    SUBTRACT = 1
    DODGE = 2
    BURN = 3
    MULTIPLY = 4
    SOFT_LIGHT = 5
    HARD_LIGHT = 6 
    OVERLAY = 7
    SCREEN = 8
    
    def __init__(self, ord_pal_mode):
        """A behaviour that takes a series of tuples of (key, palette, blend_mode) and 
        transfers from first to last"""

