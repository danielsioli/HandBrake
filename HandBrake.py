import PySimpleGUI as sg
import logging
import logging.config
import configparser
from pynput.keyboard import Key, HotKey, Listener, Controller
import argparse
from os.path import isfile
from threading import Thread
import libusb_package
import usb.core
import usb.util
import usb.backend.libusb1
import time

global jogando


class Dispositivo:

    def __init__(self, product, manufacturer=None, hid=None):
        self.product = product
        self.manufacturer = manufacturer
        self.hid = hex(hid) if hid else None
        self.id_vendor = ''
        self.id_product = ''
        self.endpoint_address = ''

    def set_manufacturer(self, manufacturer):
        self.manufacturer = manufacturer

    def get_manufacturer(self):
        return self.manufacturer

    def set_product(self, product):
        self.product = product

    def get_product(self):
        return self.product

    def set_id_vendor(self, id_vendor):
        self.id_vendor = hex(id_vendor)

    def get_id_vendor(self):
        return self.id_vendor

    def set_id_product(self, id_product):
        self.id_product = hex(id_product)

    def get_id_product(self):
        return self.id_product

    def set_configuration(self, configuration):
        self.configuration = hex(configuration)

    def get_configuration(self):
        return self.configuration

    def set_hid(self, hid):
        self.hid = hex(hid)

    def get_hid(self):
        return self.hid

    def set_endpoint_address(self, endpoint_address):
        self.endpoint_address = hex(endpoint_address)

    def get_endpoint_address(self):
        return self.endpoint_address

    def set_bytes(self, bytes):
        self.bytes = hex(bytes)

    def get_bytes(self):
        return self.bytes

    def __str__(self):
        return self.product + ' ' + (str(self.hid) if self.hid else '') + ' ' + str(self.endpoint_address)


