from overlays.overlay import Overlay
from common.utils import nonzero
from common.colour import channelwise_max
from common.colour import Colour


class Flash(Overlay):
    def __init__(self, args):
        self.decay_factor = args["decay_factor"]

    def get_overlaid_colour(self, colour, led, time_since_start):
        factor = min(1.0, 1.0 / nonzero((time_since_start + 0.5) * self.decay_factor))
        flash_colour = Colour(*(channel * factor * 2 for channel in led.colour))

        return channelwise_max(led.colour, flash_colour)
