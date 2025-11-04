import unittest
from unittest.mock import MagicMock, patch
import logging
import sys
import os
import json

# Add the project directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from agente import Agente
from controlador import Controlador

# Configure logging for the test
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestAgenteActions")

class TestAgenteActions(unittest.TestCase):

    def setUp(self):
        # Mock the ModelProvider
        self.mock_model_provider = MagicMock()
        self.mock_model_provider.set_model.return_value = None
        self.mock_model_provider.generate_content.return_value = {"text": f"""```json
{json.dumps({'pensamiento': 'Voy a hacer scroll hacia abajo.', 'accion': 'scroll', 'params': {'direccion': 'abajo', 'clics': 5}})}
```"""}

        # Mock the Comunicador to prevent actual speech/finalization
        self.mock_comunicador = MagicMock()

        # Mock the Vision to prevent actual screen captures
        self.mock_vision = MagicMock()
        self.mock_vision.capturar_entorno.return_value = "mock_capture_data"
        self.mock_vision.leer_texto_en_pantalla.return_value = [{"texto": "Some text on screen"}]

        # Mock the Controlador to prevent actual pyautogui calls
        self.mock_controlador = MagicMock(spec=Controlador)
        # Patch the Controlador class itself to return our mock instance
        self.patcher_controlador = patch('agente.Controlador', return_value=self.mock_controlador)
        self.patcher_controlador.start()

        # Mock MongoDBChatMemory
        self.mock_memoria = MagicMock()
        self.mock_memoria.operativo = True
        self.mock_memoria._recuperar_historial_crudo.return_value = []
        self.mock_memoria.convertir_historial_a_formato_simple.return_value = []
        self.mock_memoria.guardar_mensaje.return_value = None

        self.patcher_memoria = patch('agente.MongoDBChatMemory', return_value=self.mock_memoria)
        self.patcher_memoria.start()

        # Instantiate Agente with mocks
        self.agente = Agente(
            model_provider=self.mock_model_provider,
            model_name="mock_model",
            callback_hablar=self.mock_comunicador.hablar,
            callback_finalizar=self.mock_comunicador.finalizar,
            callback_log=self.mock_comunicador.log
        )
        self.agente.operativo = True # Ensure agent is marked as operative for testing
        self.agente.comunicador = self.mock_comunicador # Assign the mock comunicador
        self.agente.vision = self.mock_vision # Assign the mock vision
        self.agente.controlador = self.mock_controlador # Assign the mock controlador

        # Reset mock calls before each test
        self.mock_model_provider.generate_content.reset_mock()

    def tearDown(self):
        self.patcher_controlador.stop()
        self.patcher_memoria.stop()

    def test_scroll_action_down(self):
        logger.info("Running test_scroll_action_down")
        self.agente.establecer_objetivo("Hacer scroll hacia abajo")
        self.agente.stream_run()

        # Verify that generate_content was called
        self.mock_model_provider.generate_content.assert_called_once()

        # Verify that controlador.scroll was called with a negative value
        self.mock_controlador.scroll.assert_called_once_with(-5)
        logger.info("test_scroll_action_down completed successfully")

    def test_scroll_action_up(self):
        logger.info("Running test_scroll_action_up")
        # Reset mock for this test
        self.mock_model_provider.generate_content.return_value = {"text": f"""```json
{json.dumps({'pensamiento': 'Voy a hacer scroll hacia arriba.', 'accion': 'scroll', 'params': {'direccion': 'arriba', 'clics': 10}})}
```"""}
        self.agente.establecer_objetivo("Hacer scroll hacia arriba")
        self.agente.stream_run()

        # Verify that controlador.scroll was called with a positive value
        self.mock_controlador.scroll.assert_called_with(10)
        logger.info("test_scroll_action_up completed successfully")

    def test_no_arrastrar_barra_action(self):
        logger.info("Running test_no_arrastrar_barra_action")
        # Ensure the prompt does not contain 'arrastrar_barra'
        prompt = self.agente._construir_prompt(resumen_memoria="some memory")
        self.assertNotIn("arrastrar_barra", prompt)
        logger.info("test_no_arrastrar_barra_action completed successfully")

if __name__ == '__main__':
    unittest.main()