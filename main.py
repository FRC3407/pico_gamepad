import board
import analogio
import digitalio
import usb_hid
import time
from hid_gamepad import Gamepad


class GamepadControl:
    def process(self, gp, logger):
        pass


class GamepadButton(GamepadControl):
    "Represents a gamepad button, and its corresponding hardware pin."

    def __init__(self, button_num: int, pin: int, button_name: str = None):
        if button_num < 1 or button_num > 16:
            raise ValueError("button_num must be a number 1 through 16")
        self.button_num = button_num
        self.pin = pin
        self.button_name = button_name
        self.dio = digitalio.DigitalInOut(pin)
        self.dio.direction = digitalio.Direction.INPUT
        self.dio.pull = digitalio.Pull.UP

    def is_pressed(self) -> bool:
        return not self.dio.value

    def process(self, gp, logger):
        if self.is_pressed():
            gp.press_buttons(self.button_num)
            if logger is not None:
                logger.add(self)
        else:
            gp.release_buttons(self.button_num)
            if logger is not None:
                logger.remove(self)

    def __repr__(self) -> str:
        label =  f",'{self.button_name}'" if self.button_name is not None else ""
        return f"GamepadButton({self.button_num},{self.pin}{label})"


class GamepadDial(GamepadControl):
    "Represents a gamepad potentiometer, and its corresponding hardware pin."
    def __init__(self, dial_num: int, pin: int, dial_name: str = None, min_value: int = 0, max_value: int = 65535):
        if dial_num < 0 or dial_num > 3:
            raise ValueError("dial_num must be a number 0 through 3")  
        if min_value >= max_value:
            raise ValueError("min_value must be less than max_value")
        self.dial_num = dial_num
        self.pin = pin
        self.dial_name = dial_name
        self.min_value = min_value
        self.max_value = max_value
        self.aio = analogio.AnalogIn(pin)
        self.prev_value = -255
        self.deadband = 5  # Deadband range for joystick movement
    
    def process(self, gp, logger):
        dial_value = self.aio.value
        joystick_value = int((dial_value - self.min_value) / (self.max_value - self.min_value) * 256) - 127
        joystick_value = max(-127, min(127, joystick_value))
        label = "a"
        if abs(joystick_value - self.prev_value) > self.deadband:
            if self.dial_num == 0:
                gp.move_joysticks(x=joystick_value)
                label = "x"
            elif self.dial_num == 1:
                gp.move_joysticks(y=joystick_value)
                label = "y"
            elif self.dial_num == 2:
                gp.move_joysticks(z=joystick_value)
                label = "z"
            elif self.dial_num == 3:
                gp.move_joysticks(r_z=joystick_value)
                label = "r_z"
            self.prev_value = joystick_value
            if logger is not None:
                logger.log(f"{label}={joystick_value}", self)

    def __repr__(self) -> str:
        dial_label =  f",'{self.dial_name}'" if self.dial_name is not None else ""
        return f"GamepadDial({self.dial_num},{self.pin}{dial_label})"


led = digitalio.DigitalInOut(board.LED)
led.direction = digitalio.Direction.OUTPUT


class Logger:
    """
    Tracks the buttons that are currently pressed.
    This class exists primarily for debugging and monitoring.
    Yes, it's kind of overcomplicated for what it does.
    """

    def __init__(self):
        self.buttons_set: set[int] = set()

    def add(self, button: GamepadButton):
        if button.button_num not in self.buttons_set:
            self.log("press  ", button)
        self.buttons_set.add(button.button_num)

    def remove(self, button: GamepadButton):
        if button.button_num in self.buttons_set:
            self.log("release", button)
            self.buttons_set.remove(button.button_num)

    def log(self, action: str, control: GamepadControl):
        global led
        print(f" {action} {control}", end="\n")
        led.value = len(self.buttons_set) == 0
    
    def __repr__(self) -> str:
        return f"Logger({self.buttons_set})"


gp = Gamepad(usb_hid.devices)

control_list = [
    GamepadButton(1, board.GP9),
    GamepadButton(2, board.GP10),
    GamepadButton(3, board.GP22),
    GamepadButton(4, board.GP21),
]
logger = Logger()


while True:
    for control in control_list:
        control.process(gp, logger)
    time.sleep(0.010)  # Small delay to avoid overwhelming the USB HID interface
