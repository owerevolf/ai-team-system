"""Тесты для learning_mode.py"""

import json
import tempfile
from pathlib import Path

import pytest

from core.learning_mode import LearningMode, LearningProgress


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path / "learning"


@pytest.fixture
def lm(data_dir):
    return LearningMode(data_dir=data_dir)


def test_initial_progress(lm):
    report = lm.get_progress_report()
    assert report["completed"] == 0
    assert report["total"] == 5
    assert report["percent"] == 0.0
    assert report["is_complete"] is False


def test_complete_step(lm):
    lm.complete_step(1)
    report = lm.get_progress_report()
    assert report["completed"] == 1
    assert report["percent"] == 20.0


def test_complete_all_steps(lm):
    for i in range(1, 6):
        lm.complete_step(i)
    report = lm.get_progress_report()
    assert report["is_complete"] is True
    assert report["percent"] == 100.0


def test_get_step_returns_data(lm):
    step_data = lm.get_step(1, beginner_mode=True)
    assert "title" in step_data
    assert "prompt" in step_data
    assert "РЕЖИМ НОВИЧКА" in step_data["prompt"]


def test_get_step_standard_mode(lm):
    step_data = lm.get_step(1, beginner_mode=False)
    assert "СТАНДАРТНЫЙ РЕЖИМ" in step_data["prompt"]


def test_get_step_invalid(lm):
    step_data = lm.get_step(99)
    assert "error" in step_data


def test_progress_persistence(data_dir):
    lm1 = LearningMode(data_dir=data_dir)
    lm1.complete_step(1, concept="test_concept")

    lm2 = LearningMode(data_dir=data_dir)
    report = lm2.get_progress_report()
    assert report["completed"] == 1
    assert "test_concept" in report["concepts"]


def test_reset_progress(lm):
    lm.complete_step(1)
    lm.reset_progress()
    report = lm.get_progress_report()
    assert report["completed"] == 0


def test_tutorials_count(lm):
    assert len(lm.tutorials) == 5
