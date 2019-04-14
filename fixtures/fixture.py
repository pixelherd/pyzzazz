class Fixture:
    def __init__(self, config, overlay_handler):
        self.validate_config(config)

        self.name = config.get("name")
        self.location = config.get("location")
        self.palette_name = None
        self.overlay_handler = overlay_handler

    def validate_config(self, config):
        if "name" not in config.keys():
            raise Exception("Fixture: config contains no name")

        if "location" not in config.keys():
            raise Exception("Fixture: config contains no location")

        if "sender" not in config.keys():
            raise Exception("Fixture: config contains no sender")

    def send(self):
        pass

    def register_command(self, command):
        pass

    def receive_command(self, command, value):
        pass

    def update(self, time, palette, smoothness, master_brightness):
        pass