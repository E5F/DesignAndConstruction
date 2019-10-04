# top panel redesign calculator to evaluate all options in option tree

### imports
import math as m
from collections import namedtuple

### variables
w = 0.4
l = 0.5

material_data = {'alu': {'Suts': 100000000,
                         'Sy': 90000000,
                         'E': 72400000000,
                         'rho': 2780},
                 'steel': {'Suts': 1275000000,
                           'Sy': 1100000000,
                           'E': 210000000000,
                           'rho': 7800},}

options = {'Skin material': ['alu', 'steel'],
           'Skin thickness': [0.8e-3, 1.0e-3, 1.2e-3],
           'Stringer type': {'a':{'Material':'alu', 'Thickness':1.5e-3, 'Side':2e-2},
                             'b':{'Material':'alu', 'Thickness':2e-3, 'Side':2e-2},
                             'c':{'Material':'alu', 'Thickness':1e-3, 'Side':1.5e-2},
                             'd':{'Material':'alu', 'Thickness':1.5e-3, 'Side':1.5e-2},
                             'e':{'Material':'steel', 'Thickness':1.5e-3, 'Side':1.5e-2},
                             'f':{'Material':'steel', 'Thickness':2e-3, 'Side':1.5e-2}}}

### functions
def indent(txt):
    return '\n'.join(['    ' + line for line in txt.split('\n')])

def stringer_configs():
    """Generate all possible conbinations of stringer configuration,
    mixing all types of stringers but preserving symmetry"""
    configs = []
    for a in range(7):  # lol should've just used combinations
        for b in range(7-a):
            for c in range(7-(a+b)):
                for d in range(7-(a+b+c)):
                    for e in range(7-(a+b+c+d)):
                        for f in range(7-(a+b+c+d+e)):
                            air = 7-(a+b+c+d+e+f)
                            types = {'a':a*2, 'b':b*2, 'c':c*2, 'd':d*2, 'e':e*2, 'f':f*2, None:air*2}
                            for center in types:
                                types = {'a':a*2, 'b':b*2, 'c':c*2, 'd':d*2, 'e':e*2, 'f':f*2, None:air*2}  # ugly af
                                types[center] += 1
                                config = {Stringer(name): types[name] for name in types if name is not None and types[name]!=0}
                                configs.append(config)
    return configs

def sheet_buckling(panel):
    """Returns critical loads for sheet buckling"""
    try:
        stringer_pitch = w/(sum(panel.stringers.values())-1)
    except ZeroDivisionError:
        stringer_pitch = w
    sheet = panel.area*3.6*panel.skin.material_properties['E']*((panel.skin.thickness/stringer_pitch)**2)
    return sheet

def column_buckling(panel):
    """Return critical buckling load for column buckling"""
    slend_ratio = 0.5**2 / m.sqrt(panel.MOI/panel.area)
    slend_ratio_crit = m.sqrt(2*m.pi**2*material_data['alu']['E']/material_data['alu']['Sy'])  # hard-coded alu, don't know how to treat different types of stringers
    max_stress = (1 - slend_ratio ** 2 / (2 * slend_ratio_crit ** 2)) * material_data['alu']['Sy']
    # max_stress=max_stress/(5/3+(3/8*slend_ratio/slend_ratio_crit)-slend_ratio**3/(8*slend_ratio_crit**3)) ---- This adds a safety factor, might only be for steel. See pg.719, Mechanics of Materials book.
    column = max_stress * panel.area
    return column

def compressive_failure(panel):
    """"Return critical failure load for compressive failure"""
    compressive = panel.area*panel.skin.material_properties['Suts']
    return compressive


### classes
class Rectangle:
    """Class defining basic features of a rectangular cross-section like area, MOI and centroid"""
    def __init__(self, w, t):
        self.width = w
        self.thickness = t

    @property
    def area(self):
        """Cross-sectional area of the rectangle"""
        return self.width*self.thickness

    @property
    def centroid(self):
        """Centroid of the rectangle as measured from the top down"""
        return self.thickness/2

    @property
    def MOI(self):
        """MOI around own centroid around the horizontal axis"""
        return self.width*self.thickness**3


class Skin(Rectangle):
    """Defines properties of a skin, including a knockdown factor when it has buckled"""
    def __init__(self, material, thickness, knockdown=0.3, width=w, length=l):
        # input assignments
        self.material = material
        self.thickness = thickness
        self.width = width
        self.length = length
        self.material_properties = material_data[self.material]
        # inherit area, centroid, MOI from rectangle
        super(Skin, self).__init__(self.width, self.thickness)
        # knockdown factor
        self.knockdown_factor = 1  # area multiplier
        self.knockdown = knockdown  # factor to be set as self.knockdown_factor when skin buckles

    @property
    def area(self):
        return self.knockdown_factor*self.width*self.thickness

    @property
    def mass(self):
        """Calculates the weight of the skin"""
        return self.length*self.area*self.material_properties['rho']

    def __str__(self):
        return f'''Skin made of {self.material} with thickness {self.thickness}
With material properties {self.material_properties}'''


