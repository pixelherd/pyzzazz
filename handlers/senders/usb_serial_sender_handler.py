from handlers.senders.sender_handler import SenderHandler
from handlers.packet_handler import CommHeader


class UsbSerialSenderHandler(SenderHandler):
    def __init__(self, config, serial_handler):
        SenderHandler.__init__(self, config)
        self.validate_config(config)
        self.num_lines = config.get("num_lines", "")
        self._serial_handler = serial_handler

        self._last_send = [0.0 for _ in range(self.num_lines)]
        self._send_interval = 1.0 / 30.0 / 8

    def validate_config(self, config):
        if "num_lines" not in config.keys():
            raise Exception("Sender: config contains no num_lines")

    def is_connected(self):
        return self._serial_handler.is_connected(self.name)

    def send(self, line, byte_values):
        if not len(byte_values):
            return

        byte_values = list(byte_values)
        while len(byte_values) % 3:
            byte_values.append(0)

        if line > self.num_lines - 1 or line < 0:
            raise Exception("Sender: send called on invalid line {}".format(line))

        # if not connected, drop frame
        if self.is_connected():
            if ord('~') in byte_values:
                print("BAD")

            if ord('|') in byte_values:
                print("BaaAD")

            # packet = [ord('~'), line, len(byte_values)/3]
            header = [ord('~'), CommHeader.ops_by_str["frame_update"], line]
            footer = [ord('|')]

            # header[-1:] = byte_values
            # header[-1:] = footer

            self._serial_handler.send_bytes(self.name, header + byte_values + footer)

    def encapsulate(self, line, payload):
        header = [ord('~'), line]
        footer = [ord('|')]

        # avoid sentinel value
        for char in payload:
            if char == header[0] or char == footer[0]:
                char += 1

        return bytearray(header + payload + footer)
