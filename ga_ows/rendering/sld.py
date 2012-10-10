"""Parse SLD and make stylesheets from it"""
import re
import math
from datetime import datetime
import numpy as np

def _parseHexColor(value):
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

def _isHexColor(value):
    return (len(value) == 7 or len(value) == 9) and value.startswith('#')


class Rule(object):
    """Represents an SLD rule"""
    def __init__(self, min_scale, max_scale, clauses):
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.clauses = clauses

    def __call__(self, data, pxsize):
        if pxsize > self.min_scale and pxsize < self.max_scale:
            return self.test(data)

    def test(self, data):
        return all(clause(data) for clause in self.clauses)

######### data accessors and literals ####################

class PA(object):
    """Represents a property accessor"""
    def __init__(self, field):
        self.field = field

    def call(self, data):
        k = data[self.field]
        k = float(k) if isinstance(k, int) else k
        k = _parseHexColor(k) if _isHexColor(k) else k
        return k

class L(object):
    """Represents a literal"""
    def __init__(self, value):
        try:
            self.value = float(value)
        except:
            self.value = value
        self.value = _parseHexColor(value) if _isHexColor(value) else value

    def __call__(self, data):
        return self.value

######### comparison operators ##########################

class Gt(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return self.e1(data) > self.e2(data)

class Ge(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return self.e1(data) >= self.e2(data)

class Lt(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return self.e1(data) < self.e2(data)

class Le(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return self.e1(data) <= self.e2(data)

class Ne(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return self.e1(data) != self.e2(data)

class Eq(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return self.e1(data) == self.e2(data)

class Null(object):
    def __init__(self, e1):
        self.e1 = e1

    def __call__(self, data):
        return self.e1(data) is None

class Btw(object):
    def __init__(self, e, l, r):
        self.e = e
        self.l = l
        self.r = r

    def __call__(self, data):
        v = self.e(data)
        return v <= self.r(data) and v >= self.e(data)

class Like(object):
    def __init__(self, e, value):
        self.e = e
        self.value = value

    def __call__(self, data):
        v = self.e(data)
        if self.value.startswith('%') and self.value.endswith('%'):
            return self.value in v
        elif self.value.startswith('%'):
            return v.endswith(self.value)
        elif self.value.endswith('%'):
            return v.startswith(self.value)
        else:
            return re.match(self.value, v)

class In(object):
    def __init__(self, e, *args):
        self.e = e
        self.values = args

    def __call__(self, data):
        v = self.e(data)
        values = set(x(data) for x in self.values)
        return v in values

class NotIn(object):
    def __init__(self, e, *args):
        self.e = e
        self.values = args

    def __call__(self, data):
        v = self.e(data)
        values = set(x(data) for x in self.values)
        return v not in values

######### Control flow operators ##############################

class IfThenElse(object):
    def __init__(self, c, t, f):
        self.c = c
        self.t = t
        self.f = f

    def __call__(self, data):
        return self.t(data) if self.c(data) else self.f(data)

######### Logical operators ##################################

class And(object):
    def __init__(self, *es):
        self.es = es

    def __call__(self, data):
        return all(e(data) for e in self.es)

class Or(object):
    def __init__(self, *es):
        self.es = es

    def __call__(self, data):
        return any(e(data) for e in self.es)

class Not(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return not self.e(data)

class PropertyExists(object):
    def __init__(self, prop):
        self.prop = prop

    def __call__(self, data):
        return self.prop in data


####### Math functions  #######################################

class Add(object):
    def __init__(self, exp1, exp2, *args):
        self.exp1 = exp1
        self.exp2 = exp2
        self.rest = args

    def __call__(self, data):
        reduce(float.__add__, (exp(data) for exp in self.rest), self.exp1(data) + self.exp2(data))

class Subtract(object):
    def __init__(self, exp1, exp2, *args):
        self.exp1 = exp1
        self.exp2 = exp2
        self.rest = args

    def __call__(self, data):
        reduce(float.__sub__, (exp(data) for exp in self.rest), self.exp1(data) - self.exp2(data))

class Multiply(object):
    def __init__(self, exp1, exp2, *args):
        self.exp1 = exp1
        self.exp2 = exp2
        self.rest = args

    def __call__(self, data):
        reduce(float.__mul__, (exp(data) for exp in self.rest), self.exp1(data) * self.exp2(data))

class Divide(object):
    def __init__(self, exp1, exp2, *args):
        self.exp1 = exp1
        self.exp2 = exp2
        self.rest = args

    def __call__(self, data):
        reduce(float.__div__, (exp(data) for exp in self.rest), self.exp1(data) / self.exp2(data))

class Abs(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return abs(self.e(data))

class Sin(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.sin(self.e(data))


class Sin(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.sin(self.e(data))

class Cos(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.cos(self.e(data))

class Tan(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.sin(self.e(data))

class Asin(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.asin(self.e(data))

class Acos(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.acos(self.e(data))

class Atan(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.atan(self.e(data))

class Ceil(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.ceil(self.e(data))

class Floor(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.floor(self.e(data))

class Round(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return round(self.e(data))

class Log10(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.log10(self.e(data))

class Ln(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.log(self.e(data))

class Exp(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.exp(self.e(data))

class Deg(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.degrees(self.e(data))

class Rad(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.radians(self.e(data))

class Sqrt(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return math.sqrt(self.e(data))

class Pow(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return math.pow(self.e1(data), self.e2(data))

class Atan2(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return math.atan2(self.e1(data), self.e2(data))

########## String functions #######################################

class Concat(object):
    def __init__(self, e1, e2, *es):
        self.e1 = e1
        self.e2 = e2
        self.es = es

    def __call__(self, data):
        return reduce(str.__add__, (e(data) for e in self.es), self.e1(data) + self.e2(data))

class Capitalize(object):
    def __init__(self, e):
        self.e =e

    def __call__(self, data):
        return self.e(data).title()

class Trim(object):
    def __init__(self, e):
        self.e =e

    def __call__(self, data):
        return self.e(data).strip()

class IndexOf(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return self.e1(data).index(self.e2(data))

class LastIndexOf(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return self.e1(data).rindex(self.e2(data))

class Substring(object):
    def __init__(self, e, start, end):
        self.e = e
        self.start = start
        self.end = end

    def __call__(self, data):
        return self.e(data)[ self.start(data) : self.end(data) ]

class SubstringStart(object):
    def __init__(self, e, start):
        self.e = e
        self.start = start

    def __call__(self, data):
        return self.e(data)[ self.start(data) : ]

class Upper(object):
    def __init__(self, e):
        self.e =e

    def __call__(self, data):
        return self.e(data).upper()

class Lower(object):
    def __init__(self, e):
        self.e =e

    def __call__(self, data):
        return self.e(data).lower()

class StringLength(object):
    def __init__(self, e):
        self.e =e

    def __call__(self, data):
        return len(self.e(data))

class EndsWith(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return self.e1(data).endswith(self.e2(data))

class EqualsIgnoreCase(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return self.e1(data).lower() == self.e2(data).lower()

class Matches(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return re.match(self.e2(data), self.e1(data))

class EndsWith(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return self.e1(data).endswith(self.e2(data))

class EndsWith(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return self.e1(data).endswith(self.e2(data))

class EndsWith(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return self.e1(data).endswith(self.e2(data))

class EndsWith(object):
    def __init__(self, e1, e2):
        self.e1 = e1
        self.e2 = e2

    def __call__(self, data):
        return self.e1(data).endswith(self.e2(data))

########### Parsing and data format functions ##########################################################################

class DateFormat(object):
    def __init__(self, e, fmt):
        self.e = e
        self.fmt = fmt

    def __call__(self, data):
        return self.e(data).strftime(self.fmt)

class DateParse(object):
    def __init__(self, e, fmt):
        self.e= e
        self.fmt = fmt

    def __call__(self, data):
        return datetime.strptime(self.e(data), self.fmt)

class NumberFormat(object):
    def __init__(self, e, fmt):
        self.e = e
        self.fmt = fmt

    def __call__(self, data):
        return self.fmt % (self.e(data), )

class ParseBoolean(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return bool(self.e(data))


class ParseInt(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return int(self.e(data))


class ParseFloat(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return float(self.e(data))


class ParseLong(object):
    def __init__(self, e):
        self.e = e

    def __call__(self, data):
        return long(self.e(data))

############# Data transformation functions ############################################################################

class Recode(object):
    def __init__(self, e, default, **kwargs):
        self.e = e
        self.default = default
        self.code = kwargs

    def __call__(self, data):
        v = self.e(data)
        return self.code[v] if v in self.code else self.default

class Categorize(object):
    def __init__(self, e, *args):
        self.e = e
        self.pairs = args

    def __call__(self, data):
        v = self.e(data)
        for value, threshold in self.pairs:
            if threshold is None:
                return value
            elif v >= threshold:
                return value

class Interpolate(object):
    LINEAR = 'linear'
    CUBIC = 'cubic'
    COSINE = "cosine"

    NUMERIC = 'numeric'
    COLOR = "color"

    def __init__(self, e, mode=NUMERIC, method=LINEAR, default=None, *args):
        self.e = e
        self.method=method
        self.mode = mode
        self.pairs = args

    def __call__(self, data): # TODO support color, support cubic spline interpolation
        v = self.e(data)
        for i, (value, threshold) in enumerate(self.pairs):
            if threshold is None:
                return value
            elif v >= threshold:
                xmin = threshold
                xmax = self.pairs[i+1][1]
                xspn = xmax-xmin
                y = (v-xmin)/xspn

                if self.method == Interpolate.LINEAR:
                    return y*value + (1-y)*self.pairs[i+1][0]
                elif self.method == Interpolate.CUBIC:
                    return y*value + (1-y)*self.pairs[i+1][0]
                elif self.method == Interpolate.COSINE:
                    return math.cos(math.pi*y)*value + math.cos(math.pi * (1-y))*self.pairs[i+1][0]