class Stringer:
    """Defines the properties of an L-shaped stringer"""
    def __init__(self, type, length=l):
        # input assignments
        self.type = type
        self.length = length
        self.properties = options['Stringer type'][self.type]
        self.material_properties = material_data[self.properties['Material']]
        self.thickness = self.properties['Thickness']
        self.side = self.properties['Side']
        # components
        self.horizontal = Rectangle(self.side-self.thickness, self.thickness)
        self.vertical = Rectangle(self.thickness, self.side)

    @property
    def area(self):
        """Total area of the stringer"""
        return self.horizontal.area + self.vertical.area

    @property
    def centroid(self):
        """Centroid location measured from the top of the stringer down"""
        return (self.horizontal.centroid*self.horizontal.area + self.vertical.centroid*self.vertical.area)/self.area

    @property
    def MOI(self):
        """Calculates the MOI around the centroid of the stringer standing alone.
        Don't use this for the panel, as you should not nest Steiner's terms"""
        return self.horizontal.MOI+self.horizontal.area*(self.horizontal.centroid-self.centroid)**2 \
               + self.vertical.MOI + self.vertical.area*(self.vertical.centroid-self.centroid)**2

    @property
    def mass(self):
        """Calculates the weight of the stringer"""
        return self.length*self.area*self.material_properties['rho']

    def __str__(self):
        return f'''Stringer of type {self.type}
With properties {self.properties}
And material properties {self.material_properties}'''


class Panel:
    """Combines the skin and stringers in a particular configuration
    and provides progressive failure analysis on the assemmbly in its test() function"""
    def __init__(self, skin, stringers={Stringer('a'):3, Stringer('b'):4}):
        self.skin = skin
        self.stringers = stringers

    @property
    def area(self):
        return self.skin.area + sum([s.area*self.stringers[s] for s in self.stringers])

    @property
    def centroid(self):
        """Centroid location measured from the top of the skin down into the stringers"""
        return (self.skin.area*self.skin.centroid + sum([self.stringers[s]*s.area*s.centroid for s in self.stringers]))/self.area

    @property
    def MOI(self):
        """MOI of the entire panel calculated from separate rectangles"""
        skin_MOI = self.skin.MOI + self.skin.area*self.skin.centroid**2
        stringer_MOI = sum([self.stringers[s]*(s.horizontal.MOI+s.horizontal.area*(s.horizontal.centroid+self.skin.thickness)**2
                                               + s.vertical.MOI+s.vertical.area*(s.vertical.centroid+self.skin.thickness)**2) for s in self.stringers])
        return skin_MOI + stringer_MOI

    @property
    def mass(self):
        """Calculates the weight of the entire top panel"""
        return self.skin.mass + sum([s.mass*self.stringers[s] for s in self.stringers])

    def test(self):
        """Running progressive failure analysis on the panel"""
        sheet_start = sheet_buckling(self)
        column_start = column_buckling(self)
        compressive_start = compressive_failure(self)
        if sheet_start<30000:
            self.skin.knockdown_factor = self.skin.knockdown
        column = column_buckling(self)
        compressive = compressive_failure(self)
        self.skin.knockdown_factor = 1  # reset knockdown factor... ugly af
        return sheet_start, column, compressive

    def __str__(self):
        """Whoever reads this will get a bar of chocolate at the draft final design report TW session"""
        stringerlist = '\n'.join([f'{self.stringers[s]} times '+s.__str__() for s in self.stringers])
        return f'''Panel with mass {round(self.mass,4)} kg and buckling load of {round(min(self.test()[:2]))} N and failure load of {round(self.test()[2])} N consisting of:
{indent(self.skin.__str__())}
And {sum(self.stringers.values())} stringers: 
{indent(stringerlist)}'''

original = Panel(Skin('alu', 0.0008, knockdown=0.3), {Stringer('a'):7})
redesign = Panel(Skin('alu', 0.0008, knockdown=0.3), {Stringer('c'):7})

if __name__ == '__main__':
    panels = []
    ### option loop
    for skin_material in options['Skin material']:
        for skin_thickness in options['Skin thickness']:
            for config in stringer_configs():
                panel = Panel(Skin(skin_material, skin_thickness), config)
                panels.append(panel)
    # select viable options based on criteria like mass<0.85kg, x% of the target load achieved, target loads like sheet buckling, column buckling and compressive failure
    viable_panels = sorted([p for p in panels if p.mass<0.85 and all(goal*1<load for load,goal in zip(p.test(), (7500,22500,22500)))], key=lambda x:x.mass)
    for p in viable_panels:
        print(p)

    # wing box total weight calculations
    average_length = 1.4  # average stringer and skin length due to slanted side
    Config = namedtuple('Config', 'Striffeners Skins')
    old_config = Config({Stringer('a', length=average_length): 8,  # full length stringers
                         Stringer('a', length=0.75): 2,  # half length stringers
                         Stringer('a', length=0.15): 13},  # stiffeners are essentially type a stringers, but shorter
                        {Skin('alu', 0.0008, length=average_length): 2,  # top and bottom skin
                         Skin('alu', 0.0008, length=average_length, width=0.15): 2,  # two side skins
                         Skin('alu', 0.0008, length=0.15, width=0.4): 2})  # two ribs

    new_config = Config({Stringer('c', length=average_length): 5,  # summed length of type c stringers
                         Stringer('d', length=average_length): 2,  # summed length of type d stringers
                         Stringer('a', length=average_length): 2,  # summed length of type a stringers
                         Stringer('a', length=0.15): 7},  # stiffeners are essentially type a stringers, but shorter
                        {Skin('alu', 0.0008, length=average_length): 2,  # top and bottom skin
                         Skin('alu', 0.0008, length=average_length, width=0.15): 2,  # two side skins
                         Skin('alu', 0.0008, length=0.15, width=0.4): 2})  # two ribs

    print('old total WB mass: ', sum([sum([elem.mass * component[elem] for elem in component]) for component in old_config]))
    print('new total WB mass: ', sum([sum([elem.mass * component[elem] for elem in component]) for component in new_config]))


