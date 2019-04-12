from pattern import Pattern
import math


class Smooth(Pattern):
    def __init__(self):
        self._time_divisor = 50
        self._space_divisor = 1

    def update(self, leds, time, palette):
        return

    def get_pixel_colour(self, pixels, index, time, palette):
        space_delta = pixels[index].coord.get_delta("global")

        offset_space_component = pixels[index].coord.get("global", "spherical").theta * 3
        offset_time_component = time
        offset = math.sin(offset_space_component + offset_time_component)
        offset /= 4
        space_delta += offset

        return palette.sample_radial(space_delta, time, self._space_divisor, self._time_divisor)

