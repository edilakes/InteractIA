class Comunicador:
    def __init__(self, callback_hablar=None, callback_finalizar=None):
        self.callback_hablar = callback_hablar
        self.callback_finalizar = callback_finalizar

    def hablar(self, mensaje):
        if self.callback_hablar:
            self.callback_hablar(mensaje)
        else:
            print(f"Agente: {mensaje}")

    def finalizar_habla(self):
        if self.callback_finalizar:
            self.callback_finalizar()
