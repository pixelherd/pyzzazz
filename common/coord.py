from common.utils import nonzero
import math


# Disclaimer: this is ugly because we want all the coordinate representations cached at each stage
class Cartesian:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __add__(self, o):
        return Cartesian(self.x + o.x, self.y + o.y, self.z + o.z)

    __radd__ = __add__

    def __iadd__(self, o):
        self.x += o.x
        self.y += o.y
        self.z += o.z
        return self

    def __sub__(self, o):
        return Cartesian(self.x - o.x, self.y - o.y, self.z - o.z)

    __rsub__ = __sub__

    def __isub__(self, o):
        self.x -= o.x
        self.y -= o.y
        self.z -= o.z
        return self

    def __eq__(self, o):
        return self.x == o.x and self.y == o.y and self.z == o.z

    def __iter__(self):
        return iter([self.x, self.y, self.z])

    def __getitem__(self, key):
        return list(self)[key]

    def __str__(self):
        return '[x: {0:g}, y: {1:g}, z:{2:g}]'.format(self.x, self.y, self.z)

    def __repr__(self):
        return 'Cartesian(x: {0:g}, y: {1:g}, z:{2:g})'.format(self.x, self.y, self.z)

    def get_magnitude(self):
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def to_spherical(self):
        r = self.get_magnitude()
        theta = math.atan(self.y / nonzero(self.x))
        phi = math.atan(math.sqrt(self.x ** 2 + self.y ** 2) / nonzero(self.z))

        if self.y < 0:
            phi += math.pi

        if self.x < 0:
            theta += math.pi

        return Spherical(r, theta, phi)

    def to_cylindrical(self):
        r = math.sqrt(self.x**2 + self.y**2)
        theta = math.atan(self.y / nonzero(self.x))
        z = self.z

        if self.x < 0:
            theta += math.pi

        return Cylindrical(r, theta, z)


class Spherical:
    def __init__(self, r, theta, phi):
        self.r = r
        self.theta = theta
        self.phi = phi
        self.epsilon = 0.00001

    def __iter__(self):
        return iter([self.r, self.theta, self.phi])

    def __getitem__(self, key):
        return list(self)[key]

    def __str__(self):
        return '[r: {0:g}, theta: {1:g}, phi:{2:g}]'.format(self.r, self.theta, self.phi)

    def __repr__(self):
        return 'Spherical(r: {0:g}, theta: {1:g}, phi:{2:g})'.format(self.r, self.theta, self.phi)

    def add_angle(self, axis, angle):
        if axis == "phi":
            self.phi += angle

            while self.phi < 0:
                self.phi += 2*math.pi

            self.phi %= (2*math.pi)

        elif axis == "theta":
            self.theta += angle

            while self.theta < 0:
                self.theta += 2*math.pi

            self.theta %= (2*math.pi)

        else:
            raise Exception("unknown axis {}".format(axis))

    def to_cartesian(self):
        x = self.r * math.sin(self.phi % math.pi) * math.cos(self.theta)
        y = self.r * math.sin(self.phi % math.pi) * math.sin(self.theta)
        z = self.r * math.cos(self.phi)

        return Cartesian(x, y, z)

    def to_cylindrical(self):
        return self.to_cartesian().to_cylindrical()


class Cylindrical:
    def __init__(self, r, theta, z):
        self.r = r
        self.theta = theta
        self.z = z

    def __iter__(self):
        return iter([self.r, self.theta, self.z])

    def __getitem__(self, key):
        return list(self)[key]

    def __str__(self):
        return '[r: {0:g}, theta: {1:g}, z:{2:g}]'.format(self.r, self.theta, self.z)

    def __repr__(self):
        return 'Cylindrical(r: {0:g}, theta: {1:g}, z:{2:g})'.format(self.r, self.theta, self.z)

    def to_cartesian(self):
        x = self.r * math.cos(self.theta)
        y = self.r * math.sin(self.theta)
        z = self.z

        return Cartesian(x, y, z)

    def to_spherical(self):
        return self.to_cartesian().to_spherical()


