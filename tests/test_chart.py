import importlib
import os
import pytest


def test_dashboard_folder_exists():
    assert os.path.isdir('dashboard'), 'dashboard/ folder must exist'


def test_dashboard_app_importable():
    mod = importlib.import_module('dashboard.app')
    assert mod is not None


def test_dashboard_layout_importable():
    mod = importlib.import_module('dashboard.layout')
    assert mod is not None


def test_dashboard_charts_importable():
    mod = importlib.import_module('dashboard.charts')
    assert mod is not None


def test_dashboard_overlays_importable():
    mod = importlib.import_module('dashboard.overlays')
    assert mod is not None


def test_dashboard_callbacks_importable():
    mod = importlib.import_module('dashboard.callbacks')
    assert mod is not None
