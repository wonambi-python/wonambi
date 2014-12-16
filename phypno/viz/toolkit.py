def toolkit(toolkit='visvis', memo={}):
    """Let the user decide if they want to use visvis (stable) or vispy
    (experimental).

    Notes
    -----
    It relies on Python behavior of treating functions as objects. It might
    need to be more flexible in the future for different toolkit as well.
    """
    if 'viz' not in memo:
        memo['viz'] = toolkit

    return memo['viz']