class Coordinate:
    def __init__(self, local_origin=Cartesian(0, 0, 0), local_cartesian=None, local_spherical=None, local_cylindrical=None):
        self._local_origin = local_origin

        if local_cartesian and not local_spherical and not local_cylindrical:
            self._local_cartesian = local_cartesian
            self._local_spherical = self._local_cartesian.to_spherical()
            self._local_cylindrical = self._local_cartesian.to_cylindrical()

        elif local_spherical and not local_cartesian and not local_cylindrical:
            self._local_spherical = local_spherical
            self._local_cartesian = self._local_spherical.to_cartesian()
            self._local_cylindrical = self._local_cartesian.to_cylindrical()

        elif local_cylindrical and not local_cartesian and not local_spherical:
            self._local_cylindrical = local_cylindrical
            self._local_cartesian = self._local_cylindrical.to_cartesian()
            self._local_spherical = self._local_cartesian.to_spherical()
        else:
            raise Exception("Coordinate: must initialise with exactly one of cartesian, spherical, or cylindrical")

        self._global_cartesian = self._local_cartesian + self._local_origin
        self._global_spherical = self._global_cartesian.to_spherical()
        self._global_cylindrical = self._global_cartesian.to_cylindrical()
        self._local_delta = self._local_cartesian.get_magnitude()
        self._global_delta = self._global_cartesian.get_magnitude()

        self.access_dict = {"global":
                                 {"cartesian": self._global_cartesian,
                                  "spherical": self._global_spherical,
                                  "cylindrical": self._global_cylindrical},
                            "local":
                                 {"cartesian": self._local_cartesian,
                                  "spherical": self._local_spherical,
                                  "cylindrical": self._local_cylindrical}}

    def __eq__(self, o):
        return self._global_cartesian == o.to_cartesian()

    def get(self, reference_frame, geometry):
        try:
            return self.access_dict[reference_frame][geometry]
        except KeyError:
            raise Exception("invalid parameters {} {}".format(reference_frame, geometry))

    def set(self, reference_frame, geometry, value):
        try:
            self.access_dict[reference_frame][geometry] = value
            self._update_from("{}_{}".format(reference_frame, geometry))
        except KeyError:
            raise Exception("invalid parameters {} {}".format(reference_frame, geometry))

    def _update_from(self, variable):
        if variable == "global_cartesian":
            self._global_spherical = self._global_cartesian.to_spherical()
            self._global_cylindrical = self._global_cartesian.to_cylindrical()
            self._local_cartesian = self._global_cartesian - self._local_origin
            self._local_spherical = self._local_cartesian.to_spherical()
            self._local_cylindrical = self._local_cartesian.to_cylindrical()
            self._local_delta = self._local_cartesian.get_magnitude()
            self._global_delta = self._global_cartesian.get_magnitude()

        elif variable == "global_spherical":
            self._global_cartesian = self._global_spherical.to_cartesian()
            self._global_cylindrical = self._global_cartesian.to_cylindrical()
            self._local_cartesian = self._global_cartesian - self._local_origin
            self._local_spherical = self._local_cartesian.to_spherical()
            self._local_cylindrical = self._local_cartesian.to_cylindrical()
            self._global_delta = self._global_cartesian.get_magnitude()

        elif variable == "global_cylindrical":
            self._global_cartesian = self._global_cylindrical.to_cartesian()
            self._global_spherical = self._global_cartesian.to_spherical()
            self._local_cartesian = self._global_cartesian - self._local_origin
            self._local_spherical = self._local_cartesian.to_spherical()
            self._local_cylindrical = self._local_cartesian.to_cylindrical()
            self._global_delta = self._global_cartesian.get_magnitude()

        elif variable == "local_cartesian":
            self._local_spherical = self._local_cartesian.to_spherical()
            self._local_cylindrical = self._local_cartesian.to_cylindrical()
            self._global_cartesian = self._local_cartesian + self._local_origin
            self._global_spherical = self._global_cartesian.to_spherical()
            self._global_cylindrical = self._global_cartesian.to_cylindrical()
            self._global_delta = self._global_cartesian.get_magnitude()

        elif variable == "local_spherical":
            self._local_cartesian = self._local_spherical.to_cartesian()
            self._local_cylindrical = self._local_cartesian.to_cylindrical()
            self._global_cartesian = self._local_cartesian + self._local_origin
            self._global_spherical = self._global_cartesian.to_spherical()
            self._global_cylindrical = self._global_cartesian.to_cylindrical()
            self._global_delta = self._global_cartesian.get_magnitude()

        elif variable == "local_cylindrical":
            self._local_cartesian = self._local_cylindrical.to_cartesian()
            self._local_spherical = self._local_cartesian.to_spherical()
            self._global_cartesian = self._local_cartesian + self._local_origin
            self._global_spherical = self._global_cartesian.to_spherical()
            self._global_cylindrical = self._global_cartesian.to_cylindrical()
            self._global_delta = self._global_cartesian.get_magnitude()
        else:
            raise Exception("invalid variables {}".format(variable))

    def rotate(self, axis, reference_frame, angle):
        if reference_frame == "global":
            # must rotate local then global
            self.rotate(axis, "local", angle)

            new_origin = self._local_origin.to_spherical()
            new_origin.add_angle(axis, angle)
            self._local_origin = new_origin.to_cartesian()

            self._global_cartesian = self._local_cartesian + self._local_origin
            self._global_spherical = self._global_cartesian.to_spherical()
            self._global_delta = self._global_cartesian.get_magnitude()

        elif reference_frame == "local":
            self._local_spherical.add_angle(axis, angle)
            self._update_from("local_spherical")

    def add_cartesian(self, o):
        self._local_cartesian += o

        self._local_spherical = self._local_cartesian.to_spherical()
        self._global_cartesian = self._local_cartesian + self._local_origin
        self._global_spherical = self._global_cartesian.to_spherical()
        self._global_delta = self._global_cartesian.get_magnitude()

    def get_delta(self, reference_frame):
        if reference_frame == "global":
            return self._global_delta
        elif reference_frame == "local":
            return self._local_delta
        else:
            raise Exception("unknown reference frame {}".format(reference_frame))

    # changes the local origin and leaves the point static in the LOCAL frame
    def set_local_origin(self, o):
        self._local_origin = o
        self._global_cartesian = self._local_cartesian + self._local_origin
        self._global_spherical = self._global_cartesian.to_spherical()
        self._global_delta = self._global_cartesian.get_magnitude()

    # changes the local origin and leaves the point static in the GLOBAL frame
    def make_relative_to(self, local_origin):
        local_origin_delta = local_origin - self._local_origin
        self._local_cartesian += local_origin_delta
        self._local_spherical = self._local_cartesian.to_spherical()
