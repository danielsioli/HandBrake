import PySimpleGUI as sg
import logging
import logging.config
import configparser
from pynput.keyboard import Key, HotKey, Listener, Controller
import argparse
from os.path import isfile
import pandas as pd
from threading import Thread
import libusb_package
import usb.core
import usb.backend.libusb1
import time

global jogando

class Janela:
    def __init__(self, config_ini, logger_ini):
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
        self.vendor_id = hex(int(self.config['config']['vendor_id'], base=16))
        self.product_id = hex(int(self.config['config']['product_id'], base=16))
        self.interface = int(self.config['config']['interface'])
        self.bytes = int(self.config['config']['bytes'])
        self.zona_morta = int(self.config['config']['zona_morta'])
        self.erro = int(self.config['config']['erro'])

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
                    self.vendor_id = hex(int(values[0], base=16))
                    self.product_id = hex(int(values[1], base=16))
                    self.interface = int(values[2])
                    self.bytes = int(values[3])
                    self.zona_morta = int(values[4])
                    self.erro = int(values[5])
                    self.config['config']['vendor_id'] = str(values[0])
                    self.config['config']['product_id'] = str(values[1])
                    self.config['config']['interface'] = str(values[2])
                    self.config['config']['bytes'] = str(values[3])
                    self.config['config']['zona_morta'] = str(values[4])
                    self.config['config']['erro'] = str(values[5])
                    with open(self.config_ini, 'w', encoding='utf-8-sig') as file:
                        self.config.write(file)
                    jogando = False
                    time.sleep(0.5)
                    self.devices.reset()
                    thread_memoria = Thread(target=self.freio_de_mao)
                    jogando = True
                    thread_memoria.start()
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
            [sg.Text('Botão', size=label_size), sg.InputText(self.botao, readonly=True, key='texto_botao', size=(40, 1)), sg.Button('Trocar', key='botao', size=(6, 1))],
            [sg.Text('Vendor ID', size=label_size), sg.InputText(self.vendor_id, size=input_size)],
            [sg.Text('Product ID', size=label_size), sg.InputText(self.product_id, size=input_size)],
            [sg.Text('Interface', size=label_size), sg.InputText(self.interface, size=input_size)],
            [sg.Text('Bytes', size=label_size), sg.InputText(self.bytes, size=input_size)],
            [sg.Text('Zona Morta', size=label_size), sg.InputText(default_text=self.zona_morta, size=input_size)],
            [sg.Text('Erro', size=label_size), sg.InputText(self.erro, size=input_size)],
            [sg.Text('Leitura', size=label_size), sg.ProgressBar(max_value=255, orientation='h', size=(27.25, 18), border_width=sg.DEFAULT_BORDER_WIDTH, key='freio_de_mao')],
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
        self.devices = usb.core.find(idVendor=int(self.vendor_id, base=16), idProduct=int(self.product_id, base=16), backend=libusb1_backend)
        if self.devices is None:
            jogando = False
            raise ValueError('Freio de Mão não encontrado')
        else:
            endpoint = self.devices[0].interfaces()[self.interface].endpoints()[0]
            interface = self.devices[0].interfaces()[self.interface].bInterfaceNumber
            self.devices.reset()
            self.devices.set_configuration()
            endpoint_address = endpoint.bEndpointAddress
            logging.info(f"Conectado ao dispositivo na Vendor ID: {self.vendor_id}, Product ID: {self.product_id}, Interface {interface}")
            apertado = False
            data = pd.DataFrame()
            logging.info('Escutando o dispositivo')
            teclado = Controller()
            intensidade = 0
            while jogando:
                data_raw = self.devices.read(endpoint_address, self.bytes)
                if data_raw[5] != 0 and intensidade >= data_raw[5] - self.erro and intensidade <= data_raw[5] + self.erro:
                    continue
                intensidade = data_raw[5]
                self.window['freio_de_mao'].update(current_count=intensidade)
                if not apertado and intensidade >= self.zona_morta:
                    teclado.press(self.key)
                    apertado = True
                    self.window['freio_de_mao'].update(bar_color=('#046380', '#E6D3A8'))
                elif apertado and intensidade <= self.zona_morta - self.erro:
                    teclado.release(self.key)
                    apertado = False
                    self.window['freio_de_mao'].update(bar_color=('#046380', '#E6D3A8'))

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
        raise(f'Arquivo de configuração não encontrado em {config_ini}')
    logger_ini = args.logger
    logger_ini = logger_ini if logger_ini else 'logger.ini'
    if not isfile(logger_ini):
        raise(f'Arquivo de configuração não encontrado em {logger_ini}')
    janela = Janela(config_ini, logger_ini)
    janela.iniciar()
