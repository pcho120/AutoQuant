import sys
from unittest.mock import MagicMock
sys.modules['streamlit'] = MagicMock()
sys.modules['pandas'] = MagicMock()
sys.modules['plotly'] = MagicMock()
sys.modules['plotly.express'] = MagicMock()

from ui.prediction_tab import render_prediction_tab
print("Import successful!")
