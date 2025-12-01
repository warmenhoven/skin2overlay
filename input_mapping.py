# Delta to RetroArch input mapping

DELTA_TO_RETROARCH = {
    # Standard buttons
    'a': 'a',
    'b': 'b',
    'x': 'x',
    'y': 'y',
    'l': 'l',
    'r': 'r',
    'start': 'start',
    'select': 'select',
    'menu': 'menu_toggle',

    # N64 specific
    'z': 'l2',
    'cUp': 'r_y_minus',
    'cDown': 'r_y_plus',
    'cLeft': 'r_x_minus',
    'cRight': 'r_x_plus',

    # D-pad directions (used for dpad_area detection)
    'up': 'up',
    'down': 'down',
    'left': 'left',
    'right': 'right',

    # Analog stick directions (used for analog_left detection)
    'analogStickUp': 'l_y_minus',
    'analogStickDown': 'l_y_plus',
    'analogStickLeft': 'l_x_minus',
    'analogStickRight': 'l_x_plus',

    # DS touch (not directly convertible)
    'touchScreenX': None,
    'touchScreenY': None,
}

# Game type identifiers to friendly names
GAME_TYPE_NAMES = {
    'com.rileytestut.delta.game.nes': 'NES',
    'com.rileytestut.delta.game.snes': 'SNES',
    'com.rileytestut.delta.game.n64': 'N64',
    'com.rileytestut.delta.game.gbc': 'GBC',
    'com.rileytestut.delta.game.gba': 'GBA',
    'com.rileytestut.delta.game.ds': 'DS',
    'com.rileytestut.delta.game.genesis': 'Genesis',
}