class Janela:
    def __init__(self, config_ini, logger_ini):
        self.devices = None
        self.config_ini = config_ini
        self.config = configparser.ConfigParser(allow_no_value=True)
        self.config.read(config_ini, encoding='utf-8-sig')
        self.config.sections()
        logging.config.fileConfig(logger_ini)
        logging.info('Execução Inicializada')
        self.botao = self.config['config']['botao']
        try:
            self.key = HotKey.parse(self.botao)[0]
        except:
            self.key = HotKey.parse('<' + self.botao + '>')[0]
        id_vendor = hex(int(self.config['config']['id_vendor'], base=16))
        id_product = hex(int(self.config['config']['id_product'], base=16))
        hid = hex(int(self.config['config']['hid'], base=16))
        endpoint_address = hex(int(self.config['config']['endpoint_address'], base=16))
        self.zona_morta = int(self.config['config']['zona_morta'])
        self.erro = int(self.config['config']['erro'])

        libusb1_backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
        devices = usb.core.find(find_all=True, backend=libusb1_backend)
        self.dispositivos = []
        self.dispositivo = Dispositivo(product='Escolha um dispositivo')
        for device in devices:
            for configuration in device.configurations():
                for interface in configuration.interfaces():
                    if interface.bInterfaceClass == 0x3:  # Human Interface Device
                        for endpoint in interface.endpoints():
                            dispositivo = Dispositivo(device.product, device.manufacturer, interface.bInterfaceNumber)
                            dispositivo.set_id_vendor(device.idVendor)
                            dispositivo.set_id_product(device.idProduct)
                            dispositivo.set_configuration(configuration.bConfigurationValue)
                            dispositivo.set_endpoint_address(endpoint.bEndpointAddress)
                            dispositivo.set_bytes(device.bLength)
                            self.dispositivos.append(dispositivo)
                            if dispositivo.get_id_vendor() == id_vendor and dispositivo.get_id_product() == id_product \
                                    and dispositivo.get_hid() == hid \
                                    and dispositivo.get_endpoint_address() == endpoint_address:
                                logging.info(f'Dispositivo anterior encontrado: {dispositivo.get_product()}')
                                self.dispositivo = dispositivo

    def iniciar(self):
        global jogando
        logging.info(f'Iniciando com o botão: {self.botao}')
        sg.theme('SandyBeach')
        self.window = sg.Window('Hand Break', self.get_layout(), finalize=True)
        thread_memoria = Thread(target=self.freio_de_mao)
        jogando = True
        try:
            thread_memoria.start()
            while True:
                event, values = self.window.read()
                if event == 'Parar' or event == sg.WINDOW_CLOSED:
                    logging.info('Usuário clicou em Parar')
                    jogando = False
                    break
                elif event == 'Salvar Alterações':
                    self.dispositivo = [dispositivo for dispositivo in self.dispositivos if dispositivo == values[0]][0]
                    self.zona_morta = int(values[1])
                    self.erro = int(values[2])
                    self.config['config']['id_vendor'] = str(self.dispositivo.get_id_vendor())
                    self.config['config']['id_product'] = str(self.dispositivo.get_id_product())
                    self.config['config']['hid  '] = str(self.dispositivo.get_hid())
                    self.config['config']['zona_morta'] = str(values[1])
                    self.config['config']['erro'] = str(values[2])
                    with open(self.config_ini, 'w', encoding='utf-8-sig') as file:
                        self.config.write(file)
                    jogando = False
                    time.sleep(0.5)
                    self.devices.reset()
                    thread_memoria = Thread(target=self.freio_de_mao)
                    jogando = True
                    thread_memoria.start()
                    self.window.close()
                    self.window = sg.Window('Hand Break', self.get_layout(), finalize=True)
                elif event == 'botao':
                    self.window['texto_botao'].update('Digite uma Tecla')
                    self.window.refresh()
                    listener = Listener(on_press=self.on_press)
                    listener.start()
                    listener.join()
                    self.config['config']['botao'] = self.botao
                    self.window['texto_botao'].update(self.botao)
                    self.window.refresh()
                    with open(self.config_ini, 'w', encoding='utf-8-sig') as file:
                        self.config.write(file)
                    jogando = False
                    time.sleep(0.5)
                    self.devices.reset()
                    thread_memoria = Thread(target=self.freio_de_mao)
                    jogando = True
                    thread_memoria.start()
                    logging.info(f'Tecla redefinida para {self.botao}')
        finally:
            self.window.close()
            if self.devices:
                self.devices.reset()
                usb.util.dispose_resources(self.devices)

    def get_layout(self):
        global jogando
        label_size = (17, 1)
        input_size = (50, 1)
        layout = [
            [sg.Text('Configuração do Freio de Mão')],
            [sg.Text('Botão', size=label_size),
             sg.InputText(self.botao, readonly=True, key='texto_botao', size=(40, 1)),
             sg.Button('Trocar', key='botao', size=(6, 1))],
            [sg.Text('Dispositivo', size=label_size),
             sg.InputCombo(values=self.dispositivos, default_value=self.dispositivo, size=input_size)],
            [sg.Text('Zona Morta', size=label_size), sg.InputText(default_text=self.zona_morta, size=input_size)],
            [sg.Text('Erro', size=label_size), sg.InputText(self.erro, size=input_size)],
            [sg.Text('Leitura', size=label_size),
             sg.ProgressBar(max_value=self.zona_morta, orientation='h', size=(27.25 * self.zona_morta / 255, 18),
                            border_width=sg.DEFAULT_BORDER_WIDTH, bar_color=('#F46380', '#E6D3A8'), key='zona_morta',
                            pad=((5, 0), (3, 3))), sg.ProgressBar(max_value=255 - self.zona_morta, orientation='h',
                                                                  size=(27.25 * (1 - self.zona_morta / 255), 18),
                                                                  border_width=sg.DEFAULT_BORDER_WIDTH,
                                                                  bar_color=('#046380', '#E6D3A8'), key='freio_de_mao',
                                                                  pad=((0, 5), (3, 3)))],
            [sg.Submit('Salvar Alterações'), sg.Cancel('Parar')]
        ]
        return layout

    def on_press(self, key):
        if key == Key.esc:
            return False
        try:
            self.botao = key.char
            self.key = HotKey.parse(self.botao)[0]
        except:
            self.botao = key.name
            self.key = HotKey.parse('<' + self.botao + '>')[0]
        return False

    def freio_de_mao(self):
        global jogando
        libusb1_backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
        self.devices = usb.core.find(idVendor=int(self.dispositivo.get_id_vendor(), base=16),
                                     idProduct=int(self.dispositivo.get_id_product(), base=16), backend=libusb1_backend)
        if self.devices is None:
            jogando = False
            return
        else:
            self.devices.reset()
            self.devices.set_configuration()
            endpoint_address = int(self.dispositivo.get_endpoint_address(), base=16)
            bytes = int(self.dispositivo.get_bytes(), base=16)
            interface = self.dispositivo.get_hid()
            logging.info(f"Conectado ao dispositivo {self.dispositivo.get_product()}, Interface {interface}")
            apertado = False
            logging.info('Escutando o dispositivo')
            teclado = Controller()
            intensidade = 0
            while jogando:
                try:
                    data_raw = self.devices.read(endpoint_address, bytes)
                except:
                    continue
                if data_raw[5] != 0 and data_raw[5] - self.erro <= intensidade <= data_raw[5] + self.erro:
                    continue
                intensidade = data_raw[5]
                if intensidade <= self.zona_morta:
                    self.window['zona_morta'].update(current_count=intensidade)
                    self.window['freio_de_mao'].update(current_count=0)
                else:
                    self.window['zona_morta'].update(current_count=self.zona_morta)
                    self.window['freio_de_mao'].update(current_count=intensidade - self.zona_morta)
                if not apertado and intensidade >= self.zona_morta:
                    teclado.press(self.key)
                    apertado = True
                elif apertado and intensidade <= self.zona_morta - self.erro:
                    teclado.release(self.key)
                    apertado = False


if __name__ == '__main__':
    global jogando
    jogando = True
    parser = argparse.ArgumentParser("Hand Brake")
    parser.add_argument("-config", help="O arquivo de configuração", type=str)
    parser.add_argument("-logger", help="O arquivo de configuração para o logs", type=str)
    args = parser.parse_args()
    config_ini = args.config
    config_ini = config_ini if config_ini else 'config.ini'
    if not isfile(config_ini):
        raise f'Arquivo de configuração não encontrado em {config_ini}'
    logger_ini = args.logger
    logger_ini = logger_ini if logger_ini else 'logger.ini'
    if not isfile(logger_ini):
        raise f'Arquivo de configuração não encontrado em {logger_ini}'
    janela = Janela(config_ini, logger_ini)
    janela.iniciar()
