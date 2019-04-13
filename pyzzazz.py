from common.configparser import ConfigParser
from senders.usb_serial_sender_handler import UsbSerialSenderHandler
from controllers.gui_controller_handler import GuiControllerHandler
from controllers.usb_serial_controller_handler import UsbSerialControllerHandler
from senders.opc_sender_handler import OpcSenderHandler
from common.palette import Palette
from common.socket_server import SocketServer
from fixtures.dodecahedron import Dodecahedron
import signal
import time
import re
import traceback
from pathlib import Path

start_pattern = "make_me_one_with_everything"
default_port = 48945


class Pyzzazz:
    def __init__(self, conf_path, palette_path):
        self._src_dir = Path(__file__).parent
        self.config_parser = ConfigParser(conf_path)
        self.palette = Palette(palette_path)
        self.speed = 1.0
        self.effective_time = 0.0
        self.last_update = time.time()
        self.subprocesses = list()

        self.senders = []
        self.fixtures = []
        self.controllers = []

        self.socket_server = SocketServer(port=default_port)
        # TODO multiple palettes, pass dict to fixtures
        # TODO add target type for commands (fixtures, master, etc)
        # TODO modulators? overlays?
        # TODO set from image/video
        # TODO video players should be a different type

        # these must be done in this order
        self.init_senders()
        self.init_fixtures()
        self.init_controllers()
        self.generate_opc_layout_files()

        # FIXME how to do startup command?
        for fixture in self.fixtures:
            command = {'type': 'pattern', 'name': start_pattern, 'args': {}}
            # command = {'type': 'pattern', 'name': 'make_me_one_with_everything', 'args': {}}
            fixture.register_command(command)
            fixture.receive_command(command, 1)

    def update(self):
        self.socket_server.poll()

        self.effective_time += (time.time() - self.last_update) * self.speed
        self.last_update = time.time()

        for controller in self.controllers:
            if not controller.is_connected():
                controller.try_connect()

            if controller.is_connected():
                controller.update()

                events = controller.get_events()
                for event in events:
                    matching_fixtures = list(fixture for fixture in self.fixtures if re.search(event.target_regex, fixture.name))

                    for fixture in matching_fixtures:
                        fixture.receive_command(event.command, event.value)

        smoothness = 0.5

        for sender in self.senders:
            if not sender.is_connected():
                sender.try_connect()

        for fixture in self.fixtures:
            fixture.update(self.effective_time, self.palette, smoothness)
            fixture.send()

    def init_senders(self):
        for sender_conf in self.config_parser.get_senders():
            # check for duplicate names
            self.sanity_check_sender_conf(sender_conf)

            if sender_conf.get("type", "") == "usb_serial":
                print("Creating usb serial sender {} on port {}".format(sender_conf.get("name", ""), sender_conf.get("port", "")))
                self.senders.append(UsbSerialSenderHandler(sender_conf))

            elif sender_conf.get("type", "") == "opc":
                print("Creating opc sender {} on port {}".format(sender_conf.get("name", ""), sender_conf.get("port", "")))
                self.senders.append(OpcSenderHandler(sender_conf, self._src_dir))

            else:
                raise Exception("Unknown sender type {}".format(sender_conf.get("type", "")))

        print("\n")

    def init_fixtures(self):
        for fixture_conf in self.config_parser.get_fixtures():
            self.sanity_check_fixture_conf(fixture_conf)

            if fixture_conf.get("geometry", "") == "dodecahedron":
                print("Creating dodecahedron {} with senders {}".format(fixture_conf.get("name", ""), fixture_conf.get("senders", [])))
                fixture_senders = list(sender for sender in self.senders if sender.name in fixture_conf.get("senders", []))
                self.fixtures.append(Dodecahedron(fixture_conf, fixture_senders))

            else:
                raise Exception("Unknown fixture type {}".format(fixture_conf.get("type", "")))

        print("\n")

    def init_controllers(self):
        for controller_conf in self.config_parser.get_controllers():
            # check for duplicate names
            self.sanity_check_controller_conf(controller_conf)

            if controller_conf.get("type", "") == "usb_serial":
                print("Creating usb serial controller {} on port {}".format(controller_conf.get("name", ""), controller_conf.get("port", "")))
                self.controllers.append(UsbSerialControllerHandler(controller_conf))

            elif controller_conf.get("type", "") == "gui":
                print("Creating gui controller {} on port {}".format(controller_conf.get("name", ""), controller_conf.get("port", "")))
                self.controllers.append(GuiControllerHandler(controller_conf, self.socket_server))

            else:
                raise Exception("Unknown controller type {}".format(controller_conf.get("type", "")))

            for control in self.controllers[-1].get_controls():
                matching_fixtures = list(fixture for fixture in self.fixtures if re.search(control.target_regex, fixture.name))

                for fixture in matching_fixtures:
                    fixture.register_command(control.command)

        print("\n")

    def generate_opc_layout_files(self):
        for sender in self.senders:
            if sender.type == "opc":
                sender.generate_layout_files(self.fixtures)
                self.subprocesses.append(sender.start())

    def sanity_check_sender_conf(self, sender_conf):
        sender_names = tuple(sender.name for sender in self.senders)
        if sender_conf.get("name", "") in sender_names:
            raise Exception("Pyzzazz: config specifies one or more senders with identical name {}".format(sender_conf.get("name", "")))

        # check for duplicate ports
        sender_ports = tuple(sender.port for sender in self.senders)
        if sender_conf.get("port", "") in sender_ports:
            raise Exception("Pyzzazz: config specifies one or more senders with identical port {}".format(sender_conf.get("port", "")))

    def sanity_check_fixture_conf(self, fixture_conf):
        # check for duplicate names
        for fixture in self.fixtures:
            if fixture_conf.get("name", "") == fixture.name:
                raise Exception("Pyzzazz: config specifies one or more fixtures with identical name {}".format(fixture_conf.get("name", "")))

            for sender_name in fixture_conf.get("senders", []):
                if fixture.has_sender(sender_name) and fixture_conf.get("line", "") == fixture.line:
                    raise Exception("Pyzzazz: config specifies one or more fixtures with identical senders {} and lines {}".format(sender_name, fixture_conf.get("line", "")))

        # check sender exists
        for sender_name in fixture_conf.get("senders", []):
            if sender_name not in list(sender.name for sender in self.senders):
                raise Exception("Pyzzazz: Fixture {} specified with undefined sender {}".format(fixture_conf.get("name", ""), sender_name))

    def sanity_check_controller_conf(self, controller_conf):
        pass
        #FIXME do this

    def shut_down(self):
        print("Shutting down...")
        for p in self.subprocesses:
            p.kill()


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        print("SIGKILL received")
        self.kill_now = True


if __name__ == "__main__":
    killer = GracefulKiller()

    pyzzazz = None

    try:
        print("Initialising...")
        # FIXME backup last used conf
        # FIXME check for conf on usb stick
        # FIXME multiple palettes
        # FIXME grab palettes off usb stick
        pyzzazz = Pyzzazz("conf/conf.json", "conf/auto.bmp")

        print("Running...")
        while True:
            pyzzazz.update()

            if killer.kill_now:
                if pyzzazz:
                    pyzzazz.shut_down()

                break

    except Exception as e:
        # FIXME output to file, print to screen if we're doing that?
        traceback.print_exc()

    finally:
        pyzzazz.shut_down()

    print("have a nice day :)")
