VALID_MOVEMENTS = {
    "forward",
    "backward",
    "left",
    "right",
    "stop"
}

VALID_SPEEDS = {
    "low",
    "medium",
    "high"
}

VALID_MODES = {
    "manual",
    "autonomous"
}


def validate_command(command):

    if not isinstance(command, dict):
        return False, "Command must be an object"

    movement = command.get("movement")
    speed = command.get("speed")
    mode = command.get("mode")

    if movement not in VALID_MOVEMENTS:
        return False, f"Invalid movement: {movement}"

    if speed not in VALID_SPEEDS:
        return False, f"Invalid speed: {speed}"

    if mode not in VALID_MODES:
        return False, f"Invalid mode: {mode}"

    return True, "Command is valid"


MOVEMENT_COMMANDS = {
    "forward": "FORWARD",
    "backward": "BACKWARD",
    "left": "LEFT",
    "right": "RIGHT",
    "stop": "STOP"
}

def process_command(command):

    is_valid, message = validate_command(command)

    if not is_valid:
        return {
            "accepted": False,
            "message": message
        }

    movement = command["movement"]
    speed = command["speed"]
    mode = command["mode"]

    if mode == "autonomous":

        return {
            "accepted": True,
            "mode": "autonomous",
            "movement": "stop",
            "speed": speed,
            "message": "Autonomous mode active"
        }

    speed_values = {
        "low": 0.25,
        "medium": 0.50,
        "high": 1.00
    }

    speed_value = speed_values[speed]
    movement_action = MOVEMENT_COMMANDS[movement]

    return {
    "accepted": True,
    "mode": "manual",
    "movement": movement,
    "movement_action": movement_action,
    "speed": speed,
    "speed_value": speed_value,
    "message": "Manual command accepted"
}