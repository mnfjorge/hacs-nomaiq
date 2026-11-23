"""Contact tests using the installed Home Assistant runtime.

Run with: python -m unittest discover -s tests
"""
import importlib.util
import logging
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
import unittest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

# Load the platform without executing the integration setup or cloud login.
ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "nomaiq"
PACKAGE = "nomaiq_contact_test"
package = ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package
spec = importlib.util.spec_from_file_location(
    f"{PACKAGE}.binary_sensor", ROOT / "binary_sensor.py"
)
platform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(platform)


class ContactTests(unittest.IsolatedAsyncioTestCase):
    def test_boolean_decoding(self):
        for value, expected in [
            (0, False), (1, True), (False, False), (True, True),
            (None, None), (2, None), ("0", None), ("unknown", None),
        ]:
            with self.subTest(value=value):
                self.assertIs(platform.contact_state(value), expected)

    async def test_refresh_missing_data_and_failed_updates(self):
        with TemporaryDirectory() as config_dir:
            hass = HomeAssistant(config_dir)
            coordinator = DataUpdateCoordinator(
                hass, logging.getLogger(__name__), name="contact test",
                config_entry=None,
            )
            device = SimpleNamespace(
                serial_number="test-only", name="Test door",
                oem_model_number="doorwin",
                properties_full={"alarm_status": {"value": 0}},
            )
            coordinator.async_set_updated_data([device])
            sensor = platform.NomaIQContactSensor(coordinator, device)
            self.assertIs(sensor.is_on, False)
            self.assertTrue(sensor.available)

            replacement = SimpleNamespace(**vars(device))
            replacement.properties_full = {"alarm_status": {"value": 1}}
            coordinator.async_set_updated_data([replacement])
            self.assertIs(sensor.is_on, True)

            replacement.properties_full = {}
            self.assertIsNone(sensor.is_on)
            coordinator.async_set_updated_data([])
            self.assertIsNone(sensor.is_on)
            coordinator.async_set_update_error(Exception("simulated failure"))
            self.assertFalse(sensor.available)

            coordinator.async_set_updated_data([
                device, SimpleNamespace(oem_model_number="gdo")
            ])
            entities = []
            await platform.async_setup_entry(
                hass, SimpleNamespace(runtime_data=coordinator),
                lambda items: entities.extend(items),
            )
            self.assertEqual(len(entities), 1)
            self.assertEqual(entities[0].unique_id, "nomaiq_contact_test-only")
