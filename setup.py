from cx_Freeze import setup, Executable

base = None

executables = [Executable("HandBrake.py", base=base)]

packages = ['idna', 'PySimpleGUI', 'logging', 'logging.config', 'configparser', 'pynput', 'argparse', 'os', 'pandas', 'threading', 'libusb_package', 'usb.core', 'usb.backend.libusb1', 'time']
options = {
    'build_exe': {
        'packages': packages,
    },
}

setup(
    name="Hand Brake",
    options=options,
    version="1.0",
    description='Script para ler a entrada do dispositivo de Freio de Mão na porta USB e retornar o evento de uma tecla apertada',
    executables=executables
)