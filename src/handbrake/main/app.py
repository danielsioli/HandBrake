import argparse
import configparser
import logging
import logging.config
import time
from os.path import isfile
from threading import Thread

import libusb_package
import usb.backend.libusb1
import usb.core
import usb.util
from pynput.keyboard import HotKey, Key, Listener

from handbrake.utils import PySimpleGUI as sg

global jogando


class Dispositivo:
    def __init__(self, product, manufacturer=None, hid=None):
        self.product = product
        self.manufacturer = manufacturer
        self.hid = hex(hid) if hid else None
        self.id_vendor = ""
        self.id_product = ""
        self.endpoint_address = ""

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
        return (
            self.product
            + " "
            + (str(self.hid) if self.hid else "")
            + " "
            + str(self.endpoint_address)
        )


class Janela:
    def __init__(self, config_ini, logger_ini):
        self.devices = None
        self.intensidade = 0
        self.gráfico_pontos = 200
        self.intervalo_atualização_gráfico = 1 / 30
        self.histórico_intensidade = []
        self.config_ini = config_ini
        self.config = configparser.ConfigParser(allow_no_value=True)
        self.config.read(config_ini, encoding="utf-8-sig")
        self.config.sections()
        logging.config.fileConfig(logger_ini)
        logging.info("Execução Inicializada")
        self.botão = self.config["config"]["botão"]
        try:
            self.key = HotKey.parse(self.botão)[0]
        except Exception:
            self.key = HotKey.parse("<" + self.botão + ">")[0]
        id_vendor = hex(int(self.config["config"]["id_vendor"], base=16))
        id_product = hex(int(self.config["config"]["id_product"], base=16))
        hid = hex(int(self.config["config"]["hid"], base=16))
        endpoint_address = hex(int(self.config["config"]["endpoint_address"], base=16))
        self.zona_morta = int(self.config["config"]["zona_morta"])
        self.erro = int(self.config["config"]["erro"])

        libusb1_backend = usb.backend.libusb1.get_backend(
            find_library=libusb_package.find_library
        )
        devices = usb.core.find(find_all=True, backend=libusb1_backend)
        self.dispositivos = []
        self.dispositivo = Dispositivo(product="Escolha um dispositivo")
        for device in devices:
            for configuration in device.configurations():
                for interface in configuration.interfaces():
                    if interface.bInterfaceClass == 0x3:  # Human Interface Device
                        for endpoint in interface.endpoints():
                            dispositivo = Dispositivo(
                                device.product,
                                device.manufacturer,
                                interface.bInterfaceNumber,
                            )
                            dispositivo.set_id_vendor(device.idVendor)
                            dispositivo.set_id_product(device.idProduct)
                            dispositivo.set_configuration(
                                configuration.bConfigurationValue
                            )
                            dispositivo.set_endpoint_address(endpoint.bEndpointAddress)
                            dispositivo.set_bytes(device.bLength)
                            self.dispositivos.append(dispositivo)
                            if (
                                dispositivo.get_id_vendor() == id_vendor
                                and dispositivo.get_id_product() == id_product
                                and dispositivo.get_hid() == hid
                                and dispositivo.get_endpoint_address()
                                == endpoint_address
                            ):
                                logging.info(
                                    "Dispositivo anterior encontrado: "
                                    f"{dispositivo.get_product()}"
                                )
                                self.dispositivo = dispositivo

    def iniciar(self):
        global jogando
        logging.info(f"Iniciando com o botão: {self.botão}")
        sg.theme("SandyBeach")
        self.window = sg.Window("Hand Break", self.get_layout(), finalize=True)
        thread_memoria = Thread(target=self.freio_de_mão)
        jogando = True
        try:
            thread_memoria.start()
            while True:
                event, values = self.window.read()
                if event == "Parar" or event == sg.WINDOW_CLOSED:
                    logging.info("Usuário clicou em Parar")
                    jogando = False
                    break
                elif event == "-LEITURA_FREIO-":
                    self.atualizar_leitura(values[event])
                elif event == "Salvar Alterações":
                    self.dispositivo = [
                        dispositivo
                        for dispositivo in self.dispositivos
                        if dispositivo == values[0]
                    ][0]
                    self.zona_morta = int(values[1])
                    self.erro = int(values[2])
                    self.config["config"]["id_vendor"] = str(
                        self.dispositivo.get_id_vendor()
                    )
                    self.config["config"]["id_product"] = str(
                        self.dispositivo.get_id_product()
                    )
                    self.config["config"]["hid"] = str(self.dispositivo.get_hid())
                    self.config["config"]["zona_morta"] = str(values[1])
                    self.config["config"]["erro"] = str(values[2])
                    with open(self.config_ini, "w", encoding="utf-8-sig") as file:
                        self.config.write(file)
                    jogando = False
                    time.sleep(0.5)
                    self.devices.reset()
                    thread_memoria = Thread(target=self.freio_de_mão)
                    jogando = True
                    thread_memoria.start()
                    self.window.close()
                    self.window = sg.Window(
                        "Hand Break", self.get_layout(), finalize=True
                    )
                elif event == "botão":
                    self.window["texto_botão"].update("Digite uma Tecla")
                    self.window.refresh()
                    listener = Listener(on_press=self.on_press)
                    listener.start()
                    listener.join()
                    self.config["config"]["botão"] = self.botão
                    self.window["texto_botão"].update(self.botão)
                    self.window.refresh()
                    with open(self.config_ini, "w", encoding="utf-8-sig") as file:
                        self.config.write(file)
                    jogando = False
                    time.sleep(0.5)
                    self.devices.reset()
                    thread_memoria = Thread(target=self.freio_de_mão)
                    jogando = True
                    thread_memoria.start()
                    logging.info(f"Tecla redefinida para {self.botão}")
        finally:
            self.window.close()
            if self.devices:
                self.devices.reset()
                usb.util.dispose_resources(self.devices)

    def get_layout(self):
        # global jogando
        label_size = (17, 1)
        input_size = (50, 1)
        layout = [
            [sg.Text("Configuração do Freio de Mão")],
            [
                sg.Text("Botão", size=label_size),
                sg.InputText(
                    self.botão, readonly=True, key="texto_botao", size=(40, 1)
                ),
                sg.Button("Trocar", key="botao", size=(6, 1)),
            ],
            [
                sg.Text("Dispositivo", size=label_size),
                sg.InputCombo(
                    values=self.dispositivos,
                    default_value=self.dispositivo,
                    size=input_size,
                ),
            ],
            [
                sg.Text("Zona Morta", size=label_size),
                sg.InputText(default_text=self.zona_morta, size=input_size),
            ],
            [
                sg.Text("Erro", size=label_size),
                sg.InputText(self.erro, size=input_size),
            ],
            [
                sg.Text("Leitura", size=label_size),
                sg.InputText(
                    default_text=self.intensidade,
                    size=input_size,
                    key="freio_de_mao_txt",
                ),
            ],
            [
                sg.Text("", size=label_size),
                sg.ProgressBar(
                    max_value=self.zona_morta,
                    orientation="h",
                    size=(27.25 * self.zona_morta / 255, 18),
                    border_width=sg.DEFAULT_BORDER_WIDTH,
                    bar_color=("#F46380", "#E6D3A8"),
                    key="zona_morta",
                    pad=((5, 0), (3, 3)),
                ),
                sg.ProgressBar(
                    max_value=255 - self.zona_morta,
                    orientation="h",
                    size=(27.25 * (1 - self.zona_morta / 255), 18),
                    border_width=sg.DEFAULT_BORDER_WIDTH,
                    bar_color=("#046380", "#E6D3A8"),
                    key="freio_de_mao",
                    pad=((0, 5), (3, 3)),
                ),
            ],
            [
                sg.Text("Gráfico", size=label_size),
                sg.Graph(
                    canvas_size=(500, 160),
                    graph_bottom_left=(0, 0),
                    graph_top_right=(self.gráfico_pontos - 1, 255),
                    background_color="#FFF4D6",
                    key="grafico_freio_de_mao",
                ),
            ],
            [sg.Submit("Salvar Alterações"), sg.Cancel("Parar")],
        ]
        return layout

    def atualizar_leitura(self, intensidade):
        self.intensidade = intensidade
        self.histórico_intensidade.append(intensidade)
        self.histórico_intensidade = self.histórico_intensidade[-self.gráfico_pontos :]

        self.window["freio_de_mao_txt"].update(self.intensidade)
        if self.intensidade <= self.zona_morta:
            self.window["zona_morta"].update(current_count=self.intensidade)
            self.window["freio_de_mao"].update(current_count=0)
        else:
            self.window["zona_morta"].update(current_count=self.zona_morta)
            self.window["freio_de_mao"].update(
                current_count=self.intensidade - self.zona_morta
            )

        gráfico = self.window["grafico_freio_de_mao"]
        gráfico.erase()
        gráfico.draw_line(
            (0, self.zona_morta),
            (self.gráfico_pontos - 1, self.zona_morta),
            color="#F46380",
            width=1,
        )
        for índice, valor in enumerate(self.histórico_intensidade[1:], start=1):
            gráfico.draw_line(
                (índice - 1, self.histórico_intensidade[índice - 1]),
                (índice, valor),
                color="#046380",
                width=2,
            )

    def on_press(self, key):
        if key == Key.esc:
            return False
        try:
            self.botão = key.char
            self.key = HotKey.parse(self.botão)[0]
        except Exception:
            self.botão = key.name
            self.key = HotKey.parse("<" + self.botão + ">")[0]
        return False

    def freio_de_mão(self):
        global jogando
        libusb1_backend = usb.backend.libusb1.get_backend(
            find_library=libusb_package.find_library
        )
        self.devices = usb.core.find(
            idVendor=int(self.dispositivo.get_id_vendor(), base=16),
            idProduct=int(self.dispositivo.get_id_product(), base=16),
            backend=libusb1_backend,
        )
        if self.devices is None:
            jogando = False
            return
        else:
            self.devices.reset()
            self.devices.set_configuration()
            endpoint_address = int(self.dispositivo.get_endpoint_address(), base=16)
            bytes = int(self.dispositivo.get_bytes(), base=16)
            interface = self.dispositivo.get_hid()
            logging.info(
                f"Conectado ao dispositivo {self.dispositivo.get_product()}"
                f", Interface {interface}"
            )
            logging.info("Escutando o dispositivo")
            self.intensidade = 0
            # output = []
            próxima_atualização_gráfico = 0
            while jogando:
                # try:
                data_raw = self.devices.read(endpoint_address, bytes)
                # output.append(";".join([str(d) for d in data_raw]))
                intensidade = data_raw[-1]
                agora = time.perf_counter()
                if agora >= próxima_atualização_gráfico:
                    self.window.write_event_value("-LEITURA_FREIO-", intensidade)
                    próxima_atualização_gráfico = (
                        agora + self.intervalo_atualização_gráfico
                    )
            # with open("output.csv", "w") as f:
            #     f.write("\n".join(output))


if __name__ == "__main__":
    # global jogando
    jogando = True
    parser = argparse.ArgumentParser("Hand Brake")
    parser.add_argument("-config", help="O arquivo de configuração", type=str)
    parser.add_argument(
        "-logger", help="O arquivo de configuração para o logs", type=str
    )
    args = parser.parse_args()
    config_ini = args.config
    config_ini = config_ini if config_ini else "config/config.ini"
    if not isfile(config_ini):
        raise Exception(f"Arquivo de configuração não encontrado em {config_ini}")
    logger_ini = args.logger
    logger_ini = logger_ini if logger_ini else "config/logger.ini"
    if not isfile(logger_ini):
        raise Exception(f"Arquivo de configuração não encontrado em {logger_ini}")
    janela = Janela(config_ini, logger_ini)
    janela.iniciar()
