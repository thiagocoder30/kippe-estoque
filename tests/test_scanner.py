from unittest.mock import patch, MagicMock
from src.interfaces.termux_scanner import TermuxBarcodeScanner

@patch('subprocess.run')
def test_termux_scanner_success(mock_run):
    # Mock do retorno da câmera
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "7891020304050\n"
    mock_run.return_value = mock_result
    
    scanner = TermuxBarcodeScanner()
    res = scanner.scan()
    
    assert res.is_success is True
    assert res.value == "7891020304050"

@patch('subprocess.run')
def test_termux_scanner_empty(mock_run):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_run.return_value = mock_result
    
    scanner = TermuxBarcodeScanner()
    res = scanner.scan()
    
    assert res.is_success is False
    assert "cancelada" in res.error
